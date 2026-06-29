# provetrail

A verifier for **Provetrail**, an open standard for verifiable execution provenance.

> **Status: draft (`0.1.x`).** This package verifies the integrity tier of a sealed run record: the COSE_Sign1 checkpoint signature and the RFC 9162 Merkle root over the carried events. The on-the-wire format is not frozen until v0.1.0, so do not yet rely on it as a production security control.

## What Provetrail is

A portable, third-party-verifiable record of what an agent did, in what order, and under what governance, anchored to an append-only, tamper-evident event log.

- Specification and conformance suite: https://github.com/ionalpha/provetrail
- Project home: https://provetrail.org

## Install

```
npm install provetrail
```

## Use

```js
import { readFileSync } from "node:fs";
import { verifyRun, VerifyError } from "provetrail";

const record = readFileSync("run.cbor");
const publicKey = Buffer.from("...", "hex"); // 32-byte Ed25519 public key

try {
  const { events } = verifyRun(record, publicKey);
  console.log(`verified, ${events.length} events`);
} catch (e) {
  if (e instanceof VerifyError) console.log(`not verified: ${e.message}`);
  else throw e;
}
```

Or from the command line:

```
npx provetrail run.cbor <hex-public-key>
```

`verifyRun` follows the carry-the-bytes rule: it rehashes the exact bytes the record carries and never re-serializes, so it agrees with any other conformant verifier (the Go reference verifier and the Rust crate) on the same record. It fails closed on a bad signature, a size mismatch, or events that do not rebuild the signed root. Signature verification uses the Node.js `crypto` Ed25519 primitive; the only dependency is a CBOR codec.

## Conformance

The verifier is checked against the published conformance vectors with `npm test` (run from a checkout of the repository). The cryptographic vectors live in [`vectors/crypto`](https://github.com/ionalpha/provetrail/tree/main/vectors/crypto). The reference verifier covering every tier (integrity, governance, ground truth) ships in the Go runtime at [`ionalpha/flynn`](https://github.com/ionalpha/flynn).

## License

Apache-2.0. The specification prose is CC-BY-4.0. Provetrail is a trademark of Ion Alpha.
