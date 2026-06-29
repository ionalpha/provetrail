"""CLI: ``python -m provetrail <record-file> <hex-public-key>``."""

import sys

from .verify import VerifyError, verify_run


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python -m provetrail <record-file> <hex-public-key>", file=sys.stderr)
        return 2
    record_path, key_hex = sys.argv[1], sys.argv[2]
    with open(record_path, "rb") as f:
        record = f.read()
    try:
        key = bytes.fromhex(key_hex.strip())
    except ValueError as exc:
        print(f"public key is not valid hex: {exc}", file=sys.stderr)
        return 2

    try:
        result = verify_run(record, key)
    except VerifyError as exc:
        print(f"NOT VERIFIED: {exc}")
        return 1
    print(f"VERIFIED ({len(result.events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
