#!/usr/bin/env python3
"""Compare the vendored VIP SDK header with a pinned core checkout."""

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--vendored", type=Path, default=Path("include/vip.h"))
    args = parser.parse_args()
    upstream = args.core_root / "include/vip.h"
    if upstream.read_bytes() != args.vendored.read_bytes():
        raise SystemExit("vendored include/vip.h differs from pinned cs2-vip core")
    print("Vendored VIP SDK matches pinned core byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
