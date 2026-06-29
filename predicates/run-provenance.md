# The `run-provenance` statement

**Version:** 0.1.0-draft
**Status:** DRAFT.

`run-provenance` is the Provetrail statement type: the signed payload that asserts what an agent run did and under what governance. It is intentionally a thin, neutral statement layered on existing standards, not a new envelope format.

## Type identifier

The predicate type identifier is descriptive and vendor-neutral:

```
https://provetrail.org/predicates/run-provenance/v0.1
```

(The identifier is the stable contract; the domain hosting it is the canonical reference. It is not bound to any single implementation.)

## Carriers

The same logical statement can be carried two ways:

- **Primary (COSE / CBOR):** a SCITT-style signed statement. The protected header binds the statement and its metadata; the payload is the canonical-CBOR `run-provenance` body. This is the authoritative form.
- **JSON profile (optional, non-authoritative):** an in-toto attestation whose `predicateType` is the identifier above and whose `predicate` is the same body. Provided for compatibility with JSON supply-chain tooling.

## Statement body

The body references a run and binds it to its event stream:

| Field | Meaning |
|---|---|
| `run_id` | The identifier of the run this statement is about. |
| `stream` | The event stream identifier (Section 2.1 of the spec). |
| `head` | The `seq` and `prev_hash`-chain head this statement attests to. |
| `root` | OPTIONAL. The signed transparency-log root (RFC 9162) the stream is included under. |
| `actor` | The run's principal actor, as an external identity reference (`did`, verifiable credential, or agent-identity record). Provetrail references identity; it does not define it. |
| `fold_digest` | A digest of the deterministic fold of the stream up to `head`, so a verifier can bind the attested final state to the events. |
| `governance` | A summary of the admission and gate records present (Sections 2.2 and 2.3 of the spec), sufficient for an L4 verifier to check that no side-effecting action ran without admission. |
| `schema_version` | The schema version of this statement body. |

## What a verifier checks

Per the conformance tiers:

1. The carried event bytes rehash to the declared chain (`head`, `prev_hash` links).
2. The COSE signature(s) verify under the key bound to `actor`.
3. If `root` is present, the inclusion proof reconstructs the signed root (L3).
4. `fold_digest` matches the verifier's own re-fold of the carried events (binds the claim to what actually happened).
5. The `governance` summary is consistent with the recorded admission and gate events: no side-effecting action without a preceding admission, no executed-after-deny, no contradicted gate result (L4).

## What it deliberately does not assert

`run-provenance` does not assert that the run was "good," "safe," or "successful." It asserts what happened, in what order, under what recorded governance, in a form an independent party can verify. Quality or policy judgements are layered on top by whoever consumes the record.
