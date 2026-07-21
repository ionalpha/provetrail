#!/usr/bin/env python3
"""Check the published surfaces that live outside this repository.

`check_suite.py` keeps the five in-repo version surfaces aligned. Three more surfaces
carry Provetrail's identity and are not in this repository at all, so nothing here would
notice them breaking:

  1. The `w3id.org` permanent identifier for the predicate type. This is the stable
     contract other implementations embed in signed statements. If the redirect breaks
     or points somewhere unexpected, every consumer resolving the type identifier gets
     the wrong answer, and it fails silently from this repository's point of view.
  2. provetrail.org, which serves the specification to humans and bundles a published
     client for its in-browser demo.
  3. The three package registries, whose latest published version should not be a
     mystery when cutting a release.

Network-dependent by nature, so this is a scheduled check rather than part of the
conformance gate: an npm outage must never be able to block a pull request.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The permanent identifier from predicates/run-provenance.md, and where it is expected
# to land. Change the target here deliberately when the canonical reference moves; that
# is the point of the indirection.
W3ID_URL = "https://w3id.org/provetrail/predicates/run-provenance/v0.1"
W3ID_EXPECTED_TARGET = (
    "https://github.com/ionalpha/provetrail/blob/main/predicates/run-provenance.md"
)

SITE_URL = "https://provetrail.org"

USER_AGENT = "provetrail-surface-check (github.com/ionalpha/provetrail)"

problems: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    problems.append(message)


def get(url: str, *, follow: bool = True) -> tuple[int, str, bytes]:
    """Fetch a URL. Returns (status, final_url, body). Does not raise on 4xx/5xx."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise _Redirect(code, newurl)

    opener = urllib.request.build_opener(
        *([] if follow else [NoRedirect])
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(request, timeout=30) as response:
            return response.status, response.geturl(), response.read()
    except _Redirect as redirect:
        return redirect.code, redirect.location, b""
    except urllib.error.HTTPError as error:
        return error.code, url, error.read()


class _Redirect(Exception):
    def __init__(self, code: int, location: str) -> None:
        super().__init__(f"{code} -> {location}")
        self.code, self.location = code, location


def check_w3id() -> None:
    status, location, _ = get(W3ID_URL, follow=False)
    if status not in (301, 302, 303, 307, 308):
        fail(f"{W3ID_URL} did not redirect (HTTP {status}). The permanent identifier is broken.")
        return
    if location != W3ID_EXPECTED_TARGET:
        fail(
            f"{W3ID_URL} redirects to {location}, expected {W3ID_EXPECTED_TARGET}. "
            "Either the w3id entry changed or W3ID_EXPECTED_TARGET here is stale."
        )
        return
    status, final, _ = get(W3ID_URL)
    if status != 200:
        fail(f"{W3ID_URL} resolves to {final}, which returned HTTP {status}.")
        return
    notes.append(f"w3id identifier resolves to {final}")


def check_site() -> None:
    status, final, _ = get(SITE_URL)
    if status != 200:
        fail(f"{SITE_URL} returned HTTP {status}")
        return
    notes.append(f"{final} is serving (HTTP 200)")


def manifest_versions() -> dict[str, str]:
    npm = json.loads((REPO / "clients/npm/package.json").read_text(encoding="utf-8"))["version"]

    def toml_version(path: str) -> str:
        for line in (REPO / path).read_text(encoding="utf-8").splitlines():
            if line.startswith("version = "):
                return line.split('"')[1]
        return "?"

    return {
        "npm": npm,
        "PyPI": toml_version("clients/python/pyproject.toml"),
        "crates.io": toml_version("clients/rust/Cargo.toml"),
    }


def check_registries() -> None:
    """Report what each registry serves next to what the repository declares.

    Informational: a repository version ahead of the registry is the normal state
    between a bump and its release, not an error.
    """
    declared = manifest_versions()
    latest: dict[str, str] = {}

    status, _, body = get("https://registry.npmjs.org/provetrail")
    latest["npm"] = (
        json.loads(body)["dist-tags"]["latest"] if status == 200 else f"unavailable ({status})"
    )

    status, _, body = get("https://pypi.org/pypi/provetrail/json")
    latest["PyPI"] = (
        json.loads(body)["info"]["version"] if status == 200 else f"unavailable ({status})"
    )

    status, _, body = get("https://crates.io/api/v1/crates/provetrail")
    latest["crates.io"] = (
        json.loads(body)["crate"]["max_version"] if status == 200 else f"unavailable ({status})"
    )

    for registry, declared_version in declared.items():
        published = latest[registry]
        state = "in sync" if published == declared_version else "repository is ahead"
        notes.append(f"{registry}: repository {declared_version}, published {published} ({state})")


def main() -> int:
    check_w3id()
    check_site()
    check_registries()

    for note in notes:
        print(f"  {note}")

    if problems:
        print(f"\nexternal surface check failed ({len(problems)} problem(s)):\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nexternal surfaces OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
