# Contributing to Provetrail

Provetrail is an open, vendor-neutral standard for verifiable execution provenance. It is an early draft, and review is welcome.

## Status

This is a pre-1.0 draft. The on-the-wire format is not frozen until `v0.1.0` is tagged, so changes to `SPEC.md`, `CONFORMANCE.md`, and the predicate definitions are expected. Until the cryptographic layer is implemented, the standard provides structural guarantees only; please do not describe a record as "cryptographically verifiable" before then.

## Design philosophy

- Assemble proven primitives; do not invent cryptography. Proposals should build on established standards (deterministic CBOR, COSE, RFC 9162, Ed25519, in-toto / SCITT statement layering) rather than introduce new cryptographic constructions.
- Keep the standard implementation-neutral. It is not bound to any single implementation, and any conformant producer or verifier in any language is a first-class citizen.
- Verification MUST NOT require trusting the producer. A change that weakens third-party verifiability is out of scope.

## How to propose a change

1. Open an issue describing the problem or gap, using the relevant template.
2. For a concrete change, open a pull request against the affected document and reference the issue.
3. For conformance changes, describe the case, the expected verdict, and the failure code, so it can be added to the suite defined in `CONFORMANCE.md`.

## Conventions

- Professional, neutral tone. Wrap code identifiers in backticks. Do not use em-dashes.
- Conventional-commit style for commit messages; describe the change on its own technical terms.

## Licensing of contributions

By contributing, you agree that your contributions to the specification prose are licensed under `CC-BY-4.0`, and your contributions to code, schemas, and vectors are licensed under `Apache-2.0`, consistent with this repository.
