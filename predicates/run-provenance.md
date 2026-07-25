# The `run-provenance` statement

**Version:** 0.1.0-draft
**Status:** DRAFT.

`run-provenance` is the Provetrail statement type: the signed assertion that a run's event stream is what it claims to be. It is intentionally a thin, neutral statement layered on existing standards, not a new envelope format. At v0.1 the statement is deliberately minimal: it names exactly the artifact the reference implementation signs and the conformance vectors pin, nothing more. Fields that are designed but not yet implemented anywhere are listed in the appendix as candidates for `/v0.2`, not asserted here.

## Type identifier

The predicate type identifier is descriptive and vendor-neutral:

```
https://w3id.org/provetrail/predicates/run-provenance/v0.1
```

(The identifier is the stable contract. It is a permanent identifier on the W3C Permanent Identifier service (`w3id.org`) that redirects to the current canonical reference, so it stays fixed even if the hosting moves. It is not bound to any single implementation.)

### URI versioning policy

The versioned path is immutable once its specification version freezes: after the v0.1.0 freeze, the document `/v0.1` names may be clarified but never changed in meaning. Any breaking change to the statement mints a new path (`/v0.2`); at specification 1.0 the URI becomes `/v1`, and verifiers accept both `/v0.x` and `/v1` during migration. After 1.0, minor specification versions never change the URI and follow the in-toto monotonic principle: a statement valid under `/v1` at 1.0 remains valid under `/v1` at every later 1.x. Old version paths stay resolvable forever. Any future JSON-profile field names use lowerCamelCase, per in-toto guidance.

## The v0.1 statement: the signed checkpoint

The v0.1 `run-provenance` statement **is the signed checkpoint** of specification Section 8.4: a COSE_Sign1 (tag 18) whose protected header carries algorithm `-19` (Ed25519), the content type `application/vnd.provetrail.checkpoint+cbor`, and the signing key id, and whose payload is the canonical CBOR map:

| Field | Meaning |
|---|---|
| `root` | The signed RFC 9162 Merkle root (32 bytes, SHA-256) over the stream's events, the commitment any inclusion proof reconstructs. |
| `size` | The event count the signed root covers: the position in the stream this statement attests to. The wire field is `size`; informal prose has called this the stream "head," but normative text uses `size` (see [`GLOSSARY.md`](../GLOSSARY.md)). |
| `origin` | The identifier of the log (the run/stream scope) that produced the root, binding the root to its log so it cannot be replayed against another. |

The statement travels inside the sealed run record (`{events, checkpoint}`, specification Section 8.5), as a standalone checkpoint, or embedded in a proof artifact (Section 8.6). Every field above is exercised by published conformance vectors.

Registration in a SCITT Transparency Service is indirect by design (specification Section 4.2): the checkpoint carries a minimal protected header with no CWT Claims, and a registering party wraps or countersigns it as its own Signed Statement (`application/vnd.provetrail.statement+cose`, reserved). A JSON-profile carrier is RESERVED for a post-freeze minor version; at v0.1 the COSE/CBOR form is the only specified carrier.

## What a verifier checks

Exactly the published conformance checks, by tier:

1. The COSE signature verifies under a key in the verifier's keyring, with the pinned algorithm and content type (L2).
2. The carried event bytes are canonical, ordered, and rehash to leaves that reconstruct the signed `root` at the signed `size` (L2).
3. A standalone inclusion or consistency proof reconstructs, or connects, signed roots (L3).
4. The recorded events satisfy the admission and outcome-binding invariants of specification Sections 8.7-8.8 (L4).

## What it deliberately does not assert

`run-provenance` does not assert that the run was "good," "safe," or "successful." It asserts what happened, in what order, under what recorded governance, in a form an independent party can verify. Quality or policy judgements are layered on top by whoever consumes the record.

## Appendix: candidate fields for `/v0.2`

These fields were part of the original statement design. None is implemented by any producer, signed by any reference path, or exercised by any vector, so none is part of `/v0.1`. They are recorded here so the design intent survives without the permanent identifier naming an unimplemented artifact.

| Candidate field | Intent | What must exist first |
|---|---|---|
| `run_id` | A stable identifier for the run the statement is about, distinct from the log-scoping `origin`. | A producer-side identity scheme for runs. |
| `principal` | The external identity on whose authority the run executed, lifted from the event level to the statement level. | A ruling on how statement-level identity interacts with the per-event `principal` field. |
| `fold_digest` | A digest of the deterministic fold of the stream, binding an attested final state to the events. | A declared-fold mechanism: a normative, cross-producer fold function identified by name. No such definition exists anywhere yet, which is why the field is absent rather than underspecified. |
| `governance` | A precomputed summary of admission and gate records, so an L4 verdict is reachable without replaying every event. | A canonical summary encoding plus vectors proving it consistent with the event stream. |
