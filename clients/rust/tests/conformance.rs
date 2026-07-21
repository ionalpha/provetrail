//! Conformance: the verifier agrees with the published vectors.
//!
//! The cases are enumerated from `vectors/crypto/manifest.json` rather than listed here,
//! so a vector added to the suite immediately becomes a demand on this client. What this
//! client is measured on is declared in `clients/conformance-scope.json`.
//!
//! These read the suite from the repository; when the crate is used outside the
//! repository the vectors are absent and the checks are skipped.

use std::path::{Path, PathBuf};

use serde_json::Value;

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn crypto_dir() -> Option<PathBuf> {
    let p = repo().join("vectors/crypto");
    p.exists().then_some(p)
}

fn read_json(path: PathBuf) -> Value {
    serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap()
}

fn strings(v: &Value, key: &str) -> Vec<String> {
    v[key]
        .as_array()
        .unwrap_or_else(|| panic!("conformance-scope.json is missing the array {key}"))
        .iter()
        .map(|s| s.as_str().unwrap().to_string())
        .collect()
}

/// A vector's failure sits above the integrity tier, so this client must accept it.
fn is_out_of_scope(vector: &Value, prefixes: &[String]) -> bool {
    let code = vector["failure_code"].as_str().unwrap_or("");
    prefixes.iter().any(|p| code.starts_with(p))
}

#[test]
fn every_vector_kind_is_declared_in_the_client_scope() {
    let Some(dir) = crypto_dir() else { return };
    let manifest = read_json(dir.join("manifest.json"));
    let scope = read_json(repo().join("clients/conformance-scope.json"));

    let mut declared = strings(&scope, "kinds_supported");
    declared.extend(strings(&scope, "kinds_unsupported"));

    for vector in manifest["vectors"].as_array().unwrap() {
        let (id, kind) = (
            vector["id"].as_str().unwrap(),
            vector["kind"].as_str().unwrap(),
        );
        assert!(
            declared.iter().any(|d| d == kind),
            "vector {id} has kind {kind:?}, declared neither supported nor unsupported in \
             clients/conformance-scope.json. New coverage must be declared deliberately."
        );
    }
}

#[test]
fn the_published_suite_agrees_with_the_verifier() {
    let Some(dir) = crypto_dir() else { return };
    let manifest = read_json(dir.join("manifest.json"));
    let scope = read_json(repo().join("clients/conformance-scope.json"));

    let supported = strings(&scope, "kinds_supported");
    let out_of_scope = strings(&scope, "out_of_scope_failure_prefixes");

    // The root key comes from the manifest keyring, never pasted in here: a rotated
    // conformance key must not leave a stale copy behind that still passes.
    let key_hex = manifest["keyring"][0]["public_key_hex"].as_str().unwrap();
    let root_key: [u8; 32] = hex::decode(key_hex).unwrap().try_into().unwrap();

    let mut checked = 0;
    for vector in manifest["vectors"].as_array().unwrap() {
        let kind = vector["kind"].as_str().unwrap();
        if !supported.iter().any(|s| s == kind) {
            continue;
        }
        checked += 1;

        let id = vector["id"].as_str().unwrap();
        let record = std::fs::read(dir.join(vector["artifact"].as_str().unwrap())).unwrap();
        let result = provetrail::verify_run(&record, &root_key);

        // A reject vector whose failure is above the integrity tier is intact at this
        // tier, so this client must accept it: rejecting would claim a tier it does not
        // implement.
        if vector["expect"] == "accept" || is_out_of_scope(vector, &out_of_scope) {
            assert!(result.is_ok(), "{id} should verify, got {:?}", result.err());
        } else {
            assert!(
                result.is_err(),
                "{id} should be rejected ({})",
                vector["failure_code"].as_str().unwrap_or("?")
            );
        }
    }
    assert!(
        checked > 0,
        "no supported vectors found; the manifest path is wrong"
    );
}
