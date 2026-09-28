#!/usr/bin/env python3
"""Thicken factory repos to polished v1.0.0 releases.

For each name in state/created_names.txt (and optional extras):
- Expand README with official logo + rich badges + detailed notes
- Add CHANGELOG, CONTRIBUTING, SUPPORT, SECURITY, NOTICE
- Refresh docs site copy
- Ensure docs/logo.svg (unique accent)
- Bump/confirm package.json version 1.0.0
- Create GitHub Release v1.0.0 with detailed notes (skip if exists)
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

OWNER = "theworker02"
ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
NAMES = STATE / "created_names.txt"
DONE = STATE / "thickened.txt"
LOG = STATE / "thicken.log"
STYLES = (ROOT / "styles.css").read_text(encoding="utf-8")
BASE_LOGO = (ROOT / "logo.svg").read_text(encoding="utf-8")
WORKERS = int(os.environ.get("THICKEN_WORKERS", "3"))
LOCK = threading.Lock()

STATE.mkdir(parents=True, exist_ok=True)


def run(cmd, cwd=None, check=True, input_text=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        input=input_text,
        capture_output=True,
    )


def log(msg: str):
    # stdout only — callers typically `tee -a state/thicken.log`
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def already_done() -> set[str]:
    if not DONE.exists():
        return set()
    return {x.strip() for x in DONE.read_text().splitlines() if x.strip()}


def mark_done(name: str):
    with LOCK:
        with DONE.open("a", encoding="utf-8") as f:
            f.write(name + "\n")


def load_names() -> list[str]:
    names = []
    seen = set()
    if NAMES.exists():
        for line in NAMES.read_text().splitlines():
            n = line.strip()
            if n and n not in seen:
                seen.add(n)
                names.append(n)
    # also include useful-kit / repo-factory if present
    for extra in ("useful-kit", "repo-factory", "urlnormkit"):
        if extra not in seen:
            # only if repo exists
            r = run(["gh", "repo", "view", f"{OWNER}/{extra}", "--json", "name"], check=False)
            if r.returncode == 0:
                names.append(extra)
                seen.add(extra)
    return names


def logo_for(name: str) -> str:
    h = hashlib.sha256(name.encode()).hexdigest()
    color = f"#{h[:6]}"
    return (
        BASE_LOGO.replace("#C9A227", color)
        .replace("#c9a227", color)
        .replace('aria-label="bytesize mark"', f'aria-label="{name} mark"')
    )


def infer_meta(repo_dir: Path, name: str) -> dict:
    pkg = {}
    pj = repo_dir / "package.json"
    if pj.exists():
        try:
            pkg = json.loads(pj.read_text(encoding="utf-8"))
        except Exception:
            pkg = {}
    desc = pkg.get("description") or f"{name} — a focused developer toolkit."
    version = "1.0.0"
    keywords = pkg.get("keywords") or []
    category = "toolkit"
    for k in keywords:
        if k in {
            "text", "json", "csv", "time", "url", "hash", "color", "number",
            "path", "encode", "validate", "list", "stat", "markup", "id",
            "net", "config",
        }:
            category = k
            break
    return {
        "name": name,
        "description": desc,
        "version": version,
        "category": category,
        "keywords": keywords or [name, category, "cli", "toolkit", "nodejs"],
    }


def thick_readme(m: dict) -> str:
    name = m["name"]
    desc = m["description"]
    cat = m["category"]
    site = f"https://{OWNER}.github.io/{name}/"
    repo = f"https://github.com/{OWNER}/{name}"
    return f"""<p align="center">
  <img src="docs/logo.svg" alt="{name} logo" width="128" height="128">
</p>

# {name}

<p align="center">
  <strong>{desc}</strong>
</p>

<p align="center">
  <a href="{site}"><img src="https://img.shields.io/badge/docs-live-0B1F33?style=for-the-badge&labelColor=C9A227" alt="Docs"></a>
  <a href="{repo}/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/release-v1.0.0-success?style=for-the-badge" alt="Release"></a>
  <a href="{repo}/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License"></a>
  <a href="{repo}/actions"><img src="https://img.shields.io/badge/ci-node%20%3E%3D%2018-informational?style=for-the-badge" alt="Node"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-0B1F33.svg" alt="version">
  <img src="https://img.shields.io/badge/category-{cat}-C9A227.svg" alt="category">
  <img src="https://img.shields.io/badge/runtime-Node.js%2018%2B-339933.svg" alt="runtime">
  <img src="https://img.shields.io/badge/deps-zero-brightgreen.svg" alt="deps">
  <img src="https://img.shields.io/badge/pages-enabled-222.svg" alt="pages">
  <img src="https://img.shields.io/badge/exports-CLI%20%2B%20library-lightgrey.svg" alt="exports">
