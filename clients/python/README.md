# provetrail

A verifier for **Provetrail**, an open standard for verifiable execution provenance.

> **Status: draft (`0.1.x`).** This package verifies the integrity tier of a sealed run record: the COSE_Sign1 checkpoint signature and the RFC 9162 Merkle root over the carried events. The on-the-wire format is not frozen until v0.1.0, so do not yet rely on it as a production security control.

## What Provetrail is

A portable, third-party-verifiable record of what an agent did, in what order, and under what governance, anchored to an append-only, tamper-evident event log.

- Specification and conformance suite: https://github.com/ionalpha/provetrail
- Project home: https://provetrail.org

## Install

```
pip install provetrail
```

## Use

```python
from provetrail import verify_run, VerifyError

record = open("run.cbor", "rb").read()
public_key = bytes.fromhex("...")  # 32-byte Ed25519 public key

try:
    result = verify_run(record, public_key)
    print(f"verified, {len(result.events)} events")
except VerifyError as e:
    print(f"not verified: {e}")
```

Or from the command line:

```
python -m provetrail run.cbor <hex-public-key>
# or, once installed:
provetrail run.cbor <hex-public-key>
```

`verify_run` follows the carry-the-bytes rule: it rehashes the exact bytes the record carries and never re-serializes, so it agrees with any other conformant verifier (the Go reference verifier and the Rust crate) on the same record. It fails closed on a bad signature, a size mismatch, or events that do not rebuild the signed root.

## Conformance

The verifier is checked against the published conformance vectors:

```
pip install provetrail[test]
pytest
```

The cryptographic vectors live in [`vectors/crypto`](https://github.com/ionalpha/provetrail/tree/main/vectors/crypto). The reference verifier covering every tier (integrity, governance, ground truth) ships in the Go runtime at [`ionalpha/flynn`](https://github.com/ionalpha/flynn).

## License

Apache-2.0. The specification prose is CC-BY-4.0. Provetrail is a trademark of Ion Alpha.
