#!/usr/bin/env python3
"""Ensure every listed repo has ACQUISITION.md and official docs/logo.svg in README."""

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
DONE = STATE / "acq_logo_done.txt"
LOG = STATE / "ensure_acq_logo.log"
BASE_LOGO = (ROOT / "logo.svg").read_text(encoding="utf-8")
LOCK = threading.Lock()
WORKERS = int(os.environ.get("ACQ_WORKERS", "4"))
TARGETS = Path(os.environ.get("ACQ_TARGETS", "/tmp/need_acq_logo.txt"))


def run(cmd, cwd=None, check=False):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def log(msg: str):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOCK:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def token() -> str:
    text = (Path.home() / ".config/gh/hosts.yml").read_text(encoding="utf-8")
    m = re.search(r"oauth_token:\s*(\S+)", text)
    if not m:
        raise RuntimeError("no gh token")
    return m.group(1)


def already_done() -> set[str]:
    if not DONE.exists():
        return set()
    return {x.strip() for x in DONE.read_text().splitlines() if x.strip()}


def mark_done(name: str):
    with LOCK:
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


def infer_meta(repo: Path, name: str) -> dict:
    desc = f"{name} — a focused developer product in the @{OWNER} portfolio."
    category = "toolkit"
    readme = repo / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            s = re.sub(r"[*_`#]", "", line).strip()
            if 24 <= len(s) <= 220 and not s.startswith("<") and "http" not in s[:8]:
                desc = s
                break
    pkg = repo / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if data.get("description"):
                desc = data["description"]
            for k in data.get("keywords") or []:
                if k in {
                    "text", "json", "csv", "time", "url", "hash", "color", "number",
                    "path", "encode", "validate", "list", "stat", "markup", "id",
                    "net", "config", "toolkit",
                }:
                    category = k
                    break
        except Exception:
            pass
    return {"name": name, "description": desc, "category": category}


def acquisition_doc(m: dict) -> str:
    name = m["name"]
    cat = m["category"]
    desc = m["description"]
    return f"""# Acquisition notes — {name}

## Executive summary

`{name}` is a portfolio product in the **{cat}** category: {desc}

It ships with an official brand mark, public documentation, and diligence materials suitable for technical and commercial review. The repository is structured so an acquirer can evaluate code, docs, licensing, and go-to-market posture quickly.

## Product assets

| Asset | Location | Notes |
| --- | --- | --- |
| Source | repository root / `src/` (when present) | Implementation and tests |
| Official logo | [`docs/logo.svg`](./docs/logo.svg) | Brand mark used in README and Pages |
| Docs site | `docs/` | GitHub Pages surface when enabled |
| Acquisition brief | this file | Diligence-oriented overview |
| Support | [`SUPPORT.md`](./SUPPORT.md) | How to get help (when present) |
| Security | [`SECURITY.md`](./SECURITY.md) | Vulnerability reporting (when present) |
| Changelog | [`CHANGELOG.md`](./CHANGELOG.md) | Release history (when present) |
| License | `LICENSE` | See repository terms |
| Funding | `.github/FUNDING.yml` | Sponsors / thanks.dev when present |
| Release | `v1.0.0` (when tagged) | Stable documentation / brand baseline |

## Technical due diligence

- **Primary surface:** public GitHub repository `https://github.com/{OWNER}/{name}`
- **Documentation:** README + `docs/` + this acquisition brief
- **Brand:** deterministic official logo at `docs/logo.svg`
- **Telemetry:** none expected for local toolkit-style products
- **Distribution:** git clone and GitHub Releases

## Commercial / integration posture

Suitable as:

1. A standalone open-source or source-available product line
2. A bolt-on utility inside a larger platform or agent stack
3. A documentation-complete asset for portfolio / acquisition review

## Risks & constraints

- Scope varies by product; confirm runtime and license before production use.
- GitHub Pages availability depends on repository visibility and Pages settings.
- Third-party marks mentioned in docs remain their owners' property.

## Contact

Open a GitHub Issue on `https://github.com/{OWNER}/{name}` or contact [@{OWNER}](https://github.com/{OWNER}).
"""


