"""Integrity verification of a Provetrail sealed run record.

The record is deterministic CBOR: a map of a COSE_Sign1 ``checkpoint`` and an
array of canonical ``events``. Verification checks the checkpoint signature under
a given Ed25519 key, that the event count matches the signed size, and that the
events rebuild the signed RFC 9162 (RFC 6962) Merkle root.
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


class VerifyError(Exception):
    """A record failed verification. The message names the failed check."""


@dataclass(frozen=True)
class Verified:
    """The result of a successful verification: the run's events, in order."""

    events: list[bytes]


def verify_run(record: bytes, public_key: bytes) -> Verified:
    """Verify a marshalled sealed run record against an Ed25519 public key.

    Returns the run's events in order. Raises :class:`VerifyError` on a bad
    signature, a size mismatch, or events that do not rebuild the signed root.

    ``public_key`` is the 32-byte raw Ed25519 public key.
    """
    if len(public_key) != 32:
        raise VerifyError(f"public key must be 32 bytes, got {len(public_key)}")

    try:
        rec = cbor2.loads(record)
    except Exception as exc:  # noqa: BLE001 - any decode failure is a reject
        raise VerifyError(f"decode record: {exc}") from exc
    if not isinstance(rec, dict) or "checkpoint" not in rec or "events" not in rec:
        raise VerifyError("record is not a {checkpoint, events} map")
    checkpoint = rec["checkpoint"]
    events = rec["events"]
    if not isinstance(checkpoint, (bytes, bytearray)) or not isinstance(events, list):
        raise VerifyError("record has the wrong field types")
    events = [bytes(e) for e in events]

    size, root = _verify_checkpoint(bytes(checkpoint), public_key)

    if len(events) != size:
        raise VerifyError("event count does not match the signed size")
    leaves = [_leaf_hash(e) for e in events]
    if _merkle_root(leaves) != root:
        raise VerifyError("events do not reproduce the signed root")
    return Verified(events=events)


def _verify_checkpoint(cose_bytes: bytes, public_key: bytes) -> tuple[int, bytes]:
    """Verify the COSE_Sign1 checkpoint and return its (size, root)."""
    try:
        tag = cbor2.loads(cose_bytes)
    except Exception as exc:  # noqa: BLE001
        raise VerifyError(f"decode checkpoint: {exc}") from exc
    if not isinstance(tag, cbor2.CBORTag) or tag.tag != _COSE_SIGN1_TAG:
        raise VerifyError("checkpoint is not a tagged COSE_Sign1 message")
    arr = tag.value
    if not isinstance(arr, (list, tuple)) or len(arr) != 4:
        raise VerifyError("malformed COSE_Sign1 structure")
    protected, _unprotected, payload, signature = arr
    if payload is None:
        raise VerifyError("checkpoint has no payload")
    protected = bytes(protected)
    payload = bytes(payload)
    signature = bytes(signature)

    # The signed bytes are the COSE_Sign1 Sig_structure (RFC 9052 section 4.4),
    # with an empty external_aad. The protected header is carried verbatim.
    sig_structure = cbor2.dumps(["Signature1", protected, b"", payload], canonical=True)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, sig_structure)
    except InvalidSignature as exc:
        raise VerifyError("signature did not verify") from exc

    try:
        cp = cbor2.loads(payload)
    except Exception as exc:  # noqa: BLE001
        raise VerifyError(f"decode checkpoint payload: {exc}") from exc
    if not isinstance(cp, dict) or "size" not in cp or "root" not in cp:
        raise VerifyError("checkpoint payload is not a valid checkpoint")
    size = cp["size"]
    root = cp["root"]
    if not isinstance(size, int) or not isinstance(root, (bytes, bytearray)):
        raise VerifyError("checkpoint has the wrong field types")
    return size, bytes(root)


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
