<p align="center">
  <img src="docs/logo.svg" alt="repo-factory logo" width="128" height="128">
</p>

# repo-factory

<p align="center">
  <strong>repo-factory — a focused developer toolkit.</strong>
</p>

<p align="center">
  <a href="https://theworker02.github.io/repo-factory/"><img src="https://img.shields.io/badge/docs-live-0B1F33?style=for-the-badge&labelColor=C9A227" alt="Docs"></a>
  <a href="https://github.com/theworker02/repo-factory/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/release-v1.0.0-success?style=for-the-badge" alt="Release"></a>
  <a href="https://github.com/theworker02/repo-factory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/theworker02/repo-factory/actions"><img src="https://img.shields.io/badge/ci-node%20%3E%3D%2018-informational?style=for-the-badge" alt="Node"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-0B1F33.svg" alt="version">
  <img src="https://img.shields.io/badge/category-toolkit-C9A227.svg" alt="category">
  <img src="https://img.shields.io/badge/runtime-Node.js%2018%2B-339933.svg" alt="runtime">
  <img src="https://img.shields.io/badge/deps-zero-brightgreen.svg" alt="deps">
  <img src="https://img.shields.io/badge/pages-enabled-222.svg" alt="pages">
  <img src="https://img.shields.io/badge/exports-CLI%20%2B%20library-lightgrey.svg" alt="exports">
</p>

---

## Why this exists

`repo-factory` is a purpose-built `toolkit` toolkit for operators and application engineers who need a small, auditable utility instead of pulling in a large framework. It ships a library API and a stdin-friendly CLI, runs with **zero runtime dependencies**, and publishes a static documentation site on GitHub Pages.

### Design notes

- **Deterministic defaults** — sensible sample inputs so `node src/cli.js` always produces readable output.
- **CI-friendly** — exit codes and plain-text/JSON stdout suitable for pipelines.
- **Local-first** — no network calls, no telemetry, no API keys.
- **Portable** — Node.js 18+ on Linux, macOS, and Windows.

## Quick start

```bash
git clone https://github.com/theworker02/repo-factory.git
cd repo-factory
node --test
node src/cli.js
```

Documentation site: **[https://theworker02.github.io/repo-factory/](https://theworker02.github.io/repo-factory/)**

## Install / use as a library

```js
const lib = require("./src/index.js");
const result = lib.run([]);
console.log(result);
```

Binary entry (from `package.json`):

```bash
node src/cli.js --help 2>/dev/null || node src/cli.js
```

## API surface

| Export area | Location | Notes |
| --- | --- | --- |
| Library | [`src/index.js`](./src/index.js) | Category-specific helpers + `run(argv)` |
| CLI | [`src/cli.js`](./src/cli.js) | Thin argv wrapper; non-zero exit on failure |
| Tests | [`src/index.test.js`](./src/index.test.js) | `node:test` smoke coverage |

Category: **`toolkit`** · Release: **`v1.0.0`**

## Badges & status notes

| Badge | Meaning |
| --- | --- |
| docs live | GitHub Pages site served from `/docs` on `main` |
| release v1.0.0 | First stable tagged release with notes below |
| license MIT | Permissive use, modification, and redistribution |
| Node >= 18 | Uses modern Node APIs (`node:test`, stable URL/crypto) |
| zero deps | No `dependencies` block required at runtime |
| pages enabled | Product homepage configured on the repository |

## Release notes (v1.0.0)

See [CHANGELOG.md](./CHANGELOG.md) and the [GitHub Release](https://github.com/theworker02/repo-factory/releases/tag/v1.0.0) for the full narrative. Summary:

1. Stable public API via `run(argv)` and category helpers.
2. Official logo asset under `docs/logo.svg` (also shown above).
3. Polished GitHub Pages documentation.
4. Acquisition / support / security docs for diligence readers.
5. MIT licensing with funding metadata for sponsors.

## Documentation map

| Doc | Purpose |
| --- | --- |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and release detail |
| [ACQUISITION.md](./ACQUISITION.md) | Diligence-oriented product brief |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to propose changes |
| [SUPPORT.md](./SUPPORT.md) | How to get help |
| [SECURITY.md](./SECURITY.md) | Vulnerability reporting |
| [docs/](./docs/) | Public site sources |

## License

MIT — see [LICENSE](./LICENSE).

---

<p align="center">
  <img src="docs/logo.svg" alt="repo-factory" width="48">
  <br>
  <sub>repo-factory · v1.0.0 · MIT · @theworker02</sub>
</p>