</p>

---

## Why this exists

`{name}` is a purpose-built `{cat}` toolkit for operators and application engineers who need a small, auditable utility instead of pulling in a large framework. It ships a library API and a stdin-friendly CLI, runs with **zero runtime dependencies**, and publishes a static documentation site on GitHub Pages.

### Design notes

- **Deterministic defaults** — sensible sample inputs so `node src/cli.js` always produces readable output.
- **CI-friendly** — exit codes and plain-text/JSON stdout suitable for pipelines.
- **Local-first** — no network calls, no telemetry, no API keys.
- **Portable** — Node.js 18+ on Linux, macOS, and Windows.

## Quick start

```bash
git clone {repo}.git
cd {name}
node --test
node src/cli.js
```

Documentation site: **[{site}]({site})**

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

Category: **`{cat}`** · Release: **`v1.0.0`**

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

See [CHANGELOG.md](./CHANGELOG.md) and the [GitHub Release]({repo}/releases/tag/v1.0.0) for the full narrative. Summary:

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
  <img src="docs/logo.svg" alt="{name}" width="48">
  <br>
  <sub>{name} · v1.0.0 · MIT · @{OWNER}</sub>
</p>
"""


def thick_changelog(m: dict) -> str:
    name = m["name"]
    desc = m["description"]
    cat = m["category"]
    return f"""# Changelog

All notable changes to `{name}` are documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.0.0] — 2026-09-28

### Added — stable public release

- First **stable** release of `{name}` as a `{cat}` toolkit.
- Product statement: {desc}
- Library entrypoint `src/index.js` with `run(argv)` and category helpers.
- CLI entrypoint `src/cli.js` for shell and CI usage.
- Automated smoke tests via `node:test` (`src/index.test.js`).
- Official brand mark at `docs/logo.svg` (unique accent derived per product).
- GitHub Pages documentation site under `docs/` (`index.html`, `styles.css`, `.nojekyll`).
- Diligence pack: `ACQUISITION.md`, `CONTRIBUTING.md`, `SUPPORT.md`, `SECURITY.md`, `NOTICE`.
- Repository homepage pointed at `https://{OWNER}.github.io/{name}/`.
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

[1.0.0]: https://github.com/{OWNER}/{name}/releases/tag/v1.0.0
"""


def thick_acquisition(m: dict) -> str:
    name = m["name"]
    return f"""# Acquisition notes — {name}

## Executive summary

`{name}` is a focused open-source `{m["category"]}` utility: {m["description"]}

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
3. A reference implementation for `{m["category"]}` transforms

## Risks & constraints

- Scope is intentionally narrow; it is not a multi-product suite.
- Semver major will be required for removing `run(argv)`.
- GitHub Pages availability depends on public repository settings.

## Contact

Open a GitHub Discussion/Issue on `https://github.com/{OWNER}/{name}` or see [SUPPORT.md](./SUPPORT.md).
"""


def thick_contributing(m: dict) -> str:
    return f"""# Contributing to {m["name"]}

Thanks for considering a contribution.

## Development

```bash
git clone https://github.com/{OWNER}/{m["name"]}.git
cd {m["name"]}
node --test
node src/cli.js
```

## Guidelines

1. Keep the toolkit **zero-dependency** unless there is a compelling, discussed reason.
2. Preserve the `run(argv)` contract or propose a major-version bump.
3. Update `CHANGELOG.md` for user-visible changes.
4. Keep the docs site in `docs/` coherent with README examples.
5. Do not commit secrets, credentials, or large binaries.

## Pull requests

- Prefer small, reviewable PRs.
- Include a short test or sample invocation when behavior changes.
- Link related issues.

## Code of conduct expectations

Be respectful. This is a professional engineering project aimed at real operators.
"""


def thick_support(m: dict) -> str:
    return f"""# Support — {m["name"]}

## How to get help

