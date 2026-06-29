# Provetrail conformance vectors

The language-neutral evidence a verifier is tested against. A verifier is conformant
at a tier if and only if it reaches the declared verdict for every vector at that
tier, and for a rejection emits the registered failure code (see
[`../CONFORMANCE.md`](../CONFORMANCE.md)).

Every vector is generated deterministically by the reference implementation (fixed
keys, fixed events, no wall clock, no randomness), so the files are reproducible byte
for byte and a verifier in any language can be checked against the same bytes. Vectors
are never hand-authored: a valid vector is produced by the real signing path, and an
invalid vector is a valid record with exactly one documented mutation applied.

## Layout

```
structural/        L1: canonical event encodings and stream ordering (no cryptography)
  manifest.json    the index: each vector's id, verdict, failure code, and files
  valid/           encodings a conformant verifier MUST accept
  invalid/         encodings a conformant verifier MUST reject, one defect each
crypto/            L2-L4: signed checkpoints, run records, proofs, governance, ground truth
  manifest.json    the index, plus the keyring (the public key the vectors are signed under)
  valid/           records a conformant verifier MUST accept
  invalid/         records a conformant verifier MUST reject, one defect each
```

Each manifest entry names the vector's `id`, its `tier`, the `kind` of artifact (which
selects the check that applies), the expected verdict (`accept` or `reject`), and for a
rejection the `failure_code`.

## Tiers covered

- **structural/** (L1): canonical CBOR encoding, well-formedness, and `seq` ordering.
- **crypto/** (L2-L4): a signed checkpoint (`checkpoint`), a full signed run record
  (`run`), a single-event inclusion proof (`event_proof`), a consistency proof
  (`consistency`), governance (`governance`: no action ran without a preceding
  admission), and ground truth (`ground_truth`: a claimed success is bound to a
  passing check).

## Verifying a vector

The `crypto/` vectors are signed under the test key published in
`crypto/manifest.json` (`keyring[0].public_key_hex`), clearly marked as a test key and
not for production. A conformant verifier loads that key and checks each vector. With
the reference implementation:

```
flynn spine verify --file crypto/valid/crypto_run_valid_01.cbor --key <public_key_hex>
```

A valid vector reports verified (and, where applicable, governed and grounded); an
invalid vector is rejected with the manifest's `failure_code`.
