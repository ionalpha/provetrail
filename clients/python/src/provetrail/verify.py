"""Integrity verification of a Provetrail sealed run record.

The record is deterministic CBOR: a map of a COSE_Sign1 ``checkpoint`` and an
array of canonical ``events``. Verification checks the checkpoint signature under
a given Ed25519 key, that the event count matches the signed size, and that the
events rebuild the signed RFC 9162 (RFC 6962) Merkle root.

Every rejection carries a failure code from the published registry
(``registry.json`` / CONFORMANCE.md section 6), so a rejection names which check
failed rather than just "invalid".
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import cbor2
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# The domain tag mixed into each event's hashed preimage, matching the standard.
_LEAF_DOMAIN = b"provetrail/event/v1\n"

# CBOR tag for a COSE_Sign1 message (RFC 9052).
_COSE_SIGN1_TAG = 18

# The pinned protected-header constants: Ed25519 as COSE algorithm -19 (RFC 9864)
# and the vendor-tree checkpoint media type. Any other claim is a substitution.
_CHECKPOINT_ALG = -19
_CHECKPOINT_CONTENT_TYPE = "application/vnd.provetrail.checkpoint+cbor"


class VerifyError(Exception):
    """A record failed verification.

    ``code`` is the registered failure code (CONFORMANCE.md section 6 /
    ``registry.json``); the message names the failed check for a human.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Verified:
    """The result of a successful verification: the run's events, in order."""

    events: list[bytes]


def verify_run(record: bytes, public_key) -> Verified:
    """Verify a marshalled sealed run record against an Ed25519 public key.

    Returns the run's events in order. Raises :class:`VerifyError`, carrying a
    registered failure code, on any defect.

    ``public_key`` is either the 32-byte raw Ed25519 public key (trusted for any
    key id the record names) or a keyring: a dict mapping key id strings to
    32-byte raw keys, in which case the record's ``kid`` must resolve in it.
    """
    keyring = None
    if isinstance(public_key, dict):
        keyring = public_key
        for kid, key in keyring.items():
            if len(key) != 32:
                raise VerifyError("sign.bad_key", f"key {kid!r} must be 32 bytes, got {len(key)}")
    elif len(public_key) != 32:
        raise VerifyError("sign.bad_key", f"public key must be 32 bytes, got {len(public_key)}")

    try:
        rec = cbor2.loads(record)
    except Exception as exc:  # noqa: BLE001 - any decode failure is a reject
        raise VerifyError("record.decode", f"decode record: {exc}") from exc
    if not isinstance(rec, dict) or "checkpoint" not in rec or "events" not in rec:
        raise VerifyError("record.decode", "record is not a {checkpoint, events} map")
    # record.non_canonical: the container must be exactly the two known fields, in
    # deterministic key order. RFC 8949 Section 4.2 sorts map keys bytewise on their
    # *encoded* form, so the shorter "events" precedes "checkpoint". An extra field, or
    # keys out of order, means these bytes are not the canonical encoding of this
    # record, and two verifiers could disagree about what was signed.
    if list(rec) != ["events", "checkpoint"]:
        raise VerifyError("record.non_canonical", "record container is not in canonical form")
    checkpoint = rec["checkpoint"]
    events = rec["events"]
    if not isinstance(checkpoint, (bytes, bytearray)) or not isinstance(events, list):
        raise VerifyError("record.decode", "record has the wrong field types")
    if any(not isinstance(e, bytes) for e in events):
        raise VerifyError("record.decode", "record events must be byte strings")
    # Beyond key order, the bytes must be the exact canonical encoding of what they
    # decode to. A lenient decode absorbs several distinct defects, so the head and
    # a prefix comparison classify them: an indefinite or over-counted (duplicated
    # key) map and trailing bytes are decode-level faults; anything else that fails
    # the re-encoding comparison (a non-minimal head) is a canonical-form fault.
    head = record[0]
    if head & 0x1F == 31:
        raise VerifyError("record.decode", "record container is indefinite-length")
    entries = _map_entry_count(record)
    if entries is not None and entries > len(rec):
        raise VerifyError("record.decode", "record container has a duplicated key")
    reencoded = cbor2.dumps(rec, canonical=True)
    if bytes(record) != reencoded:
        if bytes(record[: len(reencoded)]) == reencoded:
            raise VerifyError("record.decode", "record has trailing bytes")
        raise VerifyError("record.non_canonical", "record container is not in canonical form")
    events = [bytes(e) for e in events]
    if not events:
        raise VerifyError("record.empty", "record carries no events")

    size, root = _verify_checkpoint(bytes(checkpoint), public_key, keyring)

    if len(events) != size:
        raise VerifyError("record.size_mismatch", "event count does not match the signed size")
    leaves = [_leaf_hash(e) for e in events]
    if _merkle_root(leaves) != root:
        raise VerifyError("record.root_mismatch", "events do not reproduce the signed root")
    return Verified(events=events)


