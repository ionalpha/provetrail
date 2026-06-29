//! `provetrail-verify <record-file> <hex-public-key>`: verify a sealed run record.

use std::process::exit;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: provetrail-verify <record-file> <hex-public-key>");
        exit(2);
    }
    let record = std::fs::read(&args[1]).unwrap_or_else(|e| {
        eprintln!("read {}: {e}", args[1]);
        exit(2);
    });
    let key_bytes = hex::decode(args[2].trim()).unwrap_or_else(|e| {
        eprintln!("public key is not valid hex: {e}");
        exit(2);
    });
    let key: [u8; 32] = key_bytes.try_into().unwrap_or_else(|v: Vec<u8>| {
        eprintln!("public key must be 32 bytes, got {}", v.len());
        exit(2);
    });

    match provetrail::verify_run(&record, &key) {
        Ok(v) => println!("VERIFIED ({} events)", v.events.len()),
        Err(e) => {
            println!("NOT VERIFIED: {e}");
            exit(1);
        }
    }
}
