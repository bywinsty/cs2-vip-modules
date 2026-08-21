#!/usr/bin/env python3
"""Synchronize canonical module build files and enforce explicit dependency roots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / ".github/package-manifest.json"
TEMPLATES = ROOT / ".github/templates"
GENERATED = ("AMBuildScript", "configure.py")


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def discover_build_root(module_dir: Path) -> Path:
    matches = [candidate for candidate in (module_dir, module_dir / "source", module_dir / "src") if (candidate / "AMBuildScript").is_file()]
    if len(matches) != 1:
        raise ValueError(f"{module_dir.name}: expected exactly one build root, found {matches}")
    return matches[0]


def migrate_manifest(manifest: dict) -> bool:
    changed = manifest.get("version") != 2
    for module, package in sorted(manifest["packages"].items()):
        if all(field in package for field in ("module_dir", "build_root", "plugin_name", "plugin_alias")):
            continue
        module_dir = ROOT / module
        build_root = discover_build_root(module_dir)
        build_text = (build_root / "AMBuildScript").read_text(encoding="utf-8")
        names = re.findall(r"self\.plugin_name = '([^']+)'", build_text)
        aliases = re.findall(r"self\.plugin_alias = '([^']+)'", build_text)
        if len(names) != 1 or len(aliases) != 1:
            raise ValueError(f"{module}: could not derive plugin name/alias")
        package.update(
            module_dir=module_dir.relative_to(ROOT).as_posix(),
            build_root=build_root.relative_to(ROOT).as_posix(),
            plugin_name=names[0],
            plugin_alias=aliases[0],
        )
        changed = True
    if changed:
        manifest["version"] = 2
    return changed


def migrated_ambuilder(content: str) -> str:
    content = content.replace(
        "os.path.join(builder.sourcePath, '..', 'SchemaEntity')",
        "MMSPlugin.schemaentity_root",
    )
    content = re.sub(
        r"os\.path\.join\('\.\.', 'SchemaEntity', '([^']+)'\)",
        r"os.path.join(MMSPlugin.schemaentity_root, '\1')",
        content,
    )
    content = re.sub(
        r"^\s*os\.path\.join\(sdk\.path, 'tier1', 'generichash\.cpp'\),?\s*\n",
        "",
        content,
        flags=re.MULTILINE,
    )
    return content


def validate_package(module: str, package: dict) -> None:
    for field in ("module_dir", "build_root", "plugin_name", "plugin_alias", "binary", "vdf", "files"):
        if not package.get(field):
            raise ValueError(f"{module}: missing manifest field {field}")
    if Path(package["binary"]).stem != package["plugin_name"]:
        raise ValueError(f"{module}: plugin_name does not match binary")
    if Path(package["vdf"]).stem != package["plugin_alias"]:
        raise ValueError(f"{module}: plugin_alias does not match VDF")


def synchronize(write_changes: bool) -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed_paths: list[str] = []
    if manifest.get("version") != 2:
        if not write_changes:
            raise ValueError("manifest v2 migration is required; run --write")
        if migrate_manifest(manifest):
            write(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
            changed_paths.append(MANIFEST.relative_to(ROOT).as_posix())

    for module, package in sorted(manifest["packages"].items()):
        validate_package(module, package)
        build_root = ROOT / package["build_root"]
        if not build_root.is_dir() or not (build_root / "AMBuilder").is_file():
            raise ValueError(f"{module}: invalid build_root {package['build_root']}")
        for name in GENERATED:
            expected = (TEMPLATES / name).read_text(encoding="utf-8")
            target = build_root / name
            actual = target.read_text(encoding="utf-8") if target.exists() else ""
            if actual != expected:
                if not write_changes:
                    raise ValueError(f"{module}: generated {name} has drifted")
                write(target, expected)
                changed_paths.append(target.relative_to(ROOT).as_posix())
        ambuilder = build_root / "AMBuilder"
        actual = ambuilder.read_text(encoding="utf-8")
        expected = migrated_ambuilder(actual)
        if actual != expected:
            if not write_changes:
                raise ValueError(f"{module}: AMBuilder still discovers SchemaEntity relatively")
            write(ambuilder, expected)
            changed_paths.append(ambuilder.relative_to(ROOT).as_posix())
        if "SchemaEntity" in expected and "MMSPlugin.schemaentity_root" not in expected:
            raise ValueError(f"{module}: AMBuilder has an unsupported SchemaEntity reference")

    local_headers = sorted(path for path in ROOT.glob("VIP_*/**/vip.h") if path.is_file())
    if local_headers:
        if not write_changes:
            raise ValueError(f"local VIP SDK headers remain: {[p.relative_to(ROOT).as_posix() for p in local_headers]}")
        for header in local_headers:
            header.unlink()
            changed_paths.append(header.relative_to(ROOT).as_posix())
    local_manifests = sorted(path for path in ROOT.glob("VIP_*/**/hl2sdk-manifests") if path.is_dir())
    if local_manifests:
        if not write_changes:
            raise ValueError(f"tracked local SDK manifests remain: {[p.relative_to(ROOT).as_posix() for p in local_manifests]}")
        for manifest_dir in local_manifests:
            for file_path in sorted((path for path in manifest_dir.rglob("*") if path.is_file()), reverse=True):
                changed_paths.append(file_path.relative_to(ROOT).as_posix())
                file_path.unlink()
            for directory in sorted((path for path in manifest_dir.rglob("*") if path.is_dir()), reverse=True):
                directory.rmdir()
            manifest_dir.rmdir()
    if not (ROOT / "include/vip.h").is_file():
        raise ValueError("canonical include/vip.h is missing")
    return changed_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        changed = synchronize(args.write)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"build file synchronization failed: {exc}")
    if changed:
        print("Synchronized build files:")
        print(*changed, sep="\n")
    else:
        print("Canonical build files are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