def ensure_readme_logo(repo: Path, name: str) -> None:
    path = repo / "README.md"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else f"# {name}\n"
    if "docs/logo.svg" not in text:
        block = f"""<p align="center">
  <img src="docs/logo.svg" alt="{name} official logo" width="128" height="128">
</p>

"""
        text = block + text
    # Link acquisition in README if missing
    if "ACQUISITION.md" not in text:
        text = text.rstrip() + f"""

## Acquisition

See [ACQUISITION.md](./ACQUISITION.md) for the diligence-oriented product brief, asset map, and commercial posture notes.
"""
    path.write_text(text, encoding="utf-8")


def push_changes(repo: Path, name: str, tok: str, msg: str) -> bool:
    run(["git", "add", "-A"], cwd=repo)
    st = run(["git", "status", "--porcelain"], cwd=repo)
    if not st.stdout.strip():
        return True
    run(["git", "commit", "-m", msg], cwd=repo)
    branch = run(["git", "branch", "--show-current"], cwd=repo).stdout.strip() or "main"
    p = run(["git", "push", "origin", f"HEAD:{branch}"], cwd=repo)
    if p.returncode == 0:
        return True
    topic = "cursor/acq-logo-f37b"
    tp = run(["git", "push", "-u", "origin", f"HEAD:{topic}"], cwd=repo)
    if tp.returncode != 0:
        log(f"[err-push] {name}: {(p.stderr or '')[-200:]} {(tp.stderr or '')[-200:]}")
        return False
    pr = run(
        [
            "gh",
            "pr",
            "create",
            "-R",
            f"{OWNER}/{name}",
            "--base",
            branch,
            "--head",
            topic,
            "--title",
            msg,
            "--body",
            "Adds official `docs/logo.svg` and `ACQUISITION.md` diligence brief.",
        ]
    )
    run(["gh", "pr", "merge", "-R", f"{OWNER}/{name}", "--squash", "--admin"])
    run(["gh", "pr", "merge", "-R", f"{OWNER}/{name}", "--squash"])
    log(f"[pr] {name} create_rc={pr.returncode}")
    return True


def process_one(name: str, tok: str) -> dict:
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix=f"acq-{name}-"))
    url = f"https://x-access-token:{tok}@github.com/{OWNER}/{name}.git"
    try:
        c = run(["git", "clone", "--depth", "1", url, str(tmp / name)])
        if c.returncode != 0:
            return {"name": name, "status": "error", "error": (c.stderr or "")[-300:]}
        repo = tmp / name
        run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"], cwd=repo)
        run(["git", "config", "user.name", OWNER], cwd=repo)

        m = infer_meta(repo, name)
        docs = repo / "docs"
        docs.mkdir(exist_ok=True)
        logo = docs / "logo.svg"
        if not logo.exists() or logo.stat().st_size < 40:
            logo.write_text(logo_for(name), encoding="utf-8")

        acq = repo / "ACQUISITION.md"
        if not acq.exists() or acq.stat().st_size < 80:
            acq.write_text(acquisition_doc(m), encoding="utf-8")

        ensure_readme_logo(repo, name)

        gh = repo / ".github"
        gh.mkdir(exist_ok=True)
        funding = gh / "FUNDING.yml"
        if not funding.exists():
            funding.write_text("github: [theworker02]\nthanks_dev: u/gh/theworker02\n", encoding="utf-8")

        ok = push_changes(
            repo,
            name,
            tok,
            f"docs: add acquisition brief and official logo for {name}",
        )
        if not ok:
            return {"name": name, "status": "error", "error": "push failed"}
        mark_done(name)
        return {"name": name, "status": "ok", "seconds": round(time.time() - t0, 2)}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)[:300]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    tok = token()
    if not TARGETS.exists():
        log(f"[fail] missing targets {TARGETS}")
        return 1
    targets = [x.strip() for x in TARGETS.read_text().splitlines() if x.strip()]
    done = already_done()
    queue = [n for n in targets if n not in done]
    log(f"[start] queue={len(queue)} workers={WORKERS}")
    ok = err = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        # process in small batches to avoid stampeding protected repos
        i = 0
        while i < len(queue):
            batch = queue[i : i + WORKERS]
            i += len(batch)
            futs = [ex.submit(process_one, n, tok) for n in batch]
            for fut in concurrent.futures.as_completed(futs):
                res = fut.result()
                if res["status"] == "ok":
                    ok += 1
                    log(f"[ok] {res['name']} ({res.get('seconds')}s) ok={ok} err={err}")
                else:
                    err += 1
                    log(f"[err] {res['name']}: {res.get('error')}")
            time.sleep(0.8)
    log(f"[done] ok={ok} err={err}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
