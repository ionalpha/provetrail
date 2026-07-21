// Provetrail: a verifier for verifiable execution provenance records.
//
// This package verifies the integrity of a sealed run record: the COSE_Sign1
// checkpoint signature is valid under a given Ed25519 key, and the carried
// events rebuild the signed RFC 9162 (RFC 6962) Merkle root. It follows the
// carry-the-bytes rule: it rehashes the exact bytes the record carries and
// never re-serializes, so it agrees with any other conformant verifier on the
// same record.
//
// See https://provetrail.org and https://github.com/ionalpha/provetrail for the
// specification and the conformance suite.

import { createHash, createPublicKey, verify as cryptoVerify } from "node:crypto";
import { decode, encode } from "cbor2";

// The domain tag mixed into each event's hashed preimage, matching the standard.
const LEAF_DOMAIN = Buffer.from("provetrail/event/v1\n", "utf8");

// CBOR tag for a COSE_Sign1 message (RFC 9052).
const COSE_SIGN1_TAG = 18;

// The pinned protected-header constants: Ed25519 as COSE algorithm -19 (RFC 9864)
// and the vendor-tree checkpoint media type. Any other claim is a substitution.
const CHECKPOINT_ALG = -19;
const CHECKPOINT_CONTENT_TYPE = "application/vnd.provetrail.checkpoint+cbor";

// DER SubjectPublicKeyInfo prefix for a raw Ed25519 public key.
const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

/**
 * A record failed verification. `code` is the registered failure code
 * (CONFORMANCE.md section 6 / registry.json); the message names the failed
 * check for a human.
 */
export class VerifyError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "VerifyError";
    this.code = code;
  }
}

/**
 * Verify a marshalled sealed run record against an Ed25519 public key. Returns
 * an object `{ events }` with the run's events in order (each a Uint8Array).
 * Throws {@link VerifyError} on a bad signature, a size mismatch, or events
 * that do not rebuild the signed root.
 *
 * @param {Uint8Array} record the marshalled record bytes
 * @param {Uint8Array|Map<string,Uint8Array>|Object<string,Uint8Array>} publicKey
 *   either the 32-byte raw Ed25519 public key (trusted for any key id the
 *   record names), or a keyring mapping key id strings to 32-byte raw keys, in
 *   which case the record's kid must resolve in it.
 */
export function verifyRun(record, publicKey) {
  let keyring = null;
  if (publicKey instanceof Map) {
    keyring = publicKey;
  } else if (!(publicKey instanceof Uint8Array) && publicKey && typeof publicKey === "object") {
    keyring = new Map(Object.entries(publicKey));
  }
  if (keyring) {
    for (const [kid, key] of keyring) {
      if (key.length !== 32) {
        throw new VerifyError("sign.bad_key", `key "${kid}" must be 32 bytes, got ${key.length}`);
      }
    }
  } else if (publicKey.length !== 32) {
    throw new VerifyError("sign.bad_key", `public key must be 32 bytes, got ${publicKey.length}`);
  }

  let rec;
  try {
    rec = decode(record);
  } catch (e) {
    throw new VerifyError("record.decode", `decode record: ${e.message}`);
  }
  if (rec === null || typeof rec !== "object" || !("checkpoint" in rec) || !("events" in rec)) {
    throw new VerifyError("record.decode", "record is not a {checkpoint, events} map");
  }
  // record.non_canonical: the container must be exactly the two known fields, in
  // deterministic key order. RFC 8949 Section 4.2 sorts map keys bytewise on their
  // *encoded* form, so the shorter "events" precedes "checkpoint". An extra field, or
  // keys out of order, means these bytes are not the canonical encoding of this
  // record, and two verifiers could disagree about what was signed.
  const keys = Object.keys(rec);
  if (keys.length !== 2 || keys[0] !== "events" || keys[1] !== "checkpoint") {
    throw new VerifyError("record.non_canonical", "record container is not in canonical form");
  }
  const checkpoint = rec.checkpoint;
  const events = rec.events;
  if (!(checkpoint instanceof Uint8Array) || !Array.isArray(events)) {
    throw new VerifyError("record.decode", "record has the wrong field types");
  }
  if (events.some((e) => !(e instanceof Uint8Array))) {
    throw new VerifyError("record.decode", "record events must be byte strings");
  }
  // Beyond key order, the bytes must be the exact canonical encoding of what they
  // decode to. A lenient decode absorbs several distinct defects, so the head and
  // a prefix comparison classify them: an indefinite or over-counted (duplicated
  // key) map and trailing bytes are decode-level faults; anything else that fails
  // the re-encoding comparison (a non-minimal head) is a canonical-form fault.
  // Byte fields are normalized to plain Uint8Array first: cbor2 serializes a Node
  // Buffer through its toJSON form, not as a byte string.
  if ((record[0] & 0x1f) === 31) {
    throw new VerifyError("record.decode", "record container is indefinite-length");
  }
  const claimedEntries = mapEntryCount(record);
  if (claimedEntries !== null && claimedEntries > keys.length) {
    throw new VerifyError("record.decode", "record container has a duplicated key");
  }
  const normalized = {
    events: events.map((e) => Uint8Array.from(e)),
    checkpoint: Uint8Array.from(checkpoint),
  };
  const reencoded = Buffer.from(encode(normalized));
  const recordBuf = Buffer.from(record);
  if (!reencoded.equals(recordBuf)) {
    if (recordBuf.length > reencoded.length && recordBuf.subarray(0, reencoded.length).equals(reencoded)) {
      throw new VerifyError("record.decode", "record has trailing bytes");
    }
    throw new VerifyError("record.non_canonical", "record container is not in canonical form");
  }
  if (events.length === 0) {
    throw new VerifyError("record.empty", "record carries no events");
  }
  const eventBytes = events.map((e) => Uint8Array.from(e));

  const { size, root } = verifyCheckpoint(checkpoint, publicKey, keyring);

  if (eventBytes.length !== size) {
    throw new VerifyError("record.size_mismatch", "event count does not match the signed size");
  }
  const leaves = eventBytes.map(leafHash);
  if (!Buffer.from(merkleRoot(leaves)).equals(Buffer.from(root))) {
    throw new VerifyError("record.root_mismatch", "events do not reproduce the signed root");
  }
  return { events: eventBytes };
}

