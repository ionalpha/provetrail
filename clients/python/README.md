# provetrail

A verifier for **Provetrail**, an open standard for verifiable execution provenance.

> **Status: `0.3.x`.** This package verifies the integrity tier of a sealed run record: the COSE_Sign1 checkpoint signature and the RFC 9162 Merkle root over the carried events. The on-the-wire format is frozen at **specification** v0.1.0 (the spec's version, not this package's); what verification proves is scoped by the specification's trust model.

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

`verify_run` follows the carry-the-bytes rule: it rehashes the exact bytes the record carries and never re-serializes. The conformance suite asserts identical verdicts *and* registered failure codes across this client, the npm and Rust clients, and the Go reference verifier, so agreement on the same record is tested, not assumed. It fails closed with a registered failure code (`VerifyError.code`) on every defect: container framing, protected-header claims (algorithm -19, the checkpoint content type, key id), signature, checkpoint-payload form, size, and root.

## Conformance

The verifier is checked against the published conformance vectors:

```
pip install provetrail[test]
pytest
```

The cryptographic vectors live in [`vectors/crypto`](https://github.com/ionalpha/provetrail/tree/main/vectors/crypto). This client verifies the integrity tiers (L1-L3) against conformance suite `0.1.0`; it does not enforce L4 (governance and ground truth), so an L4-claiming record needs an L4 verifier. The reference verifier covering every tier (L1-L4; in the documented shorthand, integrity = L1-L3 and governance + ground truth = L4) ships in the Go runtime at [`ionalpha/flynn`](https://github.com/ionalpha/flynn).

## License

Apache-2.0. The specification prose is CC-BY-4.0. Provetrail is a trademark of Ion Alpha.
