# Provetrail Specification

**Version:** 0.1.0-draft
**Status:** DRAFT. This document is a working draft published for review. It is not final, and the on-the-wire format is not frozen until v0.1.0 is tagged. See the status note in the README.

## Conventions

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

Identifiers are written in `code font`. This document avoids implementation-specific detail except where a concrete grounding aids clarity.

A note on maturity: the cryptographic layer (Sections 4.2 and 4.3) is implemented and shipped with a verifier in the reference implementation, so a record can be cryptographically verified against a signing key today. The on-the-wire format is not yet frozen, and the golden conformance vectors are still being published into this repository, so the format is a working draft and MUST NOT be relied on as a production security control before the v0.1.0 freeze.

---

## 1. Scope and non-goals

### 1.1 In scope

A portable, third-party-verifiable record of **what an agent did and under what governance**, anchored to an append-only, tamper-evident event log, such that an independent party can verify the record without trusting the producer and without re-implementing the producer.

### 1.2 Non-goals

- **Not content provenance.** C2PA answers "is this media authentic and by whom." Provetrail answers "what actions did an agent take, in what order, under what authority, and can you prove the record is untampered." They are complementary layers.
- **Not a tool-connection protocol** (that is MCP) and **not an agent-to-agent transport** (that is A2A). Provetrail is the provenance layer those can carry or reference.
- **Not an identity system.** The `principal` of an event is an identity expressed in an external standard (for example a `did`, a verifiable credential, or an agent-identity record). Provetrail references identity; it does not define it.
- **Not a new language or runtime.** One record format, many independent verifiers.

---

## 2. The three standardizable primitives

### 2.1 The event envelope

The envelope is the wire format of one immutable, ordered event. An event has the following logical fields:

| Field | Type | Meaning |
|---|---|---|
| `stream` | string | The identifier of the ordered stream this event belongs to. |
| `seq` | int64 | Sequence number within the stream. MUST strictly increase between adjacent events. |
| `time` | int64 | The producer's recorded time, as Unix nanoseconds in UTC. Advisory; ordering is by `seq`, not `time`. |
| `type` | string | The event type, namespaced. |
| `actor` | string | The coarse category of who produced the event: `agent`, `human`, or `system`. This is a category, not an identity; see `principal`. |
| `payload` | object | The type-specific body. |
| `schema_version` | int | The schema version of `payload` for this `type`. |
| `causation_id` | string | OPTIONAL. The id of the event that caused this one, enabling exact causal replay. |
| `principal` | string | OPTIONAL. The external identity on whose authority the event was produced, expressed as a reference into an external identity standard (for example a `did`, a verifiable credential, or an agent-identity record). This is the identity-bearing field. |
| `origin_instance_id` | string | OPTIONAL. The producing runtime instance, distinguishing events emitted by different instances that write to the same logical stream. |
| `trace_id` | string | OPTIONAL. Distributed-trace correlation, so an operational trace and this record can be lined up. |
| `span_id` | string | OPTIONAL. Distributed-trace span correlation, as `trace_id`. |

The seven fields `stream`, `seq`, `time`, `type`, `actor`, `payload`, and `schema_version` are REQUIRED and MUST always be encoded, including when a value is empty. The five OPTIONAL fields are string-valued and MUST be omitted entirely when empty, and MUST be present when set. This omit-when-empty rule is normative rather than cosmetic: field presence changes the canonical bytes of Section 3, and therefore changes the leaf commitment and the signature over it. A producer that encodes an empty optional field, or omits a set one, produces bytes that will not reproduce the expected leaf.

Ordering within a stream is carried by `seq` alone. A record MAY carry a contiguous slice of a longer stream, so `seq` gaps between adjacent carried events are permitted; what a verifier MUST reject is `seq` that repeats or decreases, which is a reordering or replay rather than a window. Tamper-evidence is not a per-event field: each event's canonical bytes are committed as a leaf in the append-only Merkle log of Section 4, and the signed root over those leaves is what makes any alteration detectable. There is therefore no `prev_hash` field.

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

