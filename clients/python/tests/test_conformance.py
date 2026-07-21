"""Conformance: the verifier agrees with the published vectors.

The cases are enumerated from ``vectors/crypto/manifest.json`` rather than listed
here, so a vector added to the suite immediately becomes a demand on this client.
What this client is measured on is declared in ``clients/conformance-scope.json``.

These read the suite from the repository; when the package is installed outside
the repository the vectors are absent and the checks are skipped.
"""

import json
from pathlib import Path

import pytest

from provetrail import VerifyError, verify_run

REPO = Path(__file__).resolve().parents[3]
CRYPTO_DIR = REPO / "vectors" / "crypto"
SCOPE_PATH = REPO / "clients" / "conformance-scope.json"

pytestmark = pytest.mark.skipif(
    not CRYPTO_DIR.exists(), reason="conformance vectors not present"
)

if CRYPTO_DIR.exists():
    MANIFEST = json.loads((CRYPTO_DIR / "manifest.json").read_text(encoding="utf-8"))
    SCOPE = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    # The keyring comes from the manifest, never pasted in here: a rotated
    # conformance key must not leave a stale copy behind that still passes. Keyed
    # by key id, so sign.unknown_key is a reachable verdict.
    KEYRING = {
        k["key_id"]: bytes.fromhex(k["public_key_hex"]) for k in MANIFEST["keyring"]
    }
    VECTORS = MANIFEST["vectors"]
    SUPPORTED = [v for v in VECTORS if v["kind"] in SCOPE["kinds_supported"]]
else:  # pragma: no cover - the whole module is skipped in this case
    MANIFEST, SCOPE, KEYRING, VECTORS, SUPPORTED = None, None, {}, [], []


def _is_out_of_scope(vector):
    """True when the vector's failure sits above the integrity tier."""
    code = vector.get("failure_code", "")
    return any(code.startswith(p) for p in SCOPE["out_of_scope_failure_prefixes"])


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_every_vector_kind_is_declared_in_the_client_scope(vector):
    declared = set(SCOPE["kinds_supported"]) | set(SCOPE["kinds_unsupported"])
    assert vector["kind"] in declared, (
        f"vector {vector['id']} has kind {vector['kind']!r}, declared neither supported "
        "nor unsupported in clients/conformance-scope.json. New coverage must be "
        "declared deliberately."
    )


def test_the_manifest_is_reachable():
    assert SUPPORTED, "no supported vectors found; the manifest path is wrong"


@pytest.mark.parametrize("vector", SUPPORTED, ids=lambda v: v["id"])
def test_the_published_suite_agrees_with_the_verifier(vector):
    record = (CRYPTO_DIR / vector["artifact"]).read_bytes()
    # A reject vector whose failure is above the integrity tier is intact at this
    # tier, so this client must accept it: rejecting would claim a tier it does
    # not implement.
    if vector["expect"] == "accept" or _is_out_of_scope(vector):
        assert len(verify_run(record, KEYRING).events) >= 1
    else:
        with pytest.raises(VerifyError) as exc_info:
            verify_run(record, KEYRING)
        # Not just any rejection: the registered code the vector pins. A wrong
        # code means the client rejected for the wrong reason.
        assert exc_info.value.code == vector["failure_code"], (
            f"{vector['id']}: rejected with {exc_info.value.code!r}, "
            f"the vector pins {vector['failure_code']!r}"
        )
