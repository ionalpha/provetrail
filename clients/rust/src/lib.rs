//! A verifier for the Provetrail standard (verifiable execution provenance).
//!
//! This first cut checks the integrity of a sealed run record: the COSE_Sign1
//! checkpoint signature is valid under a given key, and the events rebuild the signed
//! RFC 9162 Merkle root. It follows the carry-the-bytes rule, it rehashes the exact
//! bytes the record carries and never re-serializes, so it agrees with any other
//! conformant verifier on the same record.

use coset::TaggedCborSerializable;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::Deserialize;
use sha2::{Digest, Sha256};

/// The domain tag mixed into each event's hashed preimage, matching the standard.
const LEAF_DOMAIN: &[u8] = b"provetrail/event/v1\n";

/// The pinned checkpoint media type; together with COSE algorithm -19 (Ed25519,
/// RFC 9864) these are the only protected-header claims a checkpoint may carry.
const CHECKPOINT_CONTENT_TYPE: &str = "application/vnd.provetrail.checkpoint+cbor";

#[derive(Deserialize)]
struct Checkpoint {
    #[allow(dead_code)]
    origin: String,
    size: u64,
    #[serde(with = "serde_bytes")]
    root: Vec<u8>,
}

/// Why a record failed verification. [`VerifyError::code`] gives the registered
/// failure code (CONFORMANCE.md section 6 / registry.json) for each variant.
#[derive(Debug)]
#[non_exhaustive]
pub enum VerifyError {
    /// The record container could not be decoded.
    Decode(String),
    /// The record container is not in canonical form.
    NonCanonical,
    /// The checkpoint signature (or its COSE framing or algorithm) did not verify.
    Signature,
    /// The signed content type is missing or is not the checkpoint type.
    BadContentType,
    /// The signed payload is not the canonical encoding of a checkpoint.
    CheckpointDecode(String),
    /// The record was signed by a key not in the keyring.
    UnknownKey,
    /// The verifier was given a malformed key.
    BadKey,
    /// The event count does not match the signed size.
    SizeMismatch,
    /// The events do not reproduce the signed root.
    RootMismatch,
    /// The record carries no events.
    Empty,
}

impl VerifyError {
    /// The registered failure code for this rejection.
    pub fn code(&self) -> &'static str {
        match self {
            VerifyError::Decode(_) => "record.decode",
            VerifyError::NonCanonical => "record.non_canonical",
            VerifyError::Signature => "sign.signature_invalid",
            VerifyError::BadContentType => "sign.bad_content_type",
            VerifyError::CheckpointDecode(_) => "sign.checkpoint_decode",
            VerifyError::UnknownKey => "sign.unknown_key",
            VerifyError::BadKey => "sign.bad_key",
            VerifyError::SizeMismatch => "record.size_mismatch",
            VerifyError::RootMismatch => "record.root_mismatch",
            VerifyError::Empty => "record.empty",
        }
    }
}

impl std::fmt::Display for VerifyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            VerifyError::Decode(m) => write!(f, "{}: {m}", self.code()),
            VerifyError::NonCanonical => write!(
                f,
                "{}: record container is not in canonical form",
                self.code()
            ),
            VerifyError::Signature => write!(f, "{}: signature did not verify", self.code()),
            VerifyError::BadContentType => {
                write!(f, "{}: unexpected checkpoint content type", self.code())
            }
            VerifyError::CheckpointDecode(m) => write!(f, "{}: {m}", self.code()),
            VerifyError::UnknownKey => {
                write!(f, "{}: signed by a key not in the keyring", self.code())
            }
            VerifyError::BadKey => write!(f, "{}: malformed Ed25519 key", self.code()),
            VerifyError::SizeMismatch => write!(
                f,
                "{}: event count does not match the signed size",
                self.code()
            ),
            VerifyError::RootMismatch => write!(
                f,
                "{}: events do not reproduce the signed root",
                self.code()
            ),
            VerifyError::Empty => write!(f, "{}: record carries no events", self.code()),
        }
    }
}

impl std::error::Error for VerifyError {}

/// The result of a successful verification: the run's events, in order.
pub struct Verified {
    pub events: Vec<Vec<u8>>,
}

/// Verify a marshalled sealed run record against an Ed25519 public key, returning its
/// events in order. The key is trusted for any key id the record names; use
/// [`verify_run_keyring`] to resolve the record's `kid` against a keyring instead.
pub fn verify_run(record: &[u8], public_key: &[u8; 32]) -> Result<Verified, VerifyError> {
    verify_run_inner(record, Keys::Single(public_key))
}

/// Verify a marshalled sealed run record against a keyring of key id → raw
/// Ed25519 public key. The record's `kid` must resolve in the ring
/// ([`VerifyError::UnknownKey`] otherwise).
pub fn verify_run_keyring(
    record: &[u8],
    keyring: &std::collections::HashMap<String, [u8; 32]>,
) -> Result<Verified, VerifyError> {
    verify_run_inner(record, Keys::Ring(keyring))
}