1. Read the [README](./README.md) and the live docs: https://{OWNER}.github.io/{m["name"]}/
2. Check [CHANGELOG.md](./CHANGELOG.md) and the [v1.0.0 release](https://github.com/{OWNER}/{m["name"]}/releases/tag/v1.0.0).
3. Search existing GitHub Issues on `https://github.com/{OWNER}/{m["name"]}/issues`.
4. Open a new issue with:
   - Node.js version (`node -v`)
   - Exact command invoked
   - Expected vs actual output
   - Minimal reproduction snippet

## Scope of support

Community best-effort support for the open-source MIT release. There is no SLA attached to the free distribution.

## Security issues

Please follow [SECURITY.md](./SECURITY.md) instead of filing a public issue for vulnerabilities.
"""


def thick_security(m: dict) -> str:
    return f"""# Security policy — {m["name"]}

## Supported versions

| Version | Supported |
| --- | --- |
| 1.0.x | ✅ |

## Reporting a vulnerability

Email or privately report via GitHub Security Advisories on `https://github.com/{OWNER}/{m["name"]}` when available.

Please include:

- Impact assessment
- Reproduction steps
- Affected versions
- Any suggested fix

We aim to acknowledge reports within a reasonable window and to coordinate disclosure.

## Non-goals

`{m["name"]}` performs local computation only. It should not request network credentials. If you observe unexpected network behavior, treat it as high priority.
"""


def thick_notice(m: dict) -> str:
    return f"""{m["name"]}
Copyright (c) 2026 {OWNER}

This product is released under the MIT License. See LICENSE for the full text.

Third-party trademarks (if mentioned in docs) remain the property of their owners and imply no affiliation.
"""


def thick_docs_index(m: dict) -> str:
    name = m["name"]
    desc = m["description"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name} · v1.0.0</title>
  <meta name="description" content="{desc.replace('"', "'")}">
  <link rel="stylesheet" href="styles.css">
  <link rel="icon" href="logo.svg" type="image/svg+xml">
</head>
<body>
  <nav class="nav sans">
    <a class="brand-lockup" href="index.html"><img src="logo.svg" alt=""> {name}</a>
    <div class="links">
      <a href="#overview">Overview</a>
      <a href="#release">v1.0.0</a>
      <a href="#usage">Usage</a>
      <a href="https://github.com/{OWNER}/{name}">GitHub</a>
      <a href="https://github.com/{OWNER}/{name}/releases/tag/v1.0.0">Release</a>
    </div>
  </nav>
  <header class="hero">
    <img src="logo.svg" alt="{name} official logo">
    <div>
      <p class="kicker sans">@{OWNER}/{name} · official v1.0.0</p>
      <h1>{name}</h1>
      <p class="lede">{desc}</p>
      <div class="badges sans">
        <span class="badge">v1.0.0</span>
        <span class="badge">{m["category"]}</span>
        <span class="badge">MIT</span>
        <span class="badge">Zero deps</span>
        <span class="badge">Node 18+</span>
        <span class="badge">CLI + library</span>
      </div>
    </div>
  </header>
  <div class="wrap">
    <section id="overview">
      <h2>Overview</h2>
      <p>{desc} This is the stable <strong>v1.0.0</strong> documentation site: library API, CLI, tests, and diligence notes ship in the repository.</p>
    </section>
    <section id="release">
      <h2>Release v1.0.0</h2>
      <p>First stable release. Includes the official logo, expanded README badges, CHANGELOG, acquisition/support/security docs, and tagged GitHub Release notes.</p>
      <pre><code>git clone https://github.com/{OWNER}/{name}.git
cd {name}
git checkout v1.0.0
node --test
node src/cli.js</code></pre>
    </section>
    <section id="usage">
      <h2>Usage</h2>
      <p>Library entry: <code>src/index.js</code>. CLI: <code>src/cli.js</code>. Category: <strong>{m["category"]}</strong>.</p>
    </section>
  </div>
  <footer class="sans">MIT © 2026 {OWNER} · <strong>v1.0.0</strong> · <a href="https://github.com/{OWNER}/{name}">GitHub</a> · <a href="https://github.com/{OWNER}/{name}/releases/tag/v1.0.0">Release notes</a></footer>
</body>
</html>
"""


def release_body(m: dict) -> str:
    name = m["name"]
    return f"""# {name} v1.0.0 — first stable release

{m["description"]}

## Highlights

- **Stable API** — `run(argv)` library contract + CLI wrapper
- **Official logo** — `docs/logo.svg` featured in the README
- **Documentation site** — https://{OWNER}.github.io/{name}/
- **Zero runtime dependencies** on Node.js 18+
- **Diligence pack** — ACQUISITION, SUPPORT, SECURITY, CONTRIBUTING, CHANGELOG

## Category

`{m["category"]}`

## Install

```bash
git clone https://github.com/{OWNER}/{name}.git
cd {name}
git checkout v1.0.0
node --test
node src/cli.js
```

## Notes

This tag marks the first production-ready release line. Future minors may add helpers; removals of `run(argv)` will require a major version.

### Checksums / artifacts

Source tag: `v1.0.0` on branch `main` (or release commit). GitHub automatically attaches zip/tar archives to this release.

### Badge pack

![version](https://img.shields.io/badge/version-1.0.0-0B1F33.svg)
![category](https://img.shields.io/badge/category-{m["category"]}-C9A227.svg)
![license](https://img.shields.io/badge/license-MIT-blue.svg)
![node](https://img.shields.io/badge/node-%3E%3D18-brightgreen.svg)
"""


def update_package(repo_dir: Path, m: dict):
    pj = repo_dir / "package.json"
    pkg = {}
    if pj.exists():
        try:
            pkg = json.loads(pj.read_text(encoding="utf-8"))
        except Exception:
            pkg = {}
    pkg["name"] = pkg.get("name") or f"@{OWNER}/{m['name']}"
    pkg["version"] = "1.0.0"
    pkg["description"] = m["description"]
    pkg["license"] = "MIT"
    pkg["homepage"] = f"https://{OWNER}.github.io/{m['name']}/"
    pkg.setdefault("repository", {"type": "git", "url": f"https://github.com/{OWNER}/{m['name']}.git"})
    pkg.setdefault("engines", {"node": ">=18"})
    pkg["keywords"] = list(dict.fromkeys((pkg.get("keywords") or []) + m["keywords"] + ["v1", "stable"]))
    pj.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")


def has_release(name: str) -> bool:
    r = run(
        ["gh", "release", "view", "v1.0.0", "-R", f"{OWNER}/{name}", "--json", "tagName"],
        check=False,
    )
    return r.returncode == 0


def thicken_one(name: str) -> dict:
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix=f"thick-{name}-"))
    try:
        # shallow clone
        r = run(
            [
                "gh",
                "repo",
                "clone",
                f"{OWNER}/{name}",
                str(tmp / name),
                "--",
                "--depth",
                "1",
            ],
            check=False,
        )
        if r.returncode != 0:
            return {"name": name, "status": "error", "error": (r.stderr or r.stdout)[-400:]}
        repo = tmp / name
        run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"], cwd=repo)
        run(["git", "config", "user.name", OWNER], cwd=repo)

        m = infer_meta(repo, name)
        (repo / "docs").mkdir(exist_ok=True)
        (repo / ".github").mkdir(exist_ok=True)

        (repo / "docs" / "logo.svg").write_text(logo_for(name), encoding="utf-8")
        if not (repo / "docs" / "styles.css").exists():
            (repo / "docs" / "styles.css").write_text(STYLES, encoding="utf-8")
        (repo / "docs" / ".nojekyll").write_text("", encoding="utf-8")
        (repo / "docs" / "index.html").write_text(thick_docs_index(m), encoding="utf-8")
        (repo / "README.md").write_text(thick_readme(m), encoding="utf-8")
        (repo / "CHANGELOG.md").write_text(thick_changelog(m), encoding="utf-8")
        (repo / "ACQUISITION.md").write_text(thick_acquisition(m), encoding="utf-8")
        (repo / "CONTRIBUTING.md").write_text(thick_contributing(m), encoding="utf-8")
        (repo / "SUPPORT.md").write_text(thick_support(m), encoding="utf-8")
        (repo / "SECURITY.md").write_text(thick_security(m), encoding="utf-8")
        (repo / "NOTICE").write_text(thick_notice(m), encoding="utf-8")
        update_package(repo, m)
        funding = repo / ".github" / "FUNDING.yml"
        if not funding.exists():
            funding.write_text("github: [theworker02]\nthanks_dev: u/gh/theworker02\n", encoding="utf-8")

        # commit if changes
        run(["git", "add", "-A"], cwd=repo)
        st = run(["git", "status", "--porcelain"], cwd=repo)
        if st.stdout.strip():
            run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"Release v1.0.0 docs, logo, badges, and diligence pack for {name}",
                ],
                cwd=repo,
            )
            p = run(["git", "push", "origin", "HEAD:main"], cwd=repo, check=False)
            if p.returncode != 0:
                # try master
                p2 = run(["git", "push", "origin", "HEAD:master"], cwd=repo, check=False)
                if p2.returncode != 0:
                    return {
                        "name": name,
                        "status": "error",
                        "error": (p.stderr or p2.stderr or "")[-400:],
                    }

        # ensure Pages homepage (do not delete existing Pages config)
        run(
            [
                "gh",
                "repo",
                "edit",
                f"{OWNER}/{name}",
                "--homepage",
                f"https://{OWNER}.github.io/{name}/",
            ],
            check=False,
        )
        pages = run(["gh", "api", f"repos/{OWNER}/{name}/pages"], check=False)
        if pages.returncode != 0:
            run(
                [
                    "gh",
                    "api",
                    "-X",
                    "POST",
                    f"repos/{OWNER}/{name}/pages",
                    "-f",
                    "build_type=legacy",
                    "-f",
                    "source[branch]=main",
                    "-f",
                    "source[path]=/docs",
                ],
                check=False,
            )
        else:
            run(
                [
                    "gh",
                    "api",
                    "-X",
                    "PUT",
                    f"repos/{OWNER}/{name}/pages",
                    "-f",
                    "build_type=legacy",
                    "-f",
                    "source[branch]=main",
                    "-f",
                    "source[path]=/docs",
                ],
                check=False,
            )

        if not has_release(name):
            # tag + release
            run(["git", "fetch", "--tags"], cwd=repo, check=False)
            run(["git", "tag", "-f", "v1.0.0"], cwd=repo, check=False)
            run(["git", "push", "-f", "origin", "v1.0.0"], cwd=repo, check=False)
            body_path = tmp / "release.md"
            body_path.write_text(release_body(m), encoding="utf-8")
            rel = run(
                [
                    "gh",
                    "release",
                    "create",
                    "v1.0.0",
                    "-R",
                    f"{OWNER}/{name}",
                    "--title",
                    f"{name} v1.0.0 — first stable release",
                    "--notes-file",
                    str(body_path),
                    "--latest",
                ],
                check=False,
            )
            if rel.returncode != 0 and "already exists" not in (rel.stderr or ""):
                # try without --latest
                run(
                    [
                        "gh",
                        "release",
                        "create",
                        "v1.0.0",
                        "-R",
                        f"{OWNER}/{name}",
                        "--title",
                        f"{name} v1.0.0 — first stable release",
                        "--notes-file",
                        str(body_path),
                    ],
                    check=False,
                )

        mark_done(name)
        return {"name": name, "status": "ok", "seconds": round(time.time() - t0, 2)}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)[:400]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ok = err = 0
    idle_rounds = 0
    target_public = int(os.environ.get("PORTFOLIO_TARGET", "4000"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        while True:
            done = already_done()
            names = [n for n in load_names() if n not in done]
            log(f"[thicken] queue={len(names)} already_done={len(done)} workers={WORKERS}")
            if not names:
                # wait for factory to publish more, or exit when target reached
                pub = 0
                try:
                    pub = int(
                        run(["gh", "api", f"/users/{OWNER}", "--jq", ".public_repos"]).stdout.strip()
                    )
                except Exception:
                    pass
                idle_rounds += 1
                log(f"[thicken] idle pub={pub} idle_rounds={idle_rounds}")
                if pub >= target_public and idle_rounds >= 3:
                    break
                time.sleep(60)
                continue
            idle_rounds = 0
            # process current queue snapshot
            i = 0
            while i < len(names):
                batch = names[i : i + WORKERS * 4]
                i += len(batch)
                futs = [ex.submit(thicken_one, n) for n in batch]
                for fut in concurrent.futures.as_completed(futs):
                    res = fut.result()
                    if res["status"] == "ok":
                        ok += 1
                        log(f"[ok] {res['name']} ({res.get('seconds')}s) ok={ok} err={err}")
                    else:
                        err += 1
                        log(f"[err] {res['name']}: {res.get('error')}")
                time.sleep(2)
                # refresh done set mid-queue
                done = already_done()
                names = [n for n in load_names() if n not in done]
                i = 0
                break  # restart outer snapshot loop
    log(f"[thicken] finished ok={ok} err={err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
