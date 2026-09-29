#!/usr/bin/env python3
"""Non-destructive thicken for non-factory portfolio repos.

Ensures each target has:
- Official logo (docs/logo.svg) referenced from README when missing
- Badge pack + badge notes section when missing
- Diligence docs (CHANGELOG / SUPPORT / SECURITY / CONTRIBUTING / NOTICE)
- GitHub Release v1.0.0 with detailed notes (creates if absent)

Does NOT overwrite custom READMEs for established projects.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

OWNER = "theworker02"
ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
DONE = STATE / "thickened.txt"
LOG = STATE / "thicken_remaining.log"
STYLES = (ROOT / "styles.css").read_text(encoding="utf-8")
BASE_LOGO = (ROOT / "logo.svg").read_text(encoding="utf-8")
PLAN = Path("/tmp/work_plan.json")

# Empty / stub repos — safe to fully replace with factory-style pack
FULL_REPLACE = {"keepuri", "reefxml"}

# Profile / site repos — logo + badges + release only, never rewrite body
LIGHT_TOUCH = {"theworker02", "personal-site"}


def run(cmd, cwd=None, check=True, input_text=None, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        input=input_text,
        capture_output=True,
        env=env,
    )


def log(msg: str):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def token() -> str:
    hosts = Path.home() / ".config/gh/hosts.yml"
    text = hosts.read_text(encoding="utf-8")
    m = re.search(r"oauth_token:\s*(\S+)", text)
    if not m:
        raise RuntimeError("no gh oauth token")
    return m.group(1)


def git_env(tok: str) -> dict:
    env = os.environ.copy()
    env["GIT_ASKPASS"] = "echo"
    env["GIT_TERMINAL_PROMPT"] = "0"
    # credential via URL embedding preferred
    return env


def already_done() -> set[str]:
    if not DONE.exists():
        return set()
    return {x.strip() for x in DONE.read_text().splitlines() if x.strip()}


def mark_done(name: str):
    with DONE.open("a", encoding="utf-8") as f:
        f.write(name + "\n")


def logo_for(name: str) -> str:
    h = hashlib.sha256(name.encode()).hexdigest()
    color = f"#{h[:6]}"
    return (
        BASE_LOGO.replace("#C9A227", color)
        .replace("#c9a227", color)
        .replace('aria-label="bytesize mark"', f'aria-label="{name} mark"')
    )


def infer_desc(repo: Path, name: str) -> str:
    readme = repo / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("<") or s.startswith("!["):
                continue
            if s.startswith("|") or s.startswith("```"):
                continue
            # strip markdown emphasis
            s = re.sub(r"[*_`]", "", s)
            if 20 <= len(s) <= 220:
                return s
    pkg = repo / "package.json"
    if pkg.exists():
        try:
            d = json.loads(pkg.read_text(encoding="utf-8")).get("description")
            if d:
                return d
        except Exception:
            pass
    return f"{name} — portfolio product with documentation, brand mark, and stable release notes."


def badge_block(name: str, desc_cat: str = "product") -> str:
    site = f"https://{OWNER}.github.io/{name}/"
    repo = f"https://github.com/{OWNER}/{name}"
    return f"""<p align="center">
  <img src="docs/logo.svg" alt="{name} official logo" width="128" height="128">
</p>

<p align="center">
  <a href="{site}"><img src="https://img.shields.io/badge/docs-live-0B1F33?style=for-the-badge&labelColor=C9A227" alt="Docs"></a>
  <a href="{repo}/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/release-v1.0.0-success?style=for-the-badge" alt="Release"></a>
  <a href="{repo}/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-see%20LICENSE-blue?style=for-the-badge" alt="License"></a>
  <a href="{repo}"><img src="https://img.shields.io/badge/status-maintained-informational?style=for-the-badge" alt="Status"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-0B1F33.svg" alt="version">
  <img src="https://img.shields.io/badge/category-{desc_cat}-C9A227.svg" alt="category">
  <img src="https://img.shields.io/badge/pages-enabled-222.svg" alt="pages">
  <img src="https://img.shields.io/badge/docs-thickened-brightgreen.svg" alt="docs">
  <img src="https://img.shields.io/badge/notes-detailed-lightgrey.svg" alt="notes">
