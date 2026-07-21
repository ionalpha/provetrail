#!/usr/bin/env python3
"""Validate every valid vector against the published CDDL schemas.

SPEC.md Section 8 pins the wire format normatively and cddl/ carries the same
rules as machine-readable CDDL. Nothing kept those two and the vectors in
agreement until this script: it validates each MUST-accept vector against the
CDDL type its kind selects, so a schema that drifts from the generator fails
CI rather than quietly shipping.

Only valid vectors are checked. Invalid vectors each violate one rule on
purpose, and many of those rules (canonical form, duplicate keys) live below
CDDL's level of abstraction anyway; SPEC Section 8.1 is normative for those.

Requires the cddl CLI (cargo install cddl). Set CDDL_BIN to point at a
specific executable, otherwise 'cddl' is taken from PATH.

Usage:
    python scripts/check_cddl.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CDDL = REPO / "cddl"

# The cddl CLI validates against the FIRST rule of the document, so each root
# type gets a document assembled from the schema files it needs, root first. A
# root that is not already a file's first rule gets a one-line alias prepended.
ROOTS = {
    "event": {"files": ["envelope.cddl"], "alias": None},
    "signed-checkpoint": {"files": ["checkpoint.cddl"], "alias": None},
    "sealed-run": {
        "files": ["record.cddl", "checkpoint.cddl", "envelope.cddl"],
        "alias": None,
    },
    "event-proof": {
        "files": ["proofs.cddl", "record.cddl", "checkpoint.cddl", "envelope.cddl"],
        "alias": None,
    },
    "consistency-proof": {
        "files": ["proofs.cddl", "record.cddl", "checkpoint.cddl", "envelope.cddl"],
        "alias": "validation-root = consistency-proof",
    },
}

# Vector kind -> root type. Governance and ground-truth vectors are sealed runs
# whose defect (if any) is semantic, so structurally they are sealed-run.
KIND_TO_ROOT = {
    "checkpoint": "signed-checkpoint",
    "run": "sealed-run",
    "governance": "sealed-run",
    "ground_truth": "sealed-run",
    "event_proof": "event-proof",
    "consistency": "consistency-proof",
}


def build_docs(tmp: Path) -> dict[str, Path]:
    docs = {}
    for root, spec in ROOTS.items():
        body = "\n".join((CDDL / f).read_text(encoding="utf-8") for f in spec["files"])
        if spec["alias"]:
            body = spec["alias"] + "\n\n" + body
        p = tmp / (root + ".cddl")
        p.write_text(body, encoding="utf-8")
        docs[root] = p
    return docs


def validate(doc: Path, artifact: Path) -> str | None:
    """Run one validation; returns an error string or None on success."""
    proc = subprocess.run(
        [os.environ.get("CDDL_BIN", "cddl"), "validate", "-d", str(doc), "-c", str(artifact)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        return detail[-1] if detail else f"exit {proc.returncode}"
    return None


def main() -> int:
    failures: list[str] = []
    checked = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        docs = build_docs(Path(tmpdir))

        crypto = json.loads((REPO / "vectors/crypto/manifest.json").read_text(encoding="utf-8"))
        for vector in crypto["vectors"]:
            if vector["expect"] != "accept":
                continue
            doc = docs[KIND_TO_ROOT[vector["kind"]]]
            err = validate(doc, REPO / "vectors/crypto" / vector["artifact"])
            checked += 1
            if err:
                failures.append(f"{vector['id']}: {err}")

        structural = json.loads(
            (REPO / "vectors/structural/manifest.json").read_text(encoding="utf-8")
        )
        for vector in structural["vectors"]:
            if vector["expect"] != "accept":
                continue
            for rel in vector["events"]:
                err = validate(docs["event"], REPO / "vectors/structural" / rel)
                checked += 1
                if err:
                    failures.append(f"{vector['id']} {rel}: {err}")

    if failures:
        print(f"CDDL validation failed ({len(failures)} problem(s)):\n", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"CDDL OK: {checked} valid artifacts match the schemas in cddl/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
