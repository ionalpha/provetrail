# Clients

Language clients and verifiers for the Provetrail standard. Each is published under the canonical bare name `provetrail` in its ecosystem.

- `rust/` -> the `provetrail` crate (Rust): a working verifier (signature + Merkle integrity), checked against the published vectors with `cargo test`
- `npm/` -> the `provetrail` package on npm (JavaScript / TypeScript)
- `python/` -> the `provetrail` package on PyPI (Python)

The Rust crate verifies the integrity tier today; the npm and Python entries are placeholders (version `0.0.x`) that reserve the canonical names and point to the specification. A reference verifier with every tier (integrity, governance, ground truth) ships in the Go runtime at [`ionalpha/flynn`](https://github.com/ionalpha/flynn). The specification and conformance suite live at the repository root.
