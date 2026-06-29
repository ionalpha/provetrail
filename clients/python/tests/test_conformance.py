"""Conformance: the verifier agrees with the published vectors.

These read the suite from the repository; when the package is installed outside
the repository the vectors are absent and the checks are skipped.
"""

from pathlib import Path

import pytest

from provetrail import VerifyError, verify_run

# The published conformance test key (also in vectors/crypto/manifest.json). Test only.
ROOT_KEY = bytes.fromhex(
    "79b5562e8fe654f94078b112e8a98ba7901f853ae695bed7e0e3910bad049664"
)

CRYPTO_DIR = Path(__file__).resolve().parents[3] / "vectors" / "crypto"
pytestmark = pytest.mark.skipif(
    not CRYPTO_DIR.exists(), reason="conformance vectors not present"
)


@pytest.mark.parametrize(
    "name",
    [
        "valid/crypto_run_valid_01.cbor",
        "valid/crypto_governance_valid_01.cbor",
        "valid/crypto_ground_truth_valid_01.cbor",
    ],
)
def test_valid_records_verify(name):
    record = (CRYPTO_DIR / name).read_bytes()
    result = verify_run(record, ROOT_KEY)
    assert len(result.events) >= 1


@pytest.mark.parametrize(
    "name",
    [
        "invalid/crypto_run_root_mismatch_01.cbor",
        "invalid/crypto_run_size_mismatch_01.cbor",
        "invalid/crypto_run_bad_signature_01.cbor",
    ],
)
def test_integrity_failures_are_rejected(name):
    record = (CRYPTO_DIR / name).read_bytes()
    with pytest.raises(VerifyError):
        verify_run(record, ROOT_KEY)
