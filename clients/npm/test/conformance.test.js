// Conformance: the verifier agrees with the published vectors. These read the
// suite from the repository; when the package is installed outside the
// repository the vectors are absent and the checks are skipped.

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { verifyRun, VerifyError } from "../index.js";

// The published conformance test key (also in vectors/crypto/manifest.json). Test only.
const ROOT_KEY = Buffer.from(
  "79b5562e8fe654f94078b112e8a98ba7901f853ae695bed7e0e3910bad049664",
  "hex",
);

const cryptoDir = join(dirname(fileURLToPath(import.meta.url)), "../../../vectors/crypto");
const haveVectors = existsSync(cryptoDir);

test("valid records verify", { skip: !haveVectors }, () => {
  for (const name of [
    "valid/crypto_run_valid_01.cbor",
    "valid/crypto_governance_valid_01.cbor",
    "valid/crypto_ground_truth_valid_01.cbor",
  ]) {
    const record = readFileSync(join(cryptoDir, name));
    const { events } = verifyRun(record, ROOT_KEY);
    assert.ok(events.length >= 1, `${name} should verify`);
  }
});

test("integrity failures are rejected", { skip: !haveVectors }, () => {
  for (const name of [
    "invalid/crypto_run_root_mismatch_01.cbor",
    "invalid/crypto_run_size_mismatch_01.cbor",
    "invalid/crypto_run_bad_signature_01.cbor",
  ]) {
    const record = readFileSync(join(cryptoDir, name));
    assert.throws(() => verifyRun(record, ROOT_KEY), VerifyError, `${name} should be rejected`);
  }
});
