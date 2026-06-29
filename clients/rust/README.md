# provetrail (Rust)

A verifier for the [Provetrail](https://github.com/ionalpha/provetrail) standard,
verifiable execution provenance. It checks the integrity of a sealed run record: the
COSE_Sign1 checkpoint signature is valid under a given Ed25519 key, and the events
rebuild the signed RFC 9162 Merkle root.

It follows the carry-the-bytes rule, it rehashes the exact bytes the record carries and
never re-serializes, so it agrees with any other conformant verifier on the same record.
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

This release verifies the integrity tier: the signed checkpoint and the Merkle root over
the carried events. The canonical-container check and the governance and ground-truth
tiers (which the reference implementation in Go performs) are not yet implemented here.
