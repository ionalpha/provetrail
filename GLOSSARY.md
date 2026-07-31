# Provetrail glossary

**Version:** 0.1.0
**Status:** Companion to specification v0.1.0.

One definition per term, so `SPEC.md`, `CONFORMANCE.md`, and `predicates/run-provenance.md` use the same words for the same things. Where a term names a wire field, the field name is authoritative and is given in backticks; informal synonyms are noted so they stop drifting into normative text. The specification section that fixes each term is cited.

## Core record model

- **event** - one immutable, ordered record of something that happened in a run: the wire unit defined by the envelope of `SPEC.md` Section 8.2. Carries `stream`, `seq`, `time`, `type`, `actor`, `payload`, `schema_version`, and optional causal-linkage fields.
- **stream** - the identifier (`stream`) that groups events belonging to one run or one logical sequence. Events within a stream carry strictly increasing `seq`. A record may carry a window of a longer stream, so `seq` gaps are permitted.
- **record** - the sealed container `{events, checkpoint}` of `SPEC.md` Section 8.5: the carried event bytes plus the signed checkpoint whose root they reproduce. "Record" is the portable artifact a verifier is handed; it is not a synonym for a single event.
- **container** - the closed CBOR framing of a record (Section 8.5). A container is a fixed, closed shape: unknown container kinds are rejected (`record.decode`), which is what lets a future redacted-record form be a new kind rather than a reinterpretation of this one.
- **checkpoint** - the signed commitment of `SPEC.md` Section 8.4: a COSE_Sign1 (tag 18) over the canonical payload map `{ root, size, origin }`. The checkpoint is what a signature covers; the events are what it commits to.
- **statement** - a thin, signed assertion layered on the checkpoint, identified by a predicate type. At v0.1 the `run-provenance` statement *is* the signed checkpoint (`predicates/run-provenance.md`); no separate statement envelope is defined.
- **payload** - the per-event application data map (`payload`) inside an event envelope, distinct from the checkpoint payload.

## Checkpoint fields

- **`root`** - the RFC 9162 Merkle root (32 bytes, SHA-256) over a stream's events; the commitment any inclusion proof reconstructs (`SPEC.md` Section 8.3, 8.4).
- **`size`** - the event count the signed `root` covers. Informal prose has called this "the head" of the stream; the wire field is `size`, and normative text uses `size` only (`SPEC.md` Section 8.4).
- **`origin`** - the identifier of the log (the run/stream scope) that produced the root, binding a root to its log so it cannot be replayed against another (`SPEC.md` Section 8.4; `predicates/run-provenance.md`).

## Identity and authority

- **actor** - the coarse, closed category of who produced an event: `agent`, `human`, or `system` (`SPEC.md` Section 2.1). A category, not an identity.
- **principal** - the OPTIONAL external identity on whose authority an event was produced (`SPEC.md` Section 2.1). The identity-bearing field; it references whatever identity standard the deployment uses.
- **keyring** - the set of public keys a verifier trusts. The conformance `crypto/` vectors are signed under a single fixed, test-only Ed25519 key published in `vectors/crypto/manifest.json` under `keyring`.

## Proofs and transparency

- **leaf** - the per-event commitment `SHA-256(0x00 || entry)` over the domain-separated, framed entry (`SPEC.md` Section 8.3). The leaf hash can always stand in for the event bytes, which is what the reserved redaction path relies on.
- **inclusion proof** - an RFC 9162 Section 2.1.3 path that reconstructs a signed `root` from one leaf, proving an event is committed under that root (`SPEC.md` Section 8.6).
- **consistency proof** - an RFC 9162 Section 2.1.4 path proving one signed root is an append-only extension of an earlier one (`SPEC.md` Section 8.6).
- **receipt** - an RFC 9942 COSE Receipt a record MAY carry for a checkpoint (`SPEC.md` Section 6, 8.6).

## Conformance vocabulary

- **suite** - the published conformance vector set (`vectors/`) plus its manifests and the failure-code registry. The suite operationally defines the standard (`CONFORMANCE.md`).
- **tier** - one of the four conformance levels **L1** (structural), **L2** (cryptographic), **L3** (transparency), **L4** (governance-complete), defined in `CONFORMANCE.md` Section 3. A conformance claim MUST name an L-tier.
- **public vocabulary** - the three-word shorthand *integrity*, *governance*, *ground truth*, which maps onto the tiers exactly one way: integrity = L1-L3, governance and ground truth = L4 (`CONFORMANCE.md` Section 3). It is communication, not a second tier model.
- **verifier** - an implementation that checks a record against the suite. A verifier declares the highest tier it meets.
- **producer** - an implementation that emits records. A producer is conformant if every record it emits is accepted by a conformant verifier. Producer-specific vector sets are deferred beyond this version (`CONFORMANCE.md` Section 1, 4).
- **failure code** - a stable, dotted, layer-prefixed identifier for a specific rejection reason, published in `registry.json` and `CONFORMANCE.md` Section 6. A conformant verifier emits the registered code, never a free-form string.
- **predicate** - a versioned statement type named by a permanent URI (`https://w3id.org/provetrail/predicates/run-provenance/v0.1`), governed by the URI versioning policy in `predicates/run-provenance.md`.

## The name

- **provetrail** - the project name is the only short token the standard defines. There is no separate media-type token, CLI verb, or header abbreviation: media types are `application/vnd.provetrail.*`, the domain-separation tag is `provetrail/event/v1\n`, the client packages are named `provetrail`, and the reference verifier is invoked as `flynn spine verify`. This is a settled ruling (v0.1): no new short token is minted, so the question does not resurface.
