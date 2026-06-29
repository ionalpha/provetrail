"""Provetrail: a verifier for verifiable execution provenance records.

This package verifies the integrity of a sealed run record: the COSE_Sign1
checkpoint signature is valid under a given Ed25519 key, and the carried events
rebuild the signed RFC 9162 Merkle root. It follows the carry-the-bytes rule: it
rehashes the exact bytes the record carries and never re-serializes, so it agrees
with any other conformant verifier on the same record.

See https://provetrail.org and https://github.com/ionalpha/provetrail for the
specification and the conformance suite.
"""

from .verify import Verified, VerifyError, verify_run

__all__ = ["verify_run", "Verified", "VerifyError", "__version__"]

__version__ = "0.1.0"
