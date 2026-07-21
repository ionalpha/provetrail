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

Core Deterministic Encoding already requires that map keys are sorted bytewise, that integers use their shortest form, and that floats use the shortest form that round-trips. The tightenings above close the remaining ambiguities that would let two distinct byte strings claim to be the same event. This profile is compatible with the direction of the CBOR Common Deterministic Encoding (CDE) work (`draft-ietf-cbor-cde-13`, parked and expired as of 2026; informative only); the normative reference is RFC 8949 Section 4.2.1 plus the four rules above, because that is what an implementation can conform to today. Section 8.1 completes the profile normatively.

Rationale for CBOR over canonical JSON:

- The load-bearing `seq` and `time` fields are 64-bit integers and may exceed 2^53. RFC 8785 (JSON Canonicalization Scheme) numbers are IEEE-754 doubles, whose exact-integer range ends at 2^53 regardless of signedness, so JCS cannot represent them without a string-encoding workaround; CBOR encodes integers exactly. `time` as Unix nanoseconds crosses 2^53 in the ordinary course of events, not as an edge case.
- The neighbouring transparency and signing standards Provetrail aligns with (Section 4) are CBOR and COSE based.

A non-canonical JSON projection of a record MAY be produced for human inspection or debugging. It is never hashed, never signed, and is not authoritative. A JSON profile that re-canonicalizes to CBOR before hashing is a valid interoperability path; a profile that hashes JSON independently is not, because it would create a second set of bytes claiming to be the same event.

---

## 4. The proof artifact

Provetrail assembles existing standards. It does not invent cryptography.

### 4.1 Event commitment

Each event's canonical bytes are committed as a leaf in the append-only Merkle log of Section 4.3. The tree is an RFC 6962 / RFC 9162 SHA-256 Merkle tree whose *entry* is the domain-separated, length-framed preimage of the event's canonical bytes — the exact construction, with every constant, is Section 8.3. Domain separation and length framing mean two different events can never share a preimage, and because they live inside the entry the tree matches the `RFC9162_SHA256` verifiable data structure, unlocking RFC 9942 COSE Receipt interoperability. The signed root over these leaves, not a per-event back-pointer, is the tamper-evidence: altering, reordering, dropping, or inserting any event no longer reproduces the signed root.

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

- **L1 Structural** - canonical-encoding conformance, schema validity, well-formed envelope, single-stream consistency, `seq` monotonicity. No cryptography required. There is no chain-link check at this tier, because there is no `prev_hash` field (Section 2.1); link integrity is the Merkle-root check at L2.
- **L2 Cryptographic** - signature validity, key binding, algorithm pinning, Merkle-leaf integrity over carried bytes: each event's leaf is committed under the signed root, and a sealed run record's carried events must reproduce the signed root. Run-record root integrity therefore lives at this tier.
- **L3 Transparency** - standalone inclusion and consistency proofs against signed roots; receipt validity.
- **L4 Governance-complete** - every side-effecting action has a matching admission record; outcome claims are bound to a check. Gate-result consistency and containment-downgrade detection are deferred beyond this version (see `CONFORMANCE.md` Section 5).

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

## 8. Wire format (normative)

This section pins every constant a verifier needs, so an independent implementation can be built from this document alone, without reading the reference implementation or the client verifiers. The conformance vectors embody exactly these rules; machine-readable CDDL for each structure is published in [`cddl/`](./cddl/) and validated against the vectors in CI. Where CDDL cannot express a rule (encoding-level constraints, canonical form), the text here is normative.

### 8.1 Deterministic-encoding profile

Every hashed or signed structure is encoded as **deterministic CBOR**: RFC 8949 Section 4.2.1 (Core Deterministic Encoding Requirements), which requires shortest-form integer and length heads, definite lengths only, and map keys sorted bytewise on their *encoded* form. A conforming decoder MUST additionally enforce the four tightenings of Section 3.2: reject duplicate map keys, indefinite-length items, trailing bytes, and invalid UTF-8. For completeness of the profile: there is no integer/float unification (an integral value encoded as a float is a different value), and since floating-point values do not occur in any structure at this version, no float canonicalization rule is exercised; if a future version admits floats, it must state one. The parked CBOR Common Deterministic Encoding draft (`draft-ietf-cbor-cde-13`) is compatible in direction and cited informatively only.

