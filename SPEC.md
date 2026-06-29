# Provetrail Specification

**Version:** 0.1.0-draft
**Status:** DRAFT. This document is a working draft published for review. It is not final, and the on-the-wire format is not frozen until v0.1.0 is tagged. See the status note in the README.

## Conventions

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

Identifiers are written in `code font`. This document avoids implementation-specific detail except where a concrete grounding aids clarity.

A note on maturity: until the cryptographic layer (Sections 4.2 and 4.3) is implemented and shipped with a verifier, a Provetrail record provides **structural** integrity guarantees only. A producer or document MUST NOT describe a record as "cryptographically verifiable" or "tamper-evident" before that layer is present.

---

## 1. Scope and non-goals

### 1.1 In scope

A portable, third-party-verifiable record of **what an agent did and under what governance**, anchored to an append-only, tamper-evident event log, such that an independent party can verify the record without trusting the producer and without re-implementing the producer.

### 1.2 Non-goals

- **Not content provenance.** C2PA answers "is this media authentic and by whom." Provetrail answers "what actions did an agent take, in what order, under what authority, and can you prove the record is untampered." They are complementary layers.
- **Not a tool-connection protocol** (that is MCP) and **not an agent-to-agent transport** (that is A2A). Provetrail is the provenance layer those can carry or reference.
- **Not an identity system.** The actor of an event is an identity expressed in an external standard (for example a `did`, a verifiable credential, or an agent-identity record). Provetrail references identity; it does not define it.
- **Not a new language or runtime.** One record format, many independent verifiers.

---

## 2. The three standardizable primitives

### 2.1 The event envelope

The envelope is the wire format of one immutable, ordered event. An event has the following logical fields:

| Field | Type | Meaning |
|---|---|---|
| `stream` | string | The identifier of the ordered stream this event belongs to. |
| `seq` | uint64 | Monotonic sequence number within the stream. MUST strictly increase by 1 with no gaps. |
| `time` | timestamp | The producer's recorded time of the event. Advisory; ordering is by `seq`, not `time`. |
| `type` | string | The event type, namespaced. |
| `actor` | identity | Who caused the event (agent, human, or system), expressed as an external identity reference. |
| `payload` | object | The type-specific body. |
| `schema_version` | uint64 | The schema version of `payload` for this `type`. |
| `causation_id` | string | OPTIONAL. The id of the event that caused this one, enabling exact causal replay. |
| `prev_hash` | bytes | The hash of the previous event's canonical bytes in this stream (Section 4.1). Absent only on the genesis event. |

**Standardizable contract:**

- A run's state is the **fold** of its event stream. State is a deterministic function of the log; replay is re-fold. A conforming verifier MUST be able to reject a record whose carried final state disagrees with the re-fold of its events.
- `schema_version`, together with an upcast rule, defines forward and backward evolution, so older records stay verifiable as the format grows. Producers MUST set `schema_version`; verifiers MUST apply the declared upcast for versions they support and MUST reject records whose version they cannot upcast rather than silently mis-interpret them.
- The value model is I-JSON (RFC 7493) compatible, encoded canonically per Section 3.

### 2.2 The verification-gate contract

A typed declaration of the checks an action passed before and while it executed. For a given action, the record states which gates ran and what each returned, recorded as events on the stream.

This is what makes "performed under governance" a checkable claim rather than a slogan. A verifier can confirm that the declared gates were recorded for an action, and that recorded gate results are consistent with the action stream (for example, an action MUST NOT appear with a gate result that contradicts it).

### 2.3 The trust-to-containment admission record

Every side-effecting action carries a trust level and is admitted against an authority grant and a containment decision **before** it executes. That admission is emitted as an event: `(action, trust, grant, containment-decision)`.

**Standardizable contract:** a verifier MUST be able to prove "no side-effecting action executed without a preceding admission record," and MUST be able to detect an action whose admission decision was deny but which nonetheless appears as executed.

### 2.4 Composition

The three primitives compose: the **envelope** is the substrate, the **gate contract** states what was checked, the **admission record** states it was authorized, and the cryptographic layer (Section 4) proves the whole record is untampered.

---

## 3. Canonicalization and cross-language verification

A hash chain is only verifiable in another language if that language can reproduce the exact hashed bytes. Provetrail resolves this with a hybrid rule.

### 3.1 Carry the bytes, rehash the bytes

- The proof artifact **carries the exact serialized bytes** of each event.
- A verifier **rehashes the bytes it is given**. It MUST NOT re-serialize the logical event in order to hash it. This makes cross-language verification trivial and removes any dependence on a verifier reproducing the producer's serializer.
- The canonicalization rule is ALSO specified (Section 3.2), so a verifier MAY OPTIONALLY re-derive canonical bytes from the logical event and confirm they match the carried bytes. A mismatch MUST be rejected: it indicates a producer carrying bytes that disagree with the logical content.

### 3.2 Canonical encoding

The canonical encoding is **deterministic CBOR** under the CBOR Common Deterministic Encoding (CDE) profile.

Rationale for CBOR over canonical JSON:

- The load-bearing `seq` field is a `uint64` and may exceed 2^53. RFC 8785 (JSON Canonicalization Scheme) numbers are IEEE-754 doubles and cannot represent such integers without a string-encoding workaround; CBOR encodes integers exactly.
- The neighbouring transparency and signing standards Provetrail aligns with (Section 4) are CBOR and COSE based.
- Deterministic CBOR is being tightened into a single interoperable profile (CDE), removing the historical ambiguity of RFC 8949 Section 4.2.

A non-canonical JSON projection of a record MAY be produced for human inspection or debugging. It is never hashed, never signed, and is not authoritative.

> DRAFT note: the choice of CBOR/CDE over JCS is settled for this draft but remains open to review before the v0.1.0 freeze. The carry-the-bytes rule in Section 3.1 makes a verifier largely indifferent to this choice, since it rehashes carried bytes regardless.

---

## 4. The proof artifact

Provetrail assembles existing standards. It does not invent cryptography.

### 4.1 Hash chain

Each event carries `prev_hash`, the hash of the previous event's canonical bytes in the same stream, forming a tamper-evident chain. The hash function is SHA-256 unless a later profile specifies otherwise. The genesis event has no `prev_hash`.

### 4.2 Signing

Signing uses **COSE** (RFC 9052) over the canonical CBOR bytes. COSE is the CBOR-native signing standard used by the neighbouring transparency and content-provenance ecosystems and supports multiple signatures. Signatures are **Ed25519** (RFC 8032).

A JSON-profile compatibility layer MAY sign using DSSE with pre-authentication encoding; this profile is secondary and non-authoritative.

### 4.3 Transparency and receipts

An append-only log of statements uses **RFC 9162** (Certificate Transparency v2) Merkle mechanics: inclusion proofs (a statement is in the log under a signed root) and consistency proofs (the log only ever appended between two signed roots). A record MAY carry a receipt demonstrating inclusion. An external transparency anchor MAY be used so that even the holder of the signing key cannot backdate a root.

### 4.4 Statement layering

The signed payload is a `run-provenance` statement (see [`predicates/run-provenance.md`](./predicates/run-provenance.md)). Under COSE it is carried as a signed statement; a JSON profile MAY carry it as an in-toto predicate. The predicate type identifier is descriptive and vendor-neutral.

### 4.5 Reuse map

| Layer | Reuse |
|---|---|
| Value model | I-JSON (RFC 7493), encoded as deterministic CBOR (CDE) |
| Signing | COSE (RFC 9052), Ed25519 (RFC 8032); DSSE+PAE as an optional JSON profile |
| Statement layering | SCITT-style signed statement (COSE); in-toto predicate as the JSON-profile analogue |
| Append-only log + proofs | RFC 9162 (Certificate Transparency v2) |
| Portable credentials (optional) | W3C Verifiable Credentials data model |

---

## 5. Conformance

Conformance is defined by the public test-vector suite and tier model in [`CONFORMANCE.md`](./CONFORMANCE.md). In summary, a verifier declares the tier it meets:

- **L1 Structural** - canonical-encoding conformance, schema validity, chain-link presence, `seq` monotonicity, fold consistency. No cryptography required.
- **L2 Cryptographic** - signature validity, key binding, algorithm pinning, hash-chain integrity over carried bytes.
- **L3 Transparency** - inclusion and consistency proofs against signed roots; receipt validity.
- **L4 Governance-complete** - every side-effecting action has a matching admission record; recorded gate results are consistent with the action stream; outcome claims are bound to a check.

A verifier is Provetrail-conformant at a tier if and only if it accepts every valid vector and rejects every invalid vector at that tier with the registered failure code.

---

## 6. Relationship to other standards

Provetrail is designed to slot beside, not displace:

- **C2PA** secures content provenance; Provetrail secures execution provenance. An agent that produces media can carry both.
- **MCP / A2A** connect tools and agents; Provetrail records what was done across those connections.
- **Agent-identity standards** (`did`, verifiable credentials, agent passports) answer who an actor is and what it is authorized to do; Provetrail's `actor` field references them and records what that actor then did.

Adoption strategy is by composition: a Provetrail record references the identities and connections defined elsewhere and adds the verifiable execution record those layers lack.

---

## 7. Versioning and evolution

- The record carries `schema_version` per event type; evolution is governed by an upcast rule so older records remain verifiable.
- The specification itself is versioned. Breaking changes increment the major version. The conformance suite is versioned in lockstep; a verifier reports the suite version and tier it passes.
- Before v0.1.0 is tagged, any part of this draft may change. After the freeze, the on-the-wire format is a stable contract.

---

## References

- RFC 2119 / RFC 8174 - Requirement keywords
- RFC 7493 - The I-JSON Message Format
- RFC 8949 - Concise Binary Object Representation (CBOR); Section 4.2 deterministic encoding
- CBOR Common Deterministic Encoding (CDE) - `draft-ietf-cbor-cde`
- RFC 9052 - CBOR Object Signing and Encryption (COSE)
- RFC 8032 - Edwards-Curve Digital Signature Algorithm (Ed25519)
- RFC 9162 - Certificate Transparency Version 2.0
- RFC 8785 - JSON Canonicalization Scheme (referenced for the optional JSON profile and for the numeric-precision rationale)
- in-toto attestation framework; IETF SCITT architecture (`draft-ietf-scitt-architecture`)
- W3C Verifiable Credentials Data Model