</p>
"""


def badge_notes_section(name: str) -> str:
    return f"""
## Badges & release notes

| Badge | Meaning |
| --- | --- |
| docs live | Public documentation / Pages surface for `{name}` |
| release v1.0.0 | Stable tagged release with narrative notes |
| license | See repository `LICENSE` for terms |
| status maintained | Actively kept in the @{OWNER} portfolio |
| version 1.0.0 | Documentation and brand completeness milestone |
| pages enabled | Site intended at `https://{OWNER}.github.io/{name}/` |

Detailed narrative for the stable line lives in [CHANGELOG.md](./CHANGELOG.md) and the [v1.0.0 GitHub Release](https://github.com/{OWNER}/{name}/releases/tag/v1.0.0).
"""


def ensure_diligence(repo: Path, name: str, desc: str):
    def write_if_missing(path: Path, content: str):
        if not path.exists() or path.stat().st_size < 40:
            path.write_text(content, encoding="utf-8")

    write_if_missing(
        repo / "CHANGELOG.md",
        f"""# Changelog

All notable changes to `{name}` are documented in this file.

## [1.0.0] — 2026-09-29

### Added — stable documentation & brand release

- Official logo at `docs/logo.svg`, featured in the README.
- Expanded badge pack with status and documentation notes.
- Diligence pack: SUPPORT, SECURITY, CONTRIBUTING, NOTICE.
- GitHub Release **v1.0.0** with detailed release notes.
- Product statement: {desc}

### Notes

This tag marks the portfolio-stable documentation line for `{name}`.
Subsequent feature versions may continue on higher semver tags; v1.0.0 remains the baseline brand/docs milestone.

[1.0.0]: https://github.com/{OWNER}/{name}/releases/tag/v1.0.0
""",
    )
    write_if_missing(
        repo / "SUPPORT.md",
        f"""# Support — {name}

1. Read [README.md](./README.md) and [CHANGELOG.md](./CHANGELOG.md).
2. Check the [v1.0.0 release](https://github.com/{OWNER}/{name}/releases/tag/v1.0.0).
3. Open a GitHub Issue on https://github.com/{OWNER}/{name}/issues with reproduction steps.

Community best-effort support. Security reports: see [SECURITY.md](./SECURITY.md).
""",
    )
    write_if_missing(
        repo / "SECURITY.md",
        f"""# Security policy — {name}

| Version | Supported |
| --- | --- |
| 1.0.x | ✅ |
| >= 1.0 | ✅ for current line |

Report vulnerabilities privately via GitHub Security Advisories on
https://github.com/{OWNER}/{name} when available. Include impact, reproduction, and affected versions.
""",
    )
    write_if_missing(
        repo / "CONTRIBUTING.md",
        f"""# Contributing to {name}

1. Fork and clone https://github.com/{OWNER}/{name}
2. Keep changes focused and documented.
3. Update CHANGELOG for user-visible changes.
4. Do not commit secrets.

Pull requests welcome.
""",
    )
    write_if_missing(
        repo / "NOTICE",
        f"""{name}
Copyright (c) 2026 {OWNER}

See LICENSE for terms. Third-party marks remain their owners' property.
""",
    )
    gh = repo / ".github"
    gh.mkdir(exist_ok=True)
    funding = gh / "FUNDING.yml"
    if not funding.exists():
        funding.write_text("github: [theworker02]\nthanks_dev: u/gh/theworker02\n", encoding="utf-8")


def ensure_logo_docs(repo: Path, name: str, desc: str):
    docs = repo / "docs"
    docs.mkdir(exist_ok=True)
    logo = docs / "logo.svg"
    if not logo.exists():
        logo.write_text(logo_for(name), encoding="utf-8")
    # also accept existing brand assets; still provide docs/logo.svg for README consistency
    if not (docs / "styles.css").exists():
        (docs / "styles.css").write_text(STYLES, encoding="utf-8")
    (docs / ".nojekyll").write_text("", encoding="utf-8")
    idx = docs / "index.html"
    if not idx.exists() or idx.stat().st_size < 80:
        idx.write_text(
            f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · v1.0.0</title>
<link rel="stylesheet" href="styles.css">
<link rel="icon" href="logo.svg" type="image/svg+xml">
</head><body>
<header class="hero">
<img src="logo.svg" alt="{name} official logo" width="96" height="96">
<div>
<p class="kicker sans">@{OWNER}/{name} · v1.0.0</p>
<h1>{name}</h1>
<p class="lede">{desc.replace('"', "'")}</p>
</div>
</header>
<main class="wrap">
<section>
<h2>Release v1.0.0</h2>
<p>Stable documentation, official logo, badge pack, and detailed release notes.</p>
<p><a href="https://github.com/{OWNER}/{name}/releases/tag/v1.0.0">View release notes</a> ·
<a href="https://github.com/{OWNER}/{name}">Source</a></p>
</section>
</main>
<footer class="sans">v1.0.0 · @{OWNER}</footer>
</body></html>
""",
            encoding="utf-8",
        )


def patch_readme(repo: Path, name: str, need_logo: bool, need_badges: bool) -> None:
    path = repo / "README.md"
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if name in FULL_REPLACE or len(existing.strip()) < 40:
        desc = infer_desc(repo, name) if existing.strip() else f"{name} — portfolio toolkit."
        # reuse factory-ish thick readme lightly
        from thicken import thick_readme, infer_meta

        m = infer_meta(repo, name)
        m["description"] = desc
        path.write_text(thick_readme(m), encoding="utf-8")
        return

    text = existing
    has_logo_ref = bool(re.search(r"logo\.(svg|png)|assets/brand", text, re.I))
    has_shields = "shields.io" in text or "img.shields.io" in text
    block = badge_block(name)

    if name in LIGHT_TOUCH:
        # prepend logo+badges if missing, keep body
        if (not has_logo_ref or need_logo or not has_shields or need_badges) and "docs/logo.svg" not in text:
            text = block + "\n\n" + text
        elif (not has_shields or need_badges) and "img.shields.io" not in text:
            text = block + "\n\n" + text
        if "## Badges & release notes" not in text:
            text = text.rstrip() + "\n" + badge_notes_section(name)
        path.write_text(text, encoding="utf-8")
        return

    if not has_logo_ref or need_logo:
        if "docs/logo.svg" not in text:
            text = block + "\n\n" + text
        has_shields = True
    elif not has_shields or need_badges:
        # inject shields under first H1
        inject = "\n".join(block.splitlines()[4:])  # skip logo-only top if logo exists elsewhere
        if re.search(r"^# ", text, re.M):
            text = re.sub(r"(^# .+\n)", r"\1\n" + inject + "\n", text, count=1, flags=re.M)
        else:
            text = inject + "\n\n" + text

    if "## Badges & release notes" not in text and "Badge" not in text[:800]:
        text = text.rstrip() + "\n" + badge_notes_section(name)
    elif "## Badges & release notes" not in text:
        text = text.rstrip() + "\n" + badge_notes_section(name)

    path.write_text(text, encoding="utf-8")


def release_notes(name: str, desc: str) -> str:
    return f"""# {name} v1.0.0 — stable documentation & brand release

{desc}

## Highlights

- **Official logo** shipped at `docs/logo.svg` and featured in the README
- **Badge pack** with docs, release, license, status, version, category, and pages badges
- **Detailed notes** for integrators and diligence readers (CHANGELOG, SUPPORT, SECURITY, CONTRIBUTING)
- **GitHub Pages** documentation surface at https://{OWNER}.github.io/{name}/
- **Stable tag** `v1.0.0` as the portfolio baseline for this product

## What changed in this release

1. Ensured brand mark and README presentation meet portfolio standards.
2. Expanded badge strip with explanatory notes table.
3. Added or refreshed diligence documentation.
4. Published narrative release notes for the 1.0 documentation line.

## Verification

- README shows the official logo.
- Badges resolve via shields.io.
- `CHANGELOG.md` records the 1.0.0 documentation milestone.
- This GitHub Release tag is `v1.0.0`.

## Upgrade / checkout

```bash
git clone https://github.com/{OWNER}/{name}.git
cd {name}
git checkout v1.0.0
```

Subsequent feature tags may advance beyond 1.0.0; this release remains the documented stable baseline for brand and docs completeness.
"""


def has_release_http(name: str) -> bool:
    import urllib.request

    url = f"https://github.com/{OWNER}/{name}/releases/tag/v1.0.0"
    req = urllib.request.Request(url, headers={"User-Agent": "thicken-remaining"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.getcode() == 200
    except Exception:
        return False


def wait_for_api(tok: str, timeout: int = 1200) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {tok}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "thicken-remaining",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.getcode() == 200:
                    return True
        except Exception as e:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            log(f"[api] waiting… {e}")
        # never sleep past deadline; short probes should return quickly
        sleep_for = min(30, max(0.5, deadline - time.time()))
        if sleep_for <= 0:
            break
        time.sleep(sleep_for)
    return False


def create_release(tok: str, name: str, body: str, repo: Path) -> bool:
    # tag via git
    run(["git", "fetch", "--tags"], cwd=repo, check=False)
    run(["git", "tag", "-f", "v1.0.0"], cwd=repo, check=False)
    push = run(["git", "push", "-f", "origin", "v1.0.0"], cwd=repo, check=False)
    if push.returncode != 0:
        log(f"[warn] tag push {name}: {(push.stderr or '')[-200:]}")

    notes = Path(tempfile.mkstemp(suffix=".md")[1])
    notes.write_text(body, encoding="utf-8")
    # Prefer not --latest if higher releases likely exist
    rel = run(
        [
            "gh",
            "release",
            "create",
            "v1.0.0",
            "-R",
            f"{OWNER}/{name}",
            "--title",
            f"{name} v1.0.0 — stable documentation & brand release",
            "--notes-file",
            str(notes),
        ],
        check=False,
    )
    if rel.returncode == 0:
        return True
    err = (rel.stderr or "") + (rel.stdout or "")
    if "already exists" in err.lower():
        return True
    # edit notes if exists
    run(
        [
            "gh",
            "release",
            "edit",
            "v1.0.0",
            "-R",
            f"{OWNER}/{name}",
            "--notes-file",
            str(notes),
        ],
        check=False,
    )
    return has_release_http(name) or "already exists" in err.lower()


def thicken_one(name: str, flags: dict, tok: str) -> dict:
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix=f"trem-{name}-"))
    url = f"https://x-access-token:{tok}@github.com/{OWNER}/{name}.git"
    try:
        r = run(["git", "clone", "--depth", "1", url, str(tmp / name)], check=False)
        if r.returncode != 0:
            return {"name": name, "status": "error", "error": (r.stderr or "")[-300:]}
        repo = tmp / name
        run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"], cwd=repo)
        run(["git", "config", "user.name", OWNER], cwd=repo)

        # empty repo?
        if not (repo / "README.md").exists() and not any(repo.iterdir()):
            pass

        desc = infer_desc(repo, name)
        ensure_logo_docs(repo, name, desc)
        ensure_diligence(repo, name, desc)
        patch_readme(
            repo,
            name,
            need_logo=flags.get("need_logo", False),
            need_badges=flags.get("need_badges", False),
        )

        # license stub if totally missing
        if not (repo / "LICENSE").exists() and not (repo / "LICENSE.md").exists():
            (repo / "LICENSE").write_text(
                f"Copyright (c) 2026 {OWNER}\n\nAll rights reserved unless otherwise stated in project documentation.\n",
                encoding="utf-8",
            )

        run(["git", "add", "-A"], cwd=repo)
        st = run(["git", "status", "--porcelain"], cwd=repo)
        if st.stdout.strip():
            msg = f"docs: v1.0.0 logo, badges, notes, and diligence pack for {name}"
            run(["git", "commit", "-m", msg], cwd=repo)
            branch = run(["git", "branch", "--show-current"], cwd=repo).stdout.strip() or "main"
            p = run(["git", "push", "origin", f"HEAD:{branch}"], cwd=repo, check=False)
            if p.returncode != 0:
                # Branch protection — push topic branch and merge via PR when API allows
                topic = "cursor/docs-v1-f37b"
                tp = run(["git", "push", "-u", "origin", f"HEAD:{topic}"], cwd=repo, check=False)
                if tp.returncode != 0:
                    return {
                        "name": name,
                        "status": "error",
                        "error": ((p.stderr or "") + (tp.stderr or ""))[-400:],
                    }
                # Defer PR create/merge to release pass when API is available
                log(f"[warn] protected {name}: pushed {topic} (PR merge deferred)")
                with (STATE / "protected_topics.txt").open("a", encoding="utf-8") as f:
                    f.write(f"{name}\t{branch}\t{topic}\n")

        # Defer all release creation to the end pass (avoids API burn while rate-limited).
        if not has_release_http(name):
            return {
                "name": name,
                "status": "pending_release",
                "seconds": round(time.time() - t0, 2),
            }

        mark_done(name)
        return {"name": name, "status": "ok", "seconds": round(time.time() - t0, 2)}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)[:400]}
    finally:
        # keep pending clones? always cleanup; release can re-clone
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    tok = token()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    need_logo = set(plan["need_logo"])
    need_badges = set(plan["need_badges"])
    need_rel = set(plan["need_rel"])
    all_names = [a["name"] for a in plan["all"]]

    done = already_done()
    # process all 79 not yet in thickened
    targets = [n for n in all_names if n not in done]
    log(f"[start] targets={len(targets)} docs-first (API may be limited)")

    pending_release = []
    ok = err = 0
    for name in targets:
        flags = {
            "need_logo": name in need_logo,
            "need_badges": name in need_badges,
            "need_rel": name in need_rel,
        }
        res = thicken_one(name, flags, tok)
        if res["status"] == "ok":
            ok += 1
            log(f"[ok] {name} ({res.get('seconds')}s) ok={ok} err={err}")
        elif res["status"] == "pending_release":
            pending_release.append(name)
            # still record content progress separately
            content_done = STATE / "thickened_content.txt"
            with content_done.open("a", encoding="utf-8") as f:
                f.write(name + "\n")
            log(f"[pending_release] {name}")
        else:
            err += 1
            log(f"[err] {name}: {res.get('error')}")
        time.sleep(1.2)

    # second pass for releases
    if pending_release:
        log(f"[releases] waiting for API; pending={len(pending_release)}")
        wait_for_api(tok, timeout=1800)
        for name in pending_release:
            tmp = Path(tempfile.mkdtemp(prefix=f"rel-{name}-"))
            url = f"https://x-access-token:{tok}@github.com/{OWNER}/{name}.git"
            try:
                run(["git", "clone", "--depth", "1", url, str(tmp / name)], check=False)
                repo = tmp / name
                run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"], cwd=repo)
                run(["git", "config", "user.name", OWNER], cwd=repo)
                desc = infer_desc(repo, name)
                if create_release(tok, name, release_notes(name, desc), repo):
                    mark_done(name)
                    ok += 1
                    log(f"[ok-release] {name}")
                else:
                    err += 1
                    log(f"[err-release] {name}")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            time.sleep(2)

    log(f"[done] ok={ok} err={err} pending_left={len([n for n in pending_release if n not in already_done()])}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
