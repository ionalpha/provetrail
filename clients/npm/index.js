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

// DER SubjectPublicKeyInfo prefix for a raw Ed25519 public key.
const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

/** A record failed verification. The message names the failed check. */
export class VerifyError extends Error {
  constructor(message) {
    super(message);
    this.name = "VerifyError";
  }
}

/**
 * Verify a marshalled sealed run record against an Ed25519 public key. Returns
 * an object `{ events }` with the run's events in order (each a Uint8Array).
 * Throws {@link VerifyError} on a bad signature, a size mismatch, or events
 * that do not rebuild the signed root.
 *
 * @param {Uint8Array} record the marshalled record bytes
 * @param {Uint8Array} publicKey the 32-byte raw Ed25519 public key
 */
export function verifyRun(record, publicKey) {
  if (publicKey.length !== 32) {
    throw new VerifyError(`public key must be 32 bytes, got ${publicKey.length}`);
  }

  let rec;
  try {
    rec = decode(record);
  } catch (e) {
    throw new VerifyError(`decode record: ${e.message}`);
  }
  if (rec === null || typeof rec !== "object" || !("checkpoint" in rec) || !("events" in rec)) {
    throw new VerifyError("record is not a {checkpoint, events} map");
  }
  const checkpoint = rec.checkpoint;
  const events = rec.events;
  if (!(checkpoint instanceof Uint8Array) || !Array.isArray(events)) {
    throw new VerifyError("record has the wrong field types");
  }
  const eventBytes = events.map((e) => Uint8Array.from(e));

  const { size, root } = verifyCheckpoint(checkpoint, publicKey);

  if (eventBytes.length !== size) {
    throw new VerifyError("event count does not match the signed size");
  }
  const leaves = eventBytes.map(leafHash);
  if (!Buffer.from(merkleRoot(leaves)).equals(Buffer.from(root))) {
    throw new VerifyError("events do not reproduce the signed root");
  }
  return { events: eventBytes };
}

/** Verify the COSE_Sign1 checkpoint and return its { size, root }. */
function verifyCheckpoint(coseBytes, publicKey) {
  let tag;
  try {
    tag = decode(coseBytes);
  } catch (e) {
    throw new VerifyError(`decode checkpoint: ${e.message}`);
  }
  if (!tag || tag.tag !== COSE_SIGN1_TAG || !Array.isArray(tag.contents) || tag.contents.length !== 4) {
    throw new VerifyError("checkpoint is not a tagged COSE_Sign1 message");
  }
  const [protectedHeader, , payload, signature] = tag.contents;
  if (payload == null) {
    throw new VerifyError("checkpoint has no payload");
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
    throw new VerifyError(`public key is not a valid Ed25519 key: ${e.message}`);
  }
  if (!cryptoVerify(null, Buffer.from(sigStructure), key, Buffer.from(signature))) {
    throw new VerifyError("signature did not verify");
  }

  let cp;
  try {
    cp = decode(Uint8Array.from(payload));
  } catch (e) {
    throw new VerifyError(`decode checkpoint payload: ${e.message}`);
  }
  if (cp === null || typeof cp !== "object" || !("size" in cp) || !("root" in cp)) {
    throw new VerifyError("checkpoint payload is not a valid checkpoint");
  }
  const size = typeof cp.size === "bigint" ? Number(cp.size) : cp.size;
  if (!Number.isInteger(size) || !(cp.root instanceof Uint8Array)) {
    throw new VerifyError("checkpoint has the wrong field types");
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