A Merkle log is only verifiable in another language if that language can reproduce the exact hashed leaf bytes. Provetrail resolves this with a hybrid rule.

### 3.1 Carry the bytes, rehash the bytes

- The proof artifact **carries the exact serialized bytes** of each event.
- A verifier **rehashes the bytes it is given**. It MUST NOT re-serialize the logical event in order to hash it. This makes cross-language verification trivial and removes any dependence on a verifier reproducing the producer's serializer.
- The canonicalization rule is ALSO specified (Section 3.2), so a verifier MAY OPTIONALLY re-derive canonical bytes from the logical event and confirm they match the carried bytes. A mismatch MUST be rejected: it indicates a producer carrying bytes that disagree with the logical content.

### 3.2 Canonical encoding

The canonical encoding is **deterministic CBOR** as defined by RFC 8949 Section 4.2 (Core Deterministic Encoding), with the following tightenings, which a conforming decoder MUST enforce:

- Duplicate map keys MUST be rejected.
- Indefinite-length items MUST be rejected.
- Bytes trailing a complete encoding MUST be rejected.
- A text string that is not valid UTF-8 MUST be rejected.

Core Deterministic Encoding already requires that map keys are sorted bytewise, that integers use their shortest form, and that floats use the shortest form that round-trips. The tightenings above close the remaining ambiguities that would let two distinct byte strings claim to be the same event. This profile is compatible with the direction of the CBOR Common Deterministic Encoding (CDE) work, which is tracked as informative; the normative reference is RFC 8949 Section 4.2 plus the four rules above, because that is what an implementation can conform to today.

Rationale for CBOR over canonical JSON:

- The load-bearing `seq` and `time` fields are 64-bit integers and may exceed 2^53. RFC 8785 (JSON Canonicalization Scheme) numbers are IEEE-754 doubles, whose exact-integer range ends at 2^53 regardless of signedness, so JCS cannot represent them without a string-encoding workaround; CBOR encodes integers exactly. `time` as Unix nanoseconds crosses 2^53 in the ordinary course of events, not as an edge case.
- The neighbouring transparency and signing standards Provetrail aligns with (Section 4) are CBOR and COSE based.

A non-canonical JSON projection of a record MAY be produced for human inspection or debugging. It is never hashed, never signed, and is not authoritative. A JSON profile that re-canonicalizes to CBOR before hashing is a valid interoperability path; a profile that hashes JSON independently is not, because it would create a second set of bytes claiming to be the same event.

---

## 4. The proof artifact

Provetrail assembles existing standards. It does not invent cryptography.

### 4.1 Event commitment

Each event's canonical bytes are committed as a leaf in the append-only Merkle log of Section 4.3. The leaf preimage is domain-separated and length-framed (the leaf is the hash of a fixed domain tag, the canonical byte length, and the canonical bytes), so two different events can never share a preimage. The hash function is SHA-256 (RFC 6962 leaf hashing) unless a later profile specifies otherwise. The signed root over these leaves, not a per-event back-pointer, is the tamper-evidence: altering, reordering, dropping, or inserting any event no longer reproduces the signed root.

### 4.2 Signing

Signing uses **COSE** (RFC 9052) over the canonical CBOR bytes. COSE is the CBOR-native signing standard used by the neighbouring transparency and content-provenance ecosystems and supports multiple signatures. Signatures are **Ed25519** (RFC 8032), carried under the fully-specified COSE algorithm identifier **-19** (`Ed25519`, RFC 9864); the earlier polymorphic identifier -8 (`EdDSA`) is deprecated by IANA and MUST NOT be produced. The protected content type of a signed checkpoint is `application/vnd.provetrail.checkpoint+cbor`; media type names live in the vendor tree (RFC 6838 Section 3.1) because unfaceted names in the standards tree require IESG action.