def _map_entry_count(b: bytes) -> int | None:
    """The entry count a CBOR map head claims, or None if b is not a definite map."""
    if not b or b[0] >> 5 != 5:
        return None
    arg = b[0] & 0x1F
    if arg < 24:
        return arg
    widths = {24: 1, 25: 2, 26: 4, 27: 8}
    width = widths.get(arg)
    if width is None or len(b) < 1 + width:
        return None
    return int.from_bytes(b[1 : 1 + width], "big")


def _verify_checkpoint(cose_bytes: bytes, public_key, keyring) -> tuple[int, bytes]:
    """Verify the COSE_Sign1 checkpoint and return its (size, root)."""
    try:
        tag = cbor2.loads(cose_bytes)
    except Exception as exc:  # noqa: BLE001
        raise VerifyError("sign.signature_invalid", f"decode checkpoint: {exc}") from exc
    if not isinstance(tag, cbor2.CBORTag) or tag.tag != _COSE_SIGN1_TAG:
        raise VerifyError("sign.signature_invalid", "checkpoint is not a tagged COSE_Sign1 message")
    arr = tag.value
    if not isinstance(arr, (list, tuple)) or len(arr) != 4:
        raise VerifyError("sign.signature_invalid", "malformed COSE_Sign1 structure")
    protected, _unprotected, payload, signature = arr
    if payload is None:
        raise VerifyError("sign.signature_invalid", "checkpoint has no payload")
    protected = bytes(protected)
    payload = bytes(payload)
    signature = bytes(signature)

    # The protected header is covered by the signature, but its claims must still
    # be OUR claims: the pinned algorithm and content type. A verifier that skips
    # this accepts an algorithm or type substitution.
    try:
        header = cbor2.loads(protected)
    except Exception as exc:  # noqa: BLE001
        raise VerifyError("sign.signature_invalid", f"decode protected header: {exc}") from exc
    if not isinstance(header, dict):
        raise VerifyError("sign.signature_invalid", "protected header is not a map")
    if header.get(3) != _CHECKPOINT_CONTENT_TYPE:
        raise VerifyError("sign.bad_content_type", "unexpected checkpoint content type")

    if keyring is not None:
        kid = header.get(4)
        kid_str = bytes(kid).decode("utf-8", "replace") if isinstance(kid, (bytes, bytearray)) else None
        key = keyring.get(kid_str) if kid_str is not None else None
        if key is None:
            raise VerifyError("sign.unknown_key", "checkpoint signed by a key not in the keyring")
        public_key = key

    if header.get(1) != _CHECKPOINT_ALG:
        raise VerifyError("sign.signature_invalid", "unexpected checkpoint algorithm")

    # The signed bytes are the COSE_Sign1 Sig_structure (RFC 9052 section 4.4),
    # with an empty external_aad. The protected header is carried verbatim.
    sig_structure = cbor2.dumps(["Signature1", protected, b"", payload], canonical=True)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, sig_structure)
    except InvalidSignature as exc:
        raise VerifyError("sign.signature_invalid", "signature did not verify") from exc

    try:
        cp = cbor2.loads(payload)
    except Exception as exc:  # noqa: BLE001
        raise VerifyError("sign.checkpoint_decode", f"decode checkpoint payload: {exc}") from exc
    # The payload must be the exact canonical encoding of the closed checkpoint
    # map {root, size, origin}: a missing or extra field, non-canonical key order,
    # a float size, or a root that is not a SHA-256 digest is rejected rather than
    # absorbed into a default.
    if not isinstance(cp, dict) or list(cp) != ["root", "size", "origin"]:
        raise VerifyError("sign.checkpoint_decode", "checkpoint payload is not the closed {root, size, origin} map")
    root, size, origin = cp["root"], cp["size"], cp["origin"]
    if (
        not isinstance(root, bytes)
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
        or not isinstance(origin, str)
    ):
        raise VerifyError("sign.checkpoint_decode", "checkpoint has the wrong field types")
    if len(root) != 32:
        raise VerifyError("sign.checkpoint_decode", "checkpoint root is not a SHA-256 digest")
    if cbor2.dumps(cp, canonical=True) != payload:
        raise VerifyError("sign.checkpoint_decode", "checkpoint payload is not in canonical form")
    return size, root


def _leaf_hash(canonical: bytes) -> bytes:
    """RFC 6962 leaf hash over the domain-separated, length-framed preimage."""
    h = hashlib.sha256()
    h.update(b"\x00")
    h.update(_LEAF_DOMAIN)
    h.update(len(canonical).to_bytes(8, "big"))
    h.update(canonical)
    return h.digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(b"\x01")
    h.update(left)
    h.update(right)
    return h.digest()


def _merkle_root(leaves: list[bytes]) -> bytes:
    """RFC 6962 Merkle Tree Hash over the leaf hashes."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaves[0]
    k = 1
    while k * 2 < n:
        k *= 2
    return _node_hash(_merkle_root(leaves[:k]), _merkle_root(leaves[k:]))
