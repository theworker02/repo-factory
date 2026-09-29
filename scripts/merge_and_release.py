#!/usr/bin/env python3
"""Merge cursor/docs-v1-f37b branches and create v1.0.0 releases for pending repos."""
from __future__ import annotations
import json, os, re, shutil, subprocess, tempfile, time
from pathlib import Path
import thicken_remaining as tr

OWNER = "theworker02"
STATE = Path(__file__).resolve().parent / "state"
TOPIC = "cursor/docs-v1-f37b"

def run(cmd, check=False):
    return subprocess.run(cmd, check=check, text=True, capture_output=True)

def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)
    with (STATE / "merge_release.log").open("a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

def main():
    tok = tr.token()
    log("[wait] for API")
    if not tr.wait_for_api(tok, timeout=2400):
        log("[fail] API never recovered")
        return 1
    log("[api] ready")

    protected = []
    p = Path("/tmp/protected_repos.txt")
    if p.exists():
        protected = [x.strip() for x in p.read_text().splitlines() if x.strip()]
    pending = []
    for path in (STATE / "thickened_content.txt", Path("/tmp/pending_rel.txt")):
        if path.exists():
            pending.extend(x.strip() for x in path.read_text().splitlines() if x.strip())
    # also any from plan need_rel
    plan = json.loads(Path("/tmp/work_plan.json").read_text())
    pending.extend(plan.get("need_rel", []))
    pending = sorted(set(pending))
    protected = sorted(set(protected))
    log(f"[plan] merge={len(protected)} release_candidates={len(pending)}")

    for name in protected:
        # create PR if needed and merge
        pr_list = run(["gh", "pr", "list", "-R", f"{OWNER}/{name}", "--head", TOPIC, "--json", "number,state"])
        num = None
        if pr_list.returncode == 0 and pr_list.stdout.strip():
            try:
                arr = json.loads(pr_list.stdout)
                if arr:
                    num = arr[0]["number"]
            except Exception:
                pass
        if num is None:
            # detect base
            base = "main"
            meta = run(["gh", "repo", "view", f"{OWNER}/{name}", "--json", "defaultBranchRef"])
            if meta.returncode == 0:
                try:
                    base = json.loads(meta.stdout)["defaultBranchRef"]["name"]
                except Exception:
                    pass
            cr = run([
                "gh", "pr", "create", "-R", f"{OWNER}/{name}",
                "--base", base, "--head", TOPIC,
                "--title", f"docs: v1.0.0 logo, badges, notes for {name}",
                "--body", "Official logo, badge pack, diligence docs, and v1.0.0 release prep.",
            ])
            if cr.returncode == 0:
                m = re.search(r"/pull/(\d+)", cr.stdout)
                num = int(m.group(1)) if m else None
            else:
                log(f"[warn] pr create {name}: {(cr.stderr or cr.stdout)[-200:]}")
        if num:
            mg = run(["gh", "pr", "merge", str(num), "-R", f"{OWNER}/{name}", "--squash", "--admin"])
            if mg.returncode != 0:
                mg = run(["gh", "pr", "merge", str(num), "-R", f"{OWNER}/{name}", "--squash"])
            log(f"[merge] {name}#{num} rc={mg.returncode}")
        time.sleep(1)

    # releases for anything lacking v1.0.0
    ok = err = 0
    for name in pending:
        if tr.has_release_http(name):
            tr.mark_done(name)
            ok += 1
            log(f"[skip-has] {name}")
            continue
        tmp = Path(tempfile.mkdtemp(prefix=f"rel-{name}-"))
        url = f"https://x-access-token:{tok}@github.com/{OWNER}/{name}.git"
        try:
            c = run(["git", "clone", "--depth", "1", url, str(tmp / name)])
            if c.returncode != 0:
                err += 1
                log(f"[err-clone] {name}")
                continue
            repo = tmp / name
            run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"],)
            subprocess.run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"], cwd=repo, check=False, capture_output=True)
            subprocess.run(["git", "config", "user.name", OWNER], cwd=repo, check=False, capture_output=True)
            desc = tr.infer_desc(repo, name)
            if tr.create_release(tok, name, tr.release_notes(name, desc), repo):
                tr.mark_done(name)
                ok += 1
                log(f"[ok-release] {name}")
            else:
                err += 1
                log(f"[err-release] {name}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        time.sleep(1.5)

    # Also ensure need_logo/badges repos that already had releases are marked done
    for a in plan["all"]:
        n = a["name"]
        if n not in tr.already_done() and tr.has_release_http(n):
            tr.mark_done(n)
            log(f"[mark] {n}")

    log(f"[done] releases_ok={ok} err={err}")
    return 0 if err == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
