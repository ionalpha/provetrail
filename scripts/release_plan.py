#!/usr/bin/env python3
"""Decide whether one client package needs publishing.

A package needs publishing when the version in its manifest is not one the registry
already serves. That makes a release a consequence of merging a version bump, with no
tag to remember and no second place to keep in sync.

Fails safe in both directions: a registry that cannot be reached is treated as
"already published", so an outage causes a missed release (recoverable) rather than an
unintended one (not), and the registry itself refuses a duplicate version regardless.

    python scripts/release_plan.py npm
    python scripts/release_plan.py pypi --github-output "$GITHUB_OUTPUT"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
USER_AGENT = "provetrail-release-ci (github.com/ionalpha/provetrail)"


def declared_npm() -> str:
    return json.loads((REPO / "clients/npm/package.json").read_text(encoding="utf-8"))["version"]


def declared_toml(path: str) -> str:
    for line in (REPO / path).read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split('"')[1]
    raise SystemExit(f"error: no version line in {path}")


def fetch(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except Exception:  # noqa: BLE001 - unreachable registry is handled by the caller
        return 0, b""


def published_npm(version: str) -> bool | None:
    status, body = fetch("https://registry.npmjs.org/provetrail")
    if status == 404:
        return False  # the package does not exist yet; this would be the first release
    if status != 200:
        return None
    return version in json.loads(body).get("versions", {})


def published_pypi(version: str) -> bool | None:
    status, _ = fetch(f"https://pypi.org/pypi/provetrail/{version}/json")
    if status == 404:
        return False
    if status != 200:
        return None
    return True


def published_crate(version: str) -> bool | None:
    status, _ = fetch(f"https://crates.io/api/v1/crates/provetrail/{version}")
    if status == 404:
        return False
    if status != 200:
        return None
    return True


PACKAGES = {
    "npm": ("clients/npm/package.json", declared_npm, published_npm),
    "pypi": ("clients/python/pyproject.toml", lambda: declared_toml("clients/python/pyproject.toml"), published_pypi),
    "crate": ("clients/rust/Cargo.toml", lambda: declared_toml("clients/rust/Cargo.toml"), published_crate),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", choices=sorted(PACKAGES))
    parser.add_argument(
        "--github-output",
        default=os.environ.get("GITHUB_OUTPUT"),
        help="path to write needed=/version= to (defaults to $GITHUB_OUTPUT)",
    )
    parser.add_argument(
        "--github-summary",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="path to append a human-readable summary to",
    )
    args = parser.parse_args()

    manifest, declared, published = PACKAGES[args.package]
    version = declared()
    already = published(version)

    if already is None:
        needed = False
        verdict = f"registry unreachable, treating {version} as already published"
    elif already:
        needed = False
        verdict = f"{version} is already published"
    else:
        needed = True
        verdict = f"{version} is not published; publishing"

    print(f"{args.package}: {manifest} declares {version}. {verdict}.")

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"needed={'true' if needed else 'false'}\nversion={version}\n")
    if args.github_summary:
        with open(args.github_summary, "a", encoding="utf-8") as handle:
            handle.write(f"**{args.package}** `{version}` - {verdict}\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