The load-bearing consequence: for any structure in this section, decoding and canonically re-encoding MUST reproduce the input bytes exactly. A verifier that performs this re-derivation check enforces the whole profile at once; the `enc.non_canonical_cbor` and `record.non_canonical` codes name its failures.

### 8.2 Event envelope

An event is a CBOR map with text-string keys. Seven fields are REQUIRED, five are OPTIONAL with the omit-when-empty rule of Section 2.1. In canonical (bytewise) key order over the minimal envelope: `actor`, `payload`, `schema_version`, `seq`, `stream`, `time`, `type`; the optional fields `causation_id`, `origin_instance_id`, `principal`, `span_id`, `trace_id` sort among them by the same rule when present.

| Key | CBOR type | Constraint |
|---|---|---|
| `stream` | tstr | MAY be empty. |
| `seq` | int (int64) | MUST be >= 1; strictly increasing between adjacent carried events; gaps permitted. |
| `time` | int (int64) | Unix nanoseconds UTC. Advisory; any int64 value is well-formed on the wire. |
| `type` | tstr | MAY be empty. |
| `actor` | tstr | Closed category: exactly `agent`, `human`, or `system`. Any other value MUST be rejected (`enc.invalid_actor`). |
| `payload` | map | tstr keys; value model below. Always present, possibly empty. |
| `schema_version` | int | The payload schema version for this `type`. |

An unknown envelope field MUST be rejected. This follows from the canonical-form rule — no canonical event encoding contains one — and the conformance suite pins it (`invalid.schema.unknown_field.01` rejects as `enc.non_canonical_cbor`). A required field whose value is the empty string is well-formed: required fields MUST be encoded even when empty (Section 2.1).

**Payload value model.** A payload value is one of: tstr, bstr, int (int64 range), bool, null, an array of payload values, or a map with tstr keys and payload values. Floating-point values and CBOR tags MUST NOT be produced at this version; no published vector contains either. This is the I-JSON (RFC 7493) value model plus byte strings and full-int64 integers; in any JSON projection a bstr is represented as base64url (RFC 4648 Section 5, unpadded), and integers beyond 2^53 lose exactness, which is one reason a JSON projection is never hashed (Section 3.2).

### 8.3 Merkle profile

The log is an RFC 6962 / RFC 9162 Merkle tree over SHA-256 whose *entry* for each event is the domain-separated, length-framed preimage of the event's canonical bytes:

```
entry = "provetrail/event/v1\n" || uint64-BE(len(canonical)) || canonical
leaf  = SHA-256(0x00 || entry)
node  = SHA-256(0x01 || left || right)
empty = SHA-256("")            ; the root of an empty tree
```

The domain tag is the 20-byte ASCII string `provetrail/event/v1\n` (terminating newline included); the length is an unsigned 64-bit big-endian integer counting the canonical bytes. Because the domain tag and length framing live *inside* the entry, the tree is byte-for-byte an RFC 6962-conformant tree over `entry`, and therefore matches the `RFC9162_SHA256` verifiable data structure (vds = 1) of the COSE Receipts registry: a record MAY carry an RFC 9942 COSE Receipt for a checkpoint, and an RFC 9162/9942-conformant proof verifier needs no Provetrail-specific tree code. Inclusion proofs follow RFC 9162 Section 2.1.3.1 and consistency proofs Section 2.1.4.1, over the leaf definition of Section 2.1.1 with the entry defined above.

### 8.4 COSE profile

A checkpoint signature is a **COSE_Sign1** (RFC 9052), and the CBOR tag 18 is REQUIRED on the wire. The protected header is exactly three claims — no more, no fewer:

| Label | Value |
|---|---|
| 1 (alg) | **-19** (`Ed25519`, fully-specified, RFC 9864). The deprecated polymorphic `EdDSA` (-8) MUST NOT be produced and MUST be rejected. |
| 3 (content type) | `application/vnd.provetrail.checkpoint+cbor` |
| 4 (kid) | The signing key's identifier, as a byte string, resolved against the verifier's keyring. |

The unprotected header MUST be empty (`{}`). The signature input is the `Sig_structure` of RFC 9052 Section 4.4 with context `"Signature1"` and a zero-length `external_aad` (`h''`). The COSE structure itself is encoded under the Section 8.1 profile. Multi-signature (`COSE_Sign`) is deferred to a future version. Algorithm agility: algorithms are registry-pinned per profile version — SHA-256 and Ed25519/-19 at v0.1 — and a future profile version can add, for example, ML-DSA (RFC 9964, -48/-49/-50) without changing this one.

The checkpoint payload (the signed bytes) is a CBOR map, canonical key order `root`, `size`, `origin`:

```
checkpoint-payload = { root: bstr .size 32, size: uint, origin: tstr }
```

All three fields are REQUIRED — including `origin`, which scopes the root to the log that produced it. A payload that is not the exact canonical encoding of this map (missing or extra field, non-canonical key order, a root that is not 32 bytes) MUST be rejected (`sign.checkpoint_decode`).

### 8.5 Record container

A sealed run record is a CBOR map of exactly two fields, canonical key order `events`, `checkpoint`:

```
sealed-run = { events: [ + bstr ], checkpoint: bstr }
```

Each `events` entry is one event's canonical bytes; `checkpoint` is the tagged COSE_Sign1 of Section 8.4. The container is closed: an extra field, a duplicated key, indefinite-length framing, non-minimal heads, or trailing bytes MUST be rejected (`record.decode` / `record.non_canonical`). A record with zero events MUST be rejected (`record.empty`) even when its checkpoint validly signs size 0; the empty-tree root exists so that an empty *checkpoint* is verifiable (Section 8.3), but a *record* must attest at least one event. The event count MUST equal the signed `size` (`record.size_mismatch`) and the events MUST rebuild the signed `root` exactly (`record.root_mismatch`).

### 8.6 Proof artifacts

A standalone single-event proof is a CBOR map, canonical key order `size`, `index`, `canonical`, `inclusion`, `checkpoint`:

```
event-proof = { size: uint, index: uint, canonical: bstr,
                inclusion: [ * bstr .size 32 ], checkpoint: bstr }
```

`index` is zero-based and MUST be less than `size` (`record.index_out_of_range`); `size` MUST equal the signed size (`record.size_mismatch`); an inclusion path shorter than the tree shape requires MUST be rejected (`merkle.missing_node`); the path MUST reconstruct the signed root per RFC 9162 Section 2.1.3.2 (`merkle.inclusion_invalid`).

A consistency proof between two signed checkpoints of the same log is a CBOR map, canonical key order `after`, `proof`, `before`:

```
consistency-proof = { after: bstr, proof: [ * bstr .size 32 ], before: bstr }
```

`before` and `after` are each a tagged COSE_Sign1 checkpoint; `proof` is the RFC 9162 Section 2.1.4.2 consistency path from the `before` tree to the `after` tree (`merkle.consistency_invalid` on failure).

### 8.7 L4 semantics: governance

L4 verification runs over the events of an already-verified record (Sections 8.2-8.5): it assumes authenticity and order, and checks what the signed bytes then mean. Its vocabulary is ordinary events — reserved `type` values and payload keys, not new wire structures.

**The admission lifecycle** is the event family:

| `type` | Meaning | Payload |
|---|---|---|
| `dispatch.start` | The action named by `call` was admitted and began. | `call`: int |
| `dispatch.end` | The action named by `call` completed. | `call`: int |
| `dispatch.rejected` | The action named by `call` was refused admission. | `call`: int |

