// Conformance: the verifier agrees with the published vectors.
//
// The cases are enumerated from vectors/crypto/manifest.json rather than listed
// here, so a vector added to the suite immediately becomes a demand on this
// client. What this client is measured on is declared in clients/conformance-scope.json.
//
// These read the suite from the repository; when the package is installed
// outside the repository the vectors are absent and the checks are skipped.

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { verifyRun, VerifyError } from "../index.js";

const here = dirname(fileURLToPath(import.meta.url));
const cryptoDir = join(here, "../../../vectors/crypto");
const haveVectors = existsSync(cryptoDir);

const readJson = (p) => JSON.parse(readFileSync(p, "utf8"));
const manifest = haveVectors ? readJson(join(cryptoDir, "manifest.json")) : null;
const scope = haveVectors ? readJson(join(here, "../../conformance-scope.json")) : null;

// The keyring comes from the manifest, never pasted in here: a rotated
// conformance key must not leave a stale copy behind that still passes. Keyed
// by key id, so sign.unknown_key is a reachable verdict.
const keyring = haveVectors
  ? new Map(manifest.keyring.map((k) => [k.key_id, Buffer.from(k.public_key_hex, "hex")]))
  : null;

const isOutOfScope = (v) =>
  scope.out_of_scope_failure_prefixes.some((p) => (v.failure_code ?? "").startsWith(p));

test("every vector kind is declared in the client scope", { skip: !haveVectors }, () => {
  const declared = new Set([...scope.kinds_supported, ...scope.kinds_unsupported]);
  for (const v of manifest.vectors) {
    assert.ok(
      declared.has(v.kind),
      `vector ${v.id} has kind "${v.kind}", declared neither supported nor unsupported ` +
        `in clients/conformance-scope.json. New coverage must be declared deliberately.`,
    );
  }
});

test("the published suite agrees with the verifier", { skip: !haveVectors }, () => {
  const supported = manifest.vectors.filter((v) => scope.kinds_supported.includes(v.kind));
  assert.ok(supported.length > 0, "no supported vectors found; the manifest path is wrong");

  for (const v of supported) {
    const record = readFileSync(join(cryptoDir, v.artifact));
    // A reject vector whose failure is above the integrity tier is intact at this
    // tier, so this client must accept it: rejecting would claim a tier it does
    // not implement.
    const shouldAccept = v.expect === "accept" || isOutOfScope(v);

    if (shouldAccept) {
      const why =
        v.expect === "accept" ? "should verify" : `is out of tier scope (${v.failure_code}) and must verify`;
      assert.doesNotThrow(() => verifyRun(record, keyring), `${v.id} ${why}`);
    } else {
      // Not just any rejection: the registered code the vector pins. A wrong
      // code means the client rejected for the wrong reason.
      assert.throws(
        () => verifyRun(record, keyring),
        (err) => {
          assert.ok(err instanceof VerifyError, `${v.id}: rejected with a non-VerifyError`);
          assert.equal(
            err.code,
            v.failure_code,
            `${v.id}: rejected with "${err.code}", the vector pins "${v.failure_code}"`,
          );
          return true;
        },
        `${v.id} should be rejected (${v.failure_code})`,
      );
    }
  }
});
