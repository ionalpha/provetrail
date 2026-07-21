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

/// Why a record failed verification.
#[derive(Debug)]
#[non_exhaustive]
pub enum VerifyError {
    /// The record or a field within it could not be decoded.
    Decode(String),
    /// The record container is not in canonical form.
    NonCanonical,
    /// The checkpoint signature did not verify under the given key.
    Signature,
    /// The event count does not match the signed size.
    SizeMismatch,
    /// The events do not reproduce the signed root.
    RootMismatch,
    /// The record carries no events.
    Empty,
}

impl std::fmt::Display for VerifyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            VerifyError::Decode(m) => write!(f, "decode: {m}"),
            VerifyError::NonCanonical => write!(f, "record container is not in canonical form"),
            VerifyError::Signature => write!(f, "signature did not verify"),
            VerifyError::SizeMismatch => write!(f, "event count does not match the signed size"),
            VerifyError::RootMismatch => write!(f, "events do not reproduce the signed root"),
            VerifyError::Empty => write!(f, "record carries no events"),
        }
    }
}

impl std::error::Error for VerifyError {}

/// The result of a successful verification: the run's events, in order.
pub struct Verified {
    pub events: Vec<Vec<u8>>,
}

/// Verify a marshalled sealed run record against an Ed25519 public key, returning its
/// events in order. Fails closed on a bad signature, a size mismatch, or events that
/// do not rebuild the signed root.
pub fn verify_run(record: &[u8], public_key: &[u8; 32]) -> Result<Verified, VerifyError> {
    let (checkpoint, carried) = decode_container(record)?;

    if carried.is_empty() {
        return Err(VerifyError::Empty);
    }

    // The checkpoint is a tagged COSE_Sign1 (CBOR tag 18).
    let sign1 = coset::CoseSign1::from_tagged_slice(&checkpoint)
        .map_err(|e| VerifyError::Decode(format!("checkpoint: {e}")))?;
    // The protected header is covered by the signature, but its claims must still
    // be OUR claims: the pinned algorithm and content type. A verifier that skips
    // this accepts an algorithm or type substitution.
    match &sign1.protected.header.content_type {
        Some(coset::ContentType::Text(t)) if t == CHECKPOINT_CONTENT_TYPE => {}
        _ => return Err(VerifyError::Decode("unexpected checkpoint content type".into())),
    }
    if sign1.protected.header.alg
        != Some(coset::Algorithm::Assigned(coset::iana::Algorithm::Ed25519))
    {
        return Err(VerifyError::Decode("unexpected checkpoint algorithm".into()));
    }
    let vk = VerifyingKey::from_bytes(public_key).map_err(|_| VerifyError::Signature)?;
    sign1
        .verify_signature(b"", |sig, tbs| {
            let signature = Signature::from_slice(sig).map_err(|_| ())?;
            vk.verify(tbs, &signature).map_err(|_| ())
        })
        .map_err(|_| VerifyError::Signature)?;

    let payload = sign1
        .payload
        .ok_or_else(|| VerifyError::Decode("checkpoint has no payload".into()))?;
    let cp: Checkpoint = ciborium::from_reader(payload.as_slice())
        .map_err(|e| VerifyError::Decode(e.to_string()))?;

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
    // they decode to: this rejects indefinite-length framing, non-minimal heads,
    // and trailing bytes, which a lenient decode would otherwise absorb.
    let mut reencoded = Vec::with_capacity(record.len());
    ciborium::into_writer(&value, &mut reencoded)
        .map_err(|e| VerifyError::Decode(e.to_string()))?;
    if reencoded != record {
        return Err(VerifyError::NonCanonical);
    }
    let Value::Map(entries) = value else {
        return Err(VerifyError::Decode("record is not a map".into()));
    };

    let keys: Vec<Option<&str>> = entries.iter().map(|(k, _)| k.as_text()).collect();
    if keys != [Some("events"), Some("checkpoint")] {
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