`call` is an integer correlation id pairing one invocation's lifecycle events. A verifier MUST read it tolerantly across the integer representations a CBOR or JSON round trip can produce (an integral float is accepted as its integer value), so a record remains verifiable after passing through a JSON store.

**What "side-effecting" means at this version:** exactly the `dispatch.*` family. A producer marks an action as side-effecting — and thereby subject to the admission invariants — by emitting its lifecycle through this family. Events of any other `type` are outside governance scope at v0.1; a future version may widen the family, never silently reinterpret existing types.

**The invariants a verifier MUST enforce:**

1. **Admission completeness** (`gov.unadmitted_action`): every `dispatch.end` MUST carry a well-formed `call` that a `dispatch.start` with the same `call` admitted *earlier in the stream*. A completion with a missing or malformed `call` is equally unadmitted — it claims a completion no admission can be matched to, and the check fails closed.
2. **Denial is final** (`gov.admission_denied_but_executed`): no `call` may appear as both `dispatch.rejected` and `dispatch.end`, in either order. A denial after the fact contradicts the execution just as a denial before it does.

A `dispatch.start` or `dispatch.rejected` without a well-formed `call` is inert: it admits or refuses nothing.

### 8.8 L4 semantics: ground truth

Outcome binding separates two properties that "verifiable" usually conflates: integrity asks whether these are the genuine, unaltered bytes from an identified principal; outcome binding asks whether a claim of success carries a machine-checkable reference to a check that actually passed. A record can be perfectly signed and prove nothing.

**The vocabulary:**

