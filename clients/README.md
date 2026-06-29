# Clients

Language clients and verifiers for the Provetrail standard. Each is published under the canonical bare name `provetrail` in its ecosystem.

- `rust/` -> the `provetrail` crate (Rust): a working verifier (signature + Merkle integrity), checked against the published vectors with `cargo test`
- `npm/` -> the `provetrail` package on npm (JavaScript / TypeScript): a working verifier on the Node.js crypto primitives, checked against the published vectors with `npm test`
- `python/` -> the `provetrail` package on PyPI (Python): a working verifier, checked against the published vectors with `pytest`

All three verify the integrity tier (the COSE_Sign1 checkpoint signature and the RFC 9162 Merkle root over the carried events) and agree, byte for byte, with each other and with the Go reference verifier on the same records, because each rehashes the bytes the record carries rather than re-serializing. A reference verifier with every tier (integrity, governance, ground truth) ships in the Go runtime at [`ionalpha/flynn`](https://github.com/ionalpha/flynn). The specification and conformance suite live at the repository root.