/** The entry count a CBOR map head claims, or null if not a definite map. */
function mapEntryCount(b) {
  if (!b.length || b[0] >> 5 !== 5) return null;
  const arg = b[0] & 0x1f;
  if (arg < 24) return arg;
  const widths = { 24: 1, 25: 2, 26: 4, 27: 8 };
  const width = widths[arg];
  if (!width || b.length < 1 + width) return null;
  let n = 0;
  for (let i = 1; i <= width; i++) n = n * 256 + b[i];
  return n;
}

/** Verify the COSE_Sign1 checkpoint and return its { size, root }. */
function verifyCheckpoint(coseBytes, publicKey, keyring) {
  let tag;
  try {
    tag = decode(coseBytes);
  } catch (e) {
    throw new VerifyError("sign.signature_invalid", `decode checkpoint: ${e.message}`);
  }
  if (!tag || tag.tag !== COSE_SIGN1_TAG || !Array.isArray(tag.contents) || tag.contents.length !== 4) {
    throw new VerifyError("sign.signature_invalid", "checkpoint is not a tagged COSE_Sign1 message");
  }
  const [protectedHeader, , payload, signature] = tag.contents;
  if (payload == null) {
    throw new VerifyError("sign.signature_invalid", "checkpoint has no payload");
  }

  // The protected header is covered by the signature, but its claims must still
  // be OUR claims: the pinned algorithm and content type. A verifier that skips
  // this accepts an algorithm or type substitution.
  let header;
  try {
    header = decode(Uint8Array.from(protectedHeader));
  } catch (e) {
    throw new VerifyError("sign.signature_invalid", `decode protected header: ${e.message}`);
  }
  if (!(header instanceof Map)) {
    throw new VerifyError("sign.signature_invalid", "protected header is not a map");
  }
  if (header.get(3) !== CHECKPOINT_CONTENT_TYPE) {
    throw new VerifyError("sign.bad_content_type", "unexpected checkpoint content type");
  }

  if (keyring) {
    const kid = header.get(4);
    const kidStr = kid instanceof Uint8Array ? Buffer.from(kid).toString("utf8") : null;
    const resolved = kidStr !== null ? keyring.get(kidStr) : undefined;
    if (!resolved) {
      throw new VerifyError("sign.unknown_key", "checkpoint signed by a key not in the keyring");
    }
    publicKey = resolved;
  }

  if (header.get(1) !== CHECKPOINT_ALG) {
    throw new VerifyError("sign.signature_invalid", "unexpected checkpoint algorithm");
  }

  // The signed bytes are the COSE_Sign1 Sig_structure (RFC 9052 section 4.4),
  // with an empty external_aad. The protected header is carried verbatim.
  const sigStructure = encode([
    "Signature1",
    Uint8Array.from(protectedHeader),
    new Uint8Array(0),
    Uint8Array.from(payload),
  ]);

  let key;
  try {
    const der = Buffer.concat([ED25519_SPKI_PREFIX, Buffer.from(publicKey)]);
    key = createPublicKey({ key: der, format: "der", type: "spki" });
  } catch (e) {
    throw new VerifyError("sign.bad_key", `public key is not a valid Ed25519 key: ${e.message}`);
  }
  if (!cryptoVerify(null, Buffer.from(sigStructure), key, Buffer.from(signature))) {
    throw new VerifyError("sign.signature_invalid", "signature did not verify");
  }

  let cp;
  try {
    cp = decode(Uint8Array.from(payload));
  } catch (e) {
    throw new VerifyError("sign.checkpoint_decode", `decode checkpoint payload: ${e.message}`);
  }
  if (cp === null || typeof cp !== "object" || !("size" in cp) || !("root" in cp)) {
    throw new VerifyError("sign.checkpoint_decode", "checkpoint payload is not a valid checkpoint");
  }
  const size = typeof cp.size === "bigint" ? Number(cp.size) : cp.size;
  if (!Number.isInteger(size) || !(cp.root instanceof Uint8Array)) {
    throw new VerifyError("sign.checkpoint_decode", "checkpoint has the wrong field types");
  }
  return { size, root: cp.root };
}

/** RFC 6962 leaf hash over the domain-separated, length-framed preimage. */
function leafHash(canonical) {
  const len = Buffer.alloc(8);
  len.writeBigUInt64BE(BigInt(canonical.length));
  return createHash("sha256")
    .update(Buffer.from([0x00]))
    .update(LEAF_DOMAIN)
    .update(len)
    .update(Buffer.from(canonical))
    .digest();
}

function nodeHash(left, right) {
  return createHash("sha256")
    .update(Buffer.from([0x01]))
    .update(left)
    .update(right)
    .digest();
}

/** RFC 6962 Merkle Tree Hash over the leaf hashes. */
function merkleRoot(leaves) {
  const n = leaves.length;
  if (n === 0) return createHash("sha256").digest();
  if (n === 1) return leaves[0];
  let k = 1;
  while (k * 2 < n) k *= 2;
  return nodeHash(merkleRoot(leaves.slice(0, k)), merkleRoot(leaves.slice(k)));
}