The signed checkpoint deliberately carries a **minimal protected header**: algorithm, content type, and key id, nothing else. In particular it does not carry the CWT Claims header (label 15) that RFC 9943 requires of a Signed Statement, so a checkpoint is not itself directly registrable in a SCITT Transparency Service. Registration is **indirect by design**: a party registering a checkpoint wraps or countersigns it as its own SCITT Signed Statement (media type `application/vnd.provetrail.statement+cose`), keeping the frozen checkpoint surface small and leaving issuer/subject identity to the layer that actually asserts it. Rationale: identity claims baked into the checkpoint would freeze a producer-identity scheme prematurely, and an independent attestation layer can add them later without changing checkpoint bytes.

A JSON-profile compatibility layer MAY sign using DSSE with pre-authentication encoding; this profile is secondary and non-authoritative.

### 4.3 Transparency and receipts

An append-only log of statements uses **RFC 9162** (Certificate Transparency v2) Merkle mechanics: inclusion proofs (a statement is in the log under a signed root) and consistency proofs (the log only ever appended between two signed roots). A record MAY carry a receipt demonstrating inclusion. An external transparency anchor MAY be used so that even the holder of the signing key cannot backdate a root.

### 4.4 Statement layering

The signed payload is a `run-provenance` statement (see [`predicates/run-provenance.md`](./predicates/run-provenance.md)). Under COSE it is carried as a signed statement; a JSON profile MAY carry it as an in-toto predicate. The predicate type identifier is descriptive and vendor-neutral.

### 4.5 Reuse map

| Layer | Reuse |
|---|---|
| Value model | I-JSON (RFC 7493), encoded as deterministic CBOR (RFC 8949 Section 4.2) |
| Signing | COSE (RFC 9052), Ed25519 (RFC 8032); DSSE+PAE as an optional JSON profile |
| Statement layering | SCITT-style signed statement (COSE); in-toto predicate as the JSON-profile analogue |
| Append-only log + proofs | RFC 9162 (Certificate Transparency v2) |
| Portable credentials (optional) | W3C Verifiable Credentials data model |

---

## 5. Conformance

Conformance is defined by the public test-vector suite and tier model in [`CONFORMANCE.md`](./CONFORMANCE.md). In summary, a verifier declares the tier it meets:

- **L1 Structural** - canonical-encoding conformance, schema validity, well-formed envelope, single-stream consistency, `seq` monotonicity, fold consistency. No cryptography required. There is no chain-link check at this tier, because there is no `prev_hash` field (Section 2.1); link integrity is the Merkle-root check at L2.
- **L2 Cryptographic** - signature validity, key binding, algorithm pinning, Merkle-leaf integrity over carried bytes (each event's leaf is committed under the signed root).
- **L3 Transparency** - inclusion and consistency proofs against signed roots; receipt validity.
- **L4 Governance-complete** - every side-effecting action has a matching admission record; recorded gate results are consistent with the action stream; outcome claims are bound to a check.

A verifier is Provetrail-conformant at a tier if and only if it accepts every valid vector and rejects every invalid vector at that tier with the registered failure code.

---

## 6. Relationship to other standards

Provetrail is designed to slot beside, not displace:

- **C2PA** secures content provenance; Provetrail secures execution provenance. An agent that produces media can carry both.
- **MCP / A2A** connect tools and agents; Provetrail records what was done across those connections.
- **Agent-identity standards** (`did`, verifiable credentials, agent passports) answer who an actor is and what it is authorized to do; Provetrail's `principal` field references them and records what that identity then did.

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
- RFC 8949 - Concise Binary Object Representation (CBOR); Section 4.2 Core Deterministic Encoding (normative for Section 3.2)
- CBOR Common Deterministic Encoding (CDE) - `draft-ietf-cbor-cde` (informative)
- RFC 9052 - CBOR Object Signing and Encryption (COSE)
- RFC 8032 - Edwards-Curve Digital Signature Algorithm (Ed25519)
- RFC 9162 - Certificate Transparency Version 2.0
- RFC 8785 - JSON Canonicalization Scheme (referenced for the optional JSON profile and for the numeric-precision rationale)
- in-toto attestation framework; IETF SCITT architecture (`draft-ietf-scitt-architecture`)
- W3C Verifiable Credentials Data Model
