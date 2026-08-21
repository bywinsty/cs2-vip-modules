# Runtime validation gate

The combined runtime gate is Linux x86-64 only and must run on a disposable CS2 dedicated server. It is deliberately not registered as a GitHub self-hosted runner.

## Mark the test server

Copy `.github/runtime-sentinel.example.json` to `<CS2_SERVER_ROOT>/.vip-ci-test-server`, then replace every placeholder with exact installed versions and paths. The harness refuses to run without the sentinel, on a production-marked server, with paths outside the root, without Metamod/runtime dependencies, while the server is already running, or with insufficient disk space.

The `module_log_pattern` is formatted once for every `plugin_alias` in `.github/package-manifest.json`; adjust it only if the installed Metamod version formats `meta list` entries differently.

## Verify and run

First run the manual **Runtime Release Preflight** workflow for the `dev` tag. On the marked server:

```bash
export CS2_SERVER_ROOT=/srv/cs2-vip-ci
python3 .github/scripts/runtime_validate.py \
  --core-repository bywinsty/cs2-vip \
  --modules-repository bywinsty/cs2-vip-modules \
  --tag dev \
  --report-dir /var/tmp/cs2-vip-runtime-report
```

The harness verifies the checksums and GitHub attestations for the core and combined modules releases, installs both through a temporary overlay, starts CS2 in LAN/insecure mode on the fixed map, executes `meta version` and `meta list`, requires the legacy/V2 ABI probe marker and all 35 manifest aliases, rejects crash/load/interface/unresolved-symbol markers, shuts the server down, and restores the previous files.

It always writes `runtime-validation.json` and `runtime-validation-logs.zip`. Preserve both after successful and failed runs.

## Stable release authorization

The `dev` prerelease remains automatic. A future `Modules` stable release is blocked unless repository variables `RUNTIME_VALIDATION_SHA` and `RUNTIME_VALIDATION_REPORT_URL` identify a successful report for the exact stable commit. The report URL is included in release notes. Do not set these variables until core, both ABI probes, all 35 modules, shutdown, and rollback are successful.
