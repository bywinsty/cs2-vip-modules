# Clean Linux x86-64 module build

Ubuntu 24.04, Python 3.12, and Clang 18 are the supported build environment.
The package manifest is authoritative for module directories, build roots,
plugin names, aliases, binaries, VDF files, and packaged files.

Before building, validate the repository contracts:

```bash
python .github/scripts/sync_build_files.py
python .github/scripts/manifest_contract.py --manifest .github/package-manifest.json
python .github/scripts/verify_vip_sdk.py --core-root /path/to/cs2-vip-at-VIP_CORE_REF
```

Clone AMBuild, Metamod, HL2SDK CS2, and SchemaEntity at the revisions in
`.github/workflows/build.yml` into a temporary dependency root. Copy
`metamod-source/hl2sdk-manifests` to a temporary manifest directory, then run
the idempotent compatibility helper against those temporary dependencies:

```bash
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
python .github/scripts/apply_sdk_compatibility_patches.py \
  --sdk-root "$VIP_DEPS_ROOT/external/hl2sdk-cs2" \
  --manifest-path "$VIP_MANIFESTS/manifests/cs2.json" \
  --schema-root "$VIP_DEPS_ROOT/external/SchemaEntity" \
  --require-include public/game/server
```

For example, build `VIP_AntiFlash` from its manifest-declared build root:

```bash
mkdir VIP_AntiFlash/source/build
cd VIP_AntiFlash/source/build
CC=clang-18 CXX=clang++-18 python ../configure.py \
  --sdks cs2 --targets x86_64 --enable-optimize --disable-debug \
  --plugin-name vip_af --plugin-alias vip_af \
  --hl2sdk-manifests="$VIP_MANIFESTS" \
  --mms_path="$VIP_DEPS_ROOT/external/metamod-source" \
  --hl2sdk-root="$VIP_DEPS_ROOT/external" \
  --schemaentity-root="$VIP_DEPS_ROOT/external/SchemaEntity" \
  --vip-sdk-root="$(git rev-parse --show-toplevel)/include"
ambuild
```

The same command applies to every package using its `build_root`,
`plugin_name`, and `plugin_alias` fields. CI additionally validates the exact
package layout, ELF hardening, archive reproducibility, and a second independent
build of the representative `VIP_Test` module.
