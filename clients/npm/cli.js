#!/usr/bin/env node
// provetrail <record-file> <hex-public-key>: verify a sealed run record.

import { readFileSync } from "node:fs";
import { verifyRun, VerifyError } from "./index.js";

function main(argv) {
  if (argv.length !== 2) {
    process.stderr.write("usage: provetrail <record-file> <hex-public-key>\n");
    return 2;
  }
  const [recordPath, keyHex] = argv;
  const record = readFileSync(recordPath);
  const key = Buffer.from(keyHex.trim(), "hex");
  if (key.length !== 32) {
    process.stderr.write("public key must be 32 bytes of hex\n");
    return 2;
  }
  try {
    const { events } = verifyRun(record, key);
    process.stdout.write(`VERIFIED (${events.length} events)\n`);
    return 0;
  } catch (e) {
    if (e instanceof VerifyError) {
      process.stdout.write(`NOT VERIFIED: ${e.message}\n`);
      return 1;
    }
    throw e;
  }
}

process.exit(main(process.argv.slice(2)));
