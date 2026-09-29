# Acquisition notes — repo-factory

## Executive summary

`repo-factory` is a focused open-source `toolkit` utility: repo-factory — a focused developer toolkit.

It is designed as a **portable Node toolkit** with a library API, CLI, tests, and a public documentation site. There is no SaaS dependency and no proprietary runtime.

## Product assets

| Asset | Location | Notes |
| --- | --- | --- |
| Source | `src/` | Library + CLI + tests |
| Brand | `docs/logo.svg` | Official logo used in README and Pages |
| Docs site | `docs/` | GitHub Pages (`/docs` on `main`) |
| License | `LICENSE` | MIT |
| Release | `v1.0.0` | First stable tagged release |
| Funding | `.github/FUNDING.yml` | GitHub Sponsors + thanks.dev |

## Technical due diligence

- **Language:** JavaScript (CommonJS), Node.js 18+
- **Dependencies:** zero runtime dependencies
- **Network:** none required for core operation
- **Telemetry:** none
- **Tests:** `node:test` smoke suite
- **Distribution:** git clone / GitHub Releases

## Commercial / integration posture

Suitable as:

1. A CLI in developer platforms and CI templates
2. A small library import inside larger Node services
3. A reference implementation for `toolkit` transforms

## Risks & constraints

- Scope is intentionally narrow; it is not a multi-product suite.
- Semver major will be required for removing `run(argv)`.
- GitHub Pages availability depends on public repository settings.

## Contact

Open a GitHub Discussion/Issue on `https://github.com/theworker02/repo-factory` or see [SUPPORT.md](./SUPPORT.md).
