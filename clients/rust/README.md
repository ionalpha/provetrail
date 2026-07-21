# provetrail (Rust)

A verifier for the [Provetrail](https://github.com/ionalpha/provetrail) standard,
verifiable execution provenance. It checks the integrity of a sealed run record: the
COSE_Sign1 checkpoint signature is valid under a given Ed25519 key, and the events
rebuild the signed RFC 9162 Merkle root.

It follows the carry-the-bytes rule, it rehashes the exact bytes the record carries and
never re-serializes. The conformance suite asserts identical verdicts *and* registered
failure codes (`VerifyError::code()`) across this crate, the Python and npm clients, and
the Go reference verifier, so agreement on the same record is tested, not assumed.
`cargo test` checks it against the published conformance vectors.

## Use

As a library:

```rust
let record: Vec<u8> = std::fs::read("record.cbor")?;
let key: [u8; 32] = /* the signer's Ed25519 public key */;
match provetrail::verify_run(&record, &key) {
    Ok(v) => println!("verified, {} events", v.events.len()),
    Err(e) => println!("not verified: {e}"),
}
```

As a command:

```
provetrail <record-file> <hex-public-key>
```

The cryptographic vectors are signed by a fixed test key published in
`vectors/crypto/manifest.json` (`keyring[0].public_key_hex`).

## Scope

This release verifies the integrity tiers (L1-L3) against conformance suite
`0.1.0-draft`: strict canonical container decoding, the pinned protected-header claims
(algorithm -19, the checkpoint content type, key id via `verify_run_keyring`), the
signature, the closed checkpoint payload, and the Merkle root over the carried events.
It does not enforce L4 (governance and ground truth), so an L4-claiming record needs an
L4 verifier; the reference verifier covering every tier ships in the Go runtime. The
on-the-wire format is not frozen until **specification** v0.1.0 (the spec's version,
not this crate's).
