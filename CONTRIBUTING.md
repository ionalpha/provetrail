# Contributing to Provetrail

Provetrail is an open, vendor-neutral standard for verifiable execution provenance. It is an early draft, and review is welcome.

## Status

This is a pre-1.0 draft. The on-the-wire format is not frozen until `v0.1.0` is tagged, so changes to `SPEC.md`, `CONFORMANCE.md`, and the predicate definitions are expected. The cryptographic layer (the RFC 9162 Merkle log, COSE signing, and signed roots) is implemented in the reference implementation and exercised by the published vectors, so a record can be cryptographically verified against a signing key today; until the format freezes, treat any record as a draft artifact and do not rely on it as a production security control.

## Design philosophy

- Assemble proven primitives; do not invent cryptography. Proposals should build on established standards (deterministic CBOR, COSE, RFC 9162, Ed25519, in-toto / SCITT statement layering) rather than introduce new cryptographic constructions.
- Keep the standard implementation-neutral. It is not bound to any single implementation, and any conformant producer or verifier in any language is a first-class citizen.
- Verification MUST NOT require trusting the producer. A change that weakens third-party verifiability is out of scope.

The full change process, the registry-change discipline, and who maintains the standard are in [`GOVERNANCE.md`](./GOVERNANCE.md); [`VERSIONING.md`](./VERSIONING.md) defines what counts as a breaking change. In short:

1. Open an issue describing the problem or gap, using the relevant template.
2. For a concrete change, open a pull request against the affected document and reference the issue.
3. For conformance changes, describe the case, the expected verdict, and the failure code, so it can be added to the suite defined in `CONFORMANCE.md`. A normative change that adds or changes a check ships with the vector that exercises it: a rule with no vector does not land.

## What CI checks

Every pull request runs the conformance gate (`.github/workflows/conformance.yml`), and
the release pipeline runs the same workflow, so nothing is published that a pull request
would not have passed. The gate covers:

- `python scripts/check_suite.py` - every vector a manifest names exists on disk, every
  vector on disk is named by exactly one manifest entry, every failure code a vector
  pins is registered in `CONFORMANCE.md`, and one version string spans `SPEC.md`,
  `CONFORMANCE.md`, `CITATION.cff` and both manifests.
- The three client verifiers in `clients/`, each run against the published vectors.
  Their cases are **enumerated from `vectors/crypto/manifest.json`**, not hand-listed, so
  adding a vector to the suite immediately becomes a demand on every client. What the
  clients are measured on is declared in `clients/conformance-scope.json`; a vector of a
  kind that file does not mention fails the build until the scope is updated
  deliberately.

Run the same checks locally with `python scripts/check_suite.py`, `npm test` in
`clients/npm`, `pytest` in `clients/python`, and `cargo test` in `clients/rust`.

Two further checks run on a schedule rather than on pull requests
(`.github/workflows/external.yml`), because they depend on another repository or on the
network and neither should be able to block a contribution:

- `scripts/check_vector_drift.py` byte-compares the published vectors against the
  reference implementation's copy. The suite is generated there and published here
  (`CONFORMANCE.md` Section 7), so two copies exist and drift between them would mean
  verifiers are measured against a suite the generator no longer produces.
- `scripts/check_external_surfaces.py` resolves the `w3id.org` permanent identifier for
  the predicate type and confirms it still lands where it should, checks provetrail.org
  is serving, and reports each registry's published version next to this repository's.

## Conventions

- Professional, neutral tone. Wrap code identifiers in backticks. Do not use em-dashes.
- Conventional-commit style for commit messages; describe the change on its own technical terms.

## Licensing of contributions

By contributing, you agree that your contributions to the specification prose are licensed under `CC-BY-4.0`, and your contributions to code, schemas, and vectors are licensed under `Apache-2.0`, consistent with this repository.
