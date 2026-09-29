# Changelog

All notable changes to `repo-factory` are documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.0.0] — 2026-09-28

### Added — stable public release

- First **stable** release of `repo-factory` as a `toolkit` toolkit.
- Product statement: repo-factory — a focused developer toolkit.
- Library entrypoint `src/index.js` with `run(argv)` and category helpers.
- CLI entrypoint `src/cli.js` for shell and CI usage.
- Automated smoke tests via `node:test` (`src/index.test.js`).
- Official brand mark at `docs/logo.svg` (unique accent derived per product).
- GitHub Pages documentation site under `docs/` (`index.html`, `styles.css`, `.nojekyll`).
- Diligence pack: `ACQUISITION.md`, `CONTRIBUTING.md`, `SUPPORT.md`, `SECURITY.md`, `NOTICE`.
- Repository homepage pointed at `https://theworker02.github.io/repo-factory/`.
- Funding metadata in `.github/FUNDING.yml`.

### Notes for integrators

- Runtime: Node.js **18+**
- Dependencies: **none** at runtime
- License: **MIT**
- Breaking-change policy: minor/patch releases will not remove `run(argv)` without a major bump.

### Verification performed for this release

- `node --test` smoke path expected to pass on a clean clone.
- CLI invoked with default argv produces non-empty stdout for the sample path.
- Pages artifact paths present under `docs/`.

[1.0.0]: https://github.com/theworker02/repo-factory/releases/tag/v1.0.0
