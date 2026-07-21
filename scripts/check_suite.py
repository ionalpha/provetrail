#!/usr/bin/env python3
"""Structural checks over the published conformance suite and the version surfaces.

This is the gate that makes the specification's claims literally true rather than
aspirational. CONFORMANCE.md asserts that "every vector named in this document exists
on disk and in a manifest.json"; nothing enforced that until this script. It checks:

  1. Every artifact a manifest names exists on disk.
  2. Every .cbor on disk is claimed by exactly one manifest entry (no orphans, no
     two entries silently sharing a file).
  3. Vector ids are unique within a manifest.
  4. Reject vectors carry a failure_code; accept vectors do not.
  5. Every failure_code used is registered in CONFORMANCE.md.
  6. One version string across SPEC.md, CONFORMANCE.md, CITATION.cff and both
     manifests, so a version bump cannot land on some surfaces and not others.

Run with no arguments from anywhere; exits non-zero with an explanation on failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUITES = ("structural", "crypto")

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def artifacts_of(vector: dict) -> list[str] | None:
    """The vector files an entry claims, under either manifest's spelling.

    Returns None when the entry names no file list at all. An explicitly empty
    `events` list is legitimate: `invalid.chain.empty.01` *is* the empty stream.
    """
    if "artifact" in vector:
        return [vector["artifact"]]
    if "events" in vector:
        return list(vector["events"])
    return None


def check_suite(name: str) -> str | None:
    """Check one vector suite; returns its declared suite_version."""
    root = REPO / "vectors" / name
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        fail(f"{name}: manifest.json is missing")
        return None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    vectors = manifest.get("vectors", [])
    if not vectors:
        fail(f"{name}: the manifest declares no vectors")

    seen_ids: set[str] = set()
    claimed: dict[str, str] = {}  # relative path -> claiming vector id

    for vector in vectors:
        vid = vector.get("id", "<unnamed>")
        if vid in seen_ids:
            fail(f"{name}: duplicate vector id {vid!r}")
        seen_ids.add(vid)

        expect = vector.get("expect")
        code = vector.get("failure_code")
        if expect == "reject" and not code:
            fail(f"{name}/{vid}: a reject vector must name the failure_code it pins")
        if expect == "accept" and code:
            fail(f"{name}/{vid}: an accept vector must not carry a failure_code")
        if expect not in ("accept", "reject"):
            fail(f"{name}/{vid}: expect must be 'accept' or 'reject', got {expect!r}")

        paths = artifacts_of(vector)
        if paths is None:
            fail(f"{name}/{vid}: the vector names neither 'artifact' nor 'events'")
            paths = []
        for rel in paths:
            if not (root / rel).exists():
                fail(f"{name}/{vid}: names {rel}, which does not exist on disk")
            elif rel in claimed:
                fail(f"{name}: {rel} is claimed by both {claimed[rel]} and {vid}")
            else:
                claimed[rel] = vid

    on_disk = {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*.cbor")
    }
    for orphan in sorted(on_disk - set(claimed)):
        fail(
            f"{name}: {orphan} is on disk but no manifest entry claims it. "
            "An unlisted vector is invisible to every verifier."
        )

    return manifest.get("suite_version")


def check_failure_codes_are_registered() -> None:
    """Every code a vector pins must appear in the CONFORMANCE.md registry."""
    conformance = (REPO / "CONFORMANCE.md").read_text(encoding="utf-8")
    registered = set(re.findall(r"`([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)`", conformance))

    for name in SUITES:
        manifest_path = REPO / "vectors" / name / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for vector in manifest.get("vectors", []):
            code = vector.get("failure_code")
            if code and code not in registered:
                fail(
                    f"{name}/{vector.get('id')}: failure code {code!r} is not in the "
                    "CONFORMANCE.md registry. A code a vector pins must be published."
                )


def check_versions(suite_versions: dict[str, str | None]) -> None:
    """One version string across every surface that carries one."""
    surfaces: dict[str, str | None] = {}

    for doc in ("SPEC.md", "CONFORMANCE.md"):
        text = (REPO / doc).read_text(encoding="utf-8")
        match = re.search(r"^\*\*Version:\*\*\s*(\S+)", text, re.MULTILINE)
        surfaces[doc] = match.group(1) if match else None
        if match is None:
            fail(f"{doc}: no '**Version:**' header found")

    citation = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)", citation, re.MULTILINE)
    surfaces["CITATION.cff"] = match.group(1) if match else None
    if match is None:
        fail("CITATION.cff: no 'version:' field found")

    for name, version in suite_versions.items():
        surfaces[f"vectors/{name}/manifest.json"] = version
        if version is None:
            fail(f"vectors/{name}/manifest.json: no suite_version")

    distinct = {v for v in surfaces.values() if v is not None}
    if len(distinct) > 1:
        listing = "\n".join(f"    {k}: {v}" for k, v in surfaces.items())
        fail(
            "the version differs across surfaces; a bump reached some and not others:\n"
            + listing
        )


def main() -> int:
    suite_versions = {name: check_suite(name) for name in SUITES}
    check_failure_codes_are_registered()
    check_versions(suite_versions)

    if failures:
        print(f"conformance suite check failed ({len(failures)} problem(s)):\n")
        for problem in failures:
            print(f"  - {problem}")
        return 1

    total = sum(
        len(json.loads((REPO / "vectors" / n / "manifest.json").read_text(encoding="utf-8"))["vectors"])
        for n in SUITES
    )
    print(f"conformance suite OK: {total} vectors across {len(SUITES)} suites, versions aligned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