enum Keys<'a> {
    Single(&'a [u8; 32]),
    Ring(&'a std::collections::HashMap<String, [u8; 32]>),
}

fn verify_run_inner(record: &[u8], keys: Keys<'_>) -> Result<Verified, VerifyError> {
    let (checkpoint, carried) = decode_container(record)?;

    if carried.is_empty() {
        return Err(VerifyError::Empty);
    }

    // The checkpoint is a tagged COSE_Sign1 (CBOR tag 18).
    let sign1 =
        coset::CoseSign1::from_tagged_slice(&checkpoint).map_err(|_| VerifyError::Signature)?;
    // The protected header is covered by the signature, but its claims must still
    // be OUR claims: the pinned algorithm and content type. A verifier that skips
    // this accepts an algorithm or type substitution.
    match &sign1.protected.header.content_type {
        Some(coset::ContentType::Text(t)) if t == CHECKPOINT_CONTENT_TYPE => {}
        _ => return Err(VerifyError::BadContentType),
    }
    let public_key: [u8; 32] = match keys {
        Keys::Single(k) => *k,
        Keys::Ring(ring) => {
            let kid = String::from_utf8_lossy(&sign1.protected.header.key_id);
            *ring.get(kid.as_ref()).ok_or(VerifyError::UnknownKey)?
        }
    };
    if sign1.protected.header.alg
        != Some(coset::Algorithm::Assigned(coset::iana::Algorithm::Ed25519))
    {
        return Err(VerifyError::Signature);
    }
    let vk = VerifyingKey::from_bytes(&public_key).map_err(|_| VerifyError::BadKey)?;
    sign1
        .verify_signature(b"", |sig, tbs| {
            let signature = Signature::from_slice(sig).map_err(|_| ())?;
            vk.verify(tbs, &signature).map_err(|_| ())
        })
        .map_err(|_| VerifyError::Signature)?;

    let payload = sign1.payload.ok_or(VerifyError::Signature)?;
    let cp: Checkpoint = ciborium::from_reader(payload.as_slice())
        .map_err(|e| VerifyError::CheckpointDecode(e.to_string()))?;

    let events = carried;
    if events.len() as u64 != cp.size {
        return Err(VerifyError::SizeMismatch);
    }
    let leaves: Vec<[u8; 32]> = events.iter().map(|e| leaf_hash(e)).collect();
    if merkle_root(&leaves).as_slice() != cp.root.as_slice() {
        return Err(VerifyError::RootMismatch);
    }
    Ok(Verified { events })
}

/// Decode the record container into its checkpoint and carried event bytes.
///
/// The container must be exactly the two known fields, in deterministic key order. RFC
/// 8949 Section 4.2 sorts map keys bytewise on their *encoded* form, so the shorter
/// `events` precedes `checkpoint`. An extra field, or keys out of order, means these
/// bytes are not the canonical encoding of this record, and two verifiers could
/// disagree about what was signed.
fn decode_container(record: &[u8]) -> Result<(Vec<u8>, Vec<Vec<u8>>), VerifyError> {
    use ciborium::value::Value;

    let value: Value =
        ciborium::from_reader(record).map_err(|e| VerifyError::Decode(e.to_string()))?;
    // Beyond key order, the bytes must be the exact canonical encoding of what
    // they decode to. A lenient decode absorbs several distinct defects, so the
    // head and a prefix comparison classify them: an indefinite or duplicated-key
    // map and trailing bytes are decode-level faults; anything else that fails the
    // re-encoding comparison (a non-minimal head) is a canonical-form fault.
    if record.first().is_some_and(|b| b & 0x1f == 31) {
        return Err(VerifyError::Decode(
            "record container is indefinite-length".into(),
        ));
    }
    let Value::Map(entries) = value else {
        return Err(VerifyError::Decode("record is not a map".into()));
    };
    let keys: Vec<Option<&str>> = entries.iter().map(|(k, _)| k.as_text()).collect();
    for (i, k) in keys.iter().enumerate() {
        if keys[..i].contains(k) {
            return Err(VerifyError::Decode(
                "record container has a duplicated key".into(),
            ));
        }
    }
    if keys != [Some("events"), Some("checkpoint")] {
        return Err(VerifyError::NonCanonical);
    }
    let mut reencoded = Vec::with_capacity(record.len());
    ciborium::into_writer(&Value::Map(entries.clone()), &mut reencoded)
        .map_err(|e| VerifyError::Decode(e.to_string()))?;
    if reencoded != record {
        if record.len() > reencoded.len() && record[..reencoded.len()] == reencoded[..] {
            return Err(VerifyError::Decode("record has trailing bytes".into()));
        }
        return Err(VerifyError::NonCanonical);
    }

    let checkpoint = entries[1]
        .1
        .as_bytes()
        .ok_or_else(|| VerifyError::Decode("checkpoint is not a byte string".into()))?
        .clone();
    let Value::Array(items) = &entries[0].1 else {
        return Err(VerifyError::Decode("events is not an array".into()));
    };
    let mut events = Vec::with_capacity(items.len());
    for item in items {
        events.push(
            item.as_bytes()
                .ok_or_else(|| VerifyError::Decode("an event is not a byte string".into()))?
                .clone(),
        );
    }
    Ok((checkpoint, events))
}

/// RFC 6962 leaf hash of an event's canonical bytes, over the domain-separated,
/// length-framed preimage.
fn leaf_hash(canonical: &[u8]) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update([0x00]);
    h.update(LEAF_DOMAIN);
    h.update((canonical.len() as u64).to_be_bytes());
    h.update(canonical);
    h.finalize().into()
}

fn node_hash(left: &[u8; 32], right: &[u8; 32]) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update([0x01]);
    h.update(left);
    h.update(right);
    h.finalize().into()
}

/// RFC 6962 Merkle Tree Hash over the leaf hashes.
fn merkle_root(leaves: &[[u8; 32]]) -> [u8; 32] {
    match leaves.len() {
        0 => Sha256::digest([]).into(),
        1 => leaves[0],
        n => {
            let mut k = 1usize;
            while k * 2 < n {
                k *= 2;
            }
            node_hash(&merkle_root(&leaves[..k]), &merkle_root(&leaves[k..]))
        }
    }
}
