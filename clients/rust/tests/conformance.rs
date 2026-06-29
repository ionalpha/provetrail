//! Conformance: the verifier agrees with the published vectors. These read the suite
//! from the repository; when the crate is used outside the repository the vectors are
//! absent and the checks are skipped.

use std::path::{Path, PathBuf};

/// The published conformance test key (also in vectors/crypto/manifest.json). Test only.
fn root_key() -> [u8; 32] {
    let bytes =
        hex::decode("79b5562e8fe654f94078b112e8a98ba7901f853ae695bed7e0e3910bad049664").unwrap();
    bytes.try_into().unwrap()
}

fn crypto_dir() -> Option<PathBuf> {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../vectors/crypto");
    p.exists().then_some(p)
}

#[test]
fn valid_records_verify() {
    let Some(dir) = crypto_dir() else { return };
    for name in [
        "valid/crypto_run_valid_01.cbor",
        "valid/crypto_governance_valid_01.cbor",
        "valid/crypto_ground_truth_valid_01.cbor",
    ] {
        let rec = std::fs::read(dir.join(name)).unwrap();
        assert!(
            provetrail::verify_run(&rec, &root_key()).is_ok(),
            "{name} should verify"
        );
    }
}

#[test]
fn integrity_failures_are_rejected() {
    let Some(dir) = crypto_dir() else { return };
    for name in [
        "invalid/crypto_run_root_mismatch_01.cbor",
        "invalid/crypto_run_size_mismatch_01.cbor",
        "invalid/crypto_run_bad_signature_01.cbor",
    ] {
        let rec = std::fs::read(dir.join(name)).unwrap();
        assert!(
            provetrail::verify_run(&rec, &root_key()).is_err(),
            "{name} should be rejected"
        );
    }
}
