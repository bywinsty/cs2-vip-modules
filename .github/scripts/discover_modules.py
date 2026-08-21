#!/usr/bin/env python3
"""Build the module matrix exclusively from package-manifest.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    root = args.manifest.resolve().parents[1]
    packages = json.loads(args.manifest.read_text(encoding="utf-8"))["packages"]
    entries = []
    required = ("AMBuildScript", "AMBuilder", "PackageScript", "configure.py")
    for module, package in sorted(packages.items()):
        for field in ("module_dir", "build_root", "plugin_name", "plugin_alias", "binary", "vdf", "files"):
            if not package.get(field):
                raise SystemExit(f"{module}: missing manifest field {field}")
        build_root = root / package["build_root"]
        missing = [name for name in required if not (build_root / name).is_file()]
        if missing:
            raise SystemExit(f"{module}: missing build files: {missing}")
        entries.append({
            "module": module,
            "module_dir": package["module_dir"],
            "build_root": package["build_root"],
            "plugin_name": package["plugin_name"],
            "plugin_alias": package["plugin_alias"],
            "binary": package["binary"],
        })
    with args.github_output.open("a", encoding="utf-8") as output:
        output.write("modules=" + json.dumps(entries, separators=(",", ":")) + "\n")
        output.write(f"count={len(entries)}\n")
    print(f"Discovered {len(entries)} modules exclusively from the manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