| `type` | Meaning | Payload |
|---|---|---|
| `check.recorded` | The verdict of a verification. | `check`: int (the check's own id), `passed`: bool |
| `outcome.recorded` | A claimed result of a run or step. | `result`: tstr; `check`: int (the grounding check's id) when bound |

**The binding rule a verifier MUST enforce** (`shallow.no_ground_truth`): every `outcome.recorded` whose `result` is `"success"` MUST carry a `check` reference to a `check.recorded` event *in the same record* whose `passed` is `true`. The check may appear before or after the outcome — the binding is over the record, not the ordering. A success with no `check` key, a reference to a check the record does not contain, or a reference to a check whose `passed` is not `true`, is rejected. The flagship reject vector is precisely a record whose only event is `outcome.recorded {"result": "success"}`: signed, not proven. An outcome whose `result` is not `"success"` requires no backing check — a recorded failure or partial result is never penalized for honesty. A `check.recorded` with a malformed `check` id, or whose `passed` is absent or not `true`, grounds nothing.

**Omission over false attestation.** A control that did not run MUST be represented by the absence of its record, never by a present record asserting a result the control did not produce. Where no ground-truth check exists for a task, a conformant record says so by carrying no binding — turning "no ground truth" from a silent default into a machine-detectable, auditable state. This rule is what makes the distinction between signed and proven detectable rather than a matter of presentation.

**Independence, to the extent the wire carries it.** The check's own envelope attributes it: `actor` categorizes who recorded it and `principal` names the authority it was recorded under (Section 2.1). A verifier MAY reject, by policy, a binding whose check was performed by the same authority that performed the action. The wire makes the attribution visible; the independence judgment is policy.

### 8.9 What L4 does and does not claim

Outcome binding is not a correctness oracle. Provetrail standardizes the binding and its verification, not the quality of the bound check: a gameable check that passes still verifies. What the standard guarantees is narrower and more durable — the presence or absence of a binding, and the attribution of the bound check, are machine-checkable, so a gameable check becomes a named, attributable artifact rather than an invisible gap, and relying parties can set policy on the distinction. L4 is also unreachable by wrappers: a post-hoc converter around a runtime that did not emit admission and check events has nothing truthful to bind, and fabricating those events requires the signing authority — which is an attributable act, not a presentation choice.

L4 at this version means exactly the two invariants of Section 8.7 and the binding rule of Section 8.8. Gate-result consistency, containment-downgrade detection, self-graded-check rejection, and empty-governance flagging are named and explicitly deferred, identically in `CONFORMANCE.md` Section 5: they are not part of conformance at this version, have no published vectors, and a verifier is not measured on them.

---

## 9. Security considerations

This chapter calibrates every claim this repository makes: nothing elsewhere in the specification, the conformance documents, or the client documentation may claim more than this chapter supports.

### 9.1 Trust model

Verification proves that the carried bytes are the exact bytes committed under a root that a key in the verifier's keyring signed, that the events are canonical and ordered, and — at L4 — that the recorded events satisfy the admission and outcome-binding invariants of Sections 8.7-8.8. It does not prove that the events describe what actually happened: the record is only as strong as the substrate that emits it. Provetrail's guarantees hold when the record is emitted by the component that *mediated* the action, not by the agent narrating itself. A record emitted by an unconstrained agent about its own behaviour can satisfy L1-L3 and still misrepresent what happened; L4 exists precisely to make that difference checkable, and a relying party SHOULD treat an L1-L3-only record as attestation of bytes, not proof of outcome.

Trust does not disappear in these systems; it moves. A governed runtime that emits the record asks a relying party to trust the runtime — a smaller and better-anchored trust than trusting an unbounded, non-deterministic agent to report on itself, because a runtime is a small, fixed, inspectable component whose records are tamper-evident and independently verifiable. A compromised or dishonest runtime is therefore detectable in a way a self-reporting agent is not.

**The keyring.** A verifier obtains trusted public keys out of band and indexes them by the `kid` the protected header carries (Section 8.4). The `kid` is a lookup handle, not an identity: the binding of a key to a real-world producer identity is out of scope and MUST be established externally (a deployment's key distribution, an identity system referenced via `principal`). Key rotation at v0.1 is keyring membership: adding a key under a `kid` rotates it, removing it revokes it, and there is no in-band rotation or revocation signal. The conformance suite's published test key is test material only and MUST NOT be trusted in production.

### 9.2 Threat matrix

Verdicts: **prevents** (the attack cannot yield an accepting verification), **detects** (verification fails when the attack occurred), **limits** (partial defense; residual stated), **does not address** (out of scope at this version; mitigation named where one exists).

| Threat | Verdict | Mechanism / residual |
|---|---|---|
| Forged record (no keyring key) | prevents | COSE signature over the root; `sign.unknown_key`, `sign.signature_invalid`. |
| Altered event bytes | detects | Leaf rehash no longer reproduces the signed root (`record.root_mismatch`). |
| Reordered events | detects | `seq` strict monotonicity plus root mismatch (`chain.non_monotonic_seq`, `record.root_mismatch`). |
| Dropped or inserted events | detects | Count vs signed `size`, and the root (`record.size_mismatch`, `record.root_mismatch`). |
| Truncation: a genuinely signed *earlier* record presented as current | does not address | Freshness is out of scope at v0.1. A stale record verifies, because it is authentic. Mitigations: consistency proofs between checkpoints (Section 8.6) and an external transparency anchor; a relying party needing freshness MUST obtain the latest checkpoint out of band. |
| Equivocation / split-view logs | limits | Consistency proofs detect divergence *between two presented roots*; a signer-operator can still show different parties different histories. Full defense requires registration in an external Transparency Service (RFC 9943). |
| Backdating a root | limits | A self-signed root can claim any `time`. External anchoring bounds when a root could have existed; a deployment that anchors only to self-signed roots retains this residual trust in the operator and SHOULD say so. |
| Signing-key compromise | does not address | Records signed before revocation are indistinguishable from honest ones. Keyring removal stops acceptance of new records; an external anchor bounds the forgery window. There is no in-band revocation at v0.1. |
| Cross-stream / cross-record splicing | prevents | The checkpoint's `origin` binds the signed root to the log that produced it, and events carry `stream`; a root replayed against another log's events fails (`record.root_mismatch`, `chain.stream_mismatch`). |
| Parser differentials across languages | limits | The deterministic profile, the carry-the-bytes rule, and the canonical re-derivation check remove the ambiguity classes; the mutant-derived vectors (duplicate keys, indefinite lengths, non-minimal heads, trailing bytes, type confusion) pin verifier agreement. Residual: a verifier outside the conformance suite can still diverge — which is what conformance claims are for. |
| PII / secrets in payloads | does not address | v0.1 has no redaction mechanism; payload content is the producer's responsibility. See Section 9.4. |
| Verifier misconfiguration (claiming a tier it does not enforce) | limits | Reject vectors make a false tier claim falsifiable: a verifier claiming a tier is measured against every reject vector at that tier. The claim discipline itself is policy (`CONFORMANCE.md`). |
| Producer self-checking (gamed L4) | limits | Independence attribution (Section 8.8): the check's `actor`/`principal` are in signed bytes, so a self-graded binding is visible and rejectable by policy, not prevented. |

### 9.3 Limits of the outcome binding

A bound check is not a proof of correctness. Checks are domain-specific, frequently absent, and where present can be gamed: a check that verifies only a narrow extensional property admits false positives. Provetrail does not claim to eliminate this. It makes three things checkable instead: whether a success is bound to any check at all; whether the bound check is independent of the acting authority; and the identity of the check, so that a gameable check is an attributable, named artifact rather than a silent gap. A relying party retains responsibility for deciding which checks it trusts. The honest posture, enforced by the omission-over-false-attestation rule (Section 8.8), is that an unproven claim is marked unproven rather than dressed as a result.

### 9.4 Selective disclosure and redaction

v0.1 defines no redaction mechanism: a record is disclosed whole, and producers MUST NOT place content in payloads that cannot be disclosed to every intended verifier. Any future redaction mechanism is constrained in advance: an elision MUST preserve the leaf commitment so that inclusion under the signed root still verifies; a verifier MUST NOT treat a well-formed elision as evidence of tampering; and a producer MUST NOT use elision to remove a control record that the omission-over-false-attestation rule requires to be absent-or-true.

---

## References

- RFC 2119 / RFC 8174 - Requirement keywords
- RFC 7493 - The I-JSON Message Format
- RFC 4648 - Base16, Base32, and Base64 Data Encodings (base64url, for JSON projections of byte strings)
- RFC 8949 - Concise Binary Object Representation (CBOR); Section 4.2.1 Core Deterministic Encoding Requirements (normative for Sections 3.2 and 8.1)
- CBOR Common Deterministic Encoding (CDE) - `draft-ietf-cbor-cde-13` (informative; parked and expired as of 2026)
- RFC 9052 - CBOR Object Signing and Encryption (COSE)
- RFC 8032 - Edwards-Curve Digital Signature Algorithm (Ed25519)
- RFC 9864 - Fully-Specified Algorithms for JOSE and COSE (Ed25519 as COSE algorithm -19; deprecates -8)
- RFC 6838 - Media Type Specifications and Registration Procedures (vendor tree, Section 3.1)
- RFC 6962 - Certificate Transparency (the Merkle tree construction the entry profile of Section 8.3 conforms to)
- RFC 9162 - Certificate Transparency Version 2.0 (Sections 2.1.1, 2.1.3.x, 2.1.4.x; normative for Section 8.3)
- RFC 9942 - COSE Receipts (`RFC9162_SHA256`, vds = 1)
- RFC 9943 - An Architecture for Trustworthy and Transparent Digital Supply Chains (SCITT)
- RFC 9964 - ML-DSA for COSE (referenced by the algorithm-agility statement of Section 8.4)
- RFC 8785 - JSON Canonicalization Scheme (referenced for the optional JSON profile and for the numeric-precision rationale)
- in-toto attestation framework
- W3C Verifiable Credentials Data Model
