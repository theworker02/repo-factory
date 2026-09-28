#!/usr/bin/env python3
"""Enable /docs GitHub Pages for existing public non-fork repos that are missing a live site."""

from __future__ import annotations

import base64
import json
import subprocess
import time
import urllib.request
from pathlib import Path

OWNER = "theworker02"
STYLES = Path(__file__).resolve().parent.joinpath("styles.css").read_text(encoding="utf-8")
LOGO = Path(__file__).resolve().parent.joinpath("logo.svg").read_text(encoding="utf-8")


def run(cmd, check=True):
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def api(path, method="GET", fields=None):
    cmd = ["gh", "api", "-X", method, path]
    if fields:
        for k, v in fields.items():
            cmd += ["-f", f"{k}={v}"]
    r = run(cmd, check=False)
    if r.returncode != 0:
        return {"_error": (r.stderr or r.stdout)[-400:]}
    return json.loads(r.stdout) if r.stdout.strip() else {}


def http_ok(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pages-fix"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def put_file(repo: str, path: str, content: str, message: str):
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    # get sha if exists
    existing = api(f"repos/{OWNER}/{repo}/contents/{path}")
    cmd = [
        "gh",
        "api",
        "-X",
        "PUT",
        f"repos/{OWNER}/{repo}/contents/{path}",
        "-f",
        f"message={message}",
        "-f",
        f"content={b64}",
        "-f",
        "branch=main",
    ]
    if isinstance(existing, dict) and existing.get("sha"):
        cmd += ["-f", f"sha={existing['sha']}"]
    r = run(cmd, check=False)
    return r.returncode == 0, (r.stderr or r.stdout)[-300:]


def ensure_docs_site(repo: str, description: str) -> bool:
    contents = api(f"repos/{OWNER}/{repo}/contents/")
    names = [x["name"] for x in contents] if isinstance(contents, list) else []
    has_docs_index = False
    if "docs" in names:
        docs = api(f"repos/{OWNER}/{repo}/contents/docs")
        if isinstance(docs, list):
            has_docs_index = any(x.get("name") == "index.html" for x in docs)
    if not has_docs_index:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{repo}</title>
  <meta name="description" content="{description.replace('"', "'")}">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <nav class="nav sans">
    <a class="brand-lockup" href="index.html"><img src="logo.svg" alt=""> {repo}</a>
    <div class="links"><a href="https://github.com/{OWNER}/{repo}">GitHub</a></div>
  </nav>
  <header class="hero">
    <img src="logo.svg" alt="">
    <div>
      <p class="kicker sans">@{OWNER}/{repo}</p>
      <h1>{repo}</h1>
      <p class="lede">{description}</p>
    </div>
  </header>
  <div class="wrap">
    <section>
      <h2>Repository</h2>
      <p>Product documentation site for <a href="https://github.com/{OWNER}/{repo}"><code>{OWNER}/{repo}</code></a>.</p>
      <pre><code>git clone https://github.com/{OWNER}/{repo}.git</code></pre>
    </section>
  </div>
  <footer class="sans">MIT © 2026 {OWNER} · <a href="https://github.com/{OWNER}/{repo}">GitHub</a></footer>
</body>
</html>
"""
        ok1, e1 = put_file(repo, "docs/index.html", html, f"Add GitHub Pages site for {repo}")
        ok2, e2 = put_file(repo, "docs/styles.css", STYLES, f"Add Pages styles for {repo}")
        ok3, e3 = put_file(repo, "docs/logo.svg", LOGO, f"Add Pages logo for {repo}")
        put_file(repo, "docs/.nojekyll", "", f"Disable Jekyll for {repo}")
        if not (ok1 and ok2 and ok3):
            print(f"[docs-fail] {repo}: {e1} {e2} {e3}", flush=True)
            return False
    # enable pages
    api(f"repos/{OWNER}/{repo}/pages", method="DELETE")
    res = api(
        f"repos/{OWNER}/{repo}/pages",
        method="POST",
        fields={
            "build_type": "legacy",
            "source[branch]": "main",
            "source[path]": "/docs",
        },
    )
    if "_error" in res and "already exists" not in res["_error"]:
        res = api(
            f"repos/{OWNER}/{repo}/pages",
            method="PUT",
            fields={
                "build_type": "legacy",
                "source[branch]": "main",
                "source[path]": "/docs",
            },
        )
    run(
        [
            "gh",
            "repo",
            "edit",
            f"{OWNER}/{repo}",
            "--homepage",
            f"https://{OWNER}.github.io/{repo}/",
        ],
        check=False,
    )
    return "_error" not in res or "already" in res.get("_error", "").lower()


def main():
    repos = json.loads(
        run(
            [
                "gh",
                "api",
                "--paginate",
                f"/users/{OWNER}/repos?per_page=100&type=owner",
            ]
        ).stdout
    )
    # flatten paginate - gh --paginate concatenates JSON arrays incorrectly sometimes; handle both
    if isinstance(repos, dict):
        repos = [repos]
    # When paginating, gh may return concatenated arrays - use jq approach instead
    names = run(
        [
            "gh",
            "api",
            "--paginate",
            f"/users/{OWNER}/repos?per_page=100&type=owner",
            "--jq",
            ".[] | select(.fork==false and .private==false) | [.name,.description] | @tsv",
        ]
    ).stdout.splitlines()

    fixed = 0
    skipped = 0
    for line in names:
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        name = parts[0]
        desc = parts[1] if len(parts) > 1 else name
        if name == OWNER:
            continue
        url = f"https://{OWNER}.github.io/{name}/"
        if http_ok(url):
            skipped += 1
            continue
        print(f"[fix] {name}", flush=True)
        if ensure_docs_site(name, desc or name):
            fixed += 1
            print(f"[ok] {name} -> {url}", flush=True)
        else:
            print(f"[err] {name}", flush=True)
        time.sleep(0.4)
    print(f"[done] fixed={fixed} already_ok={skipped}", flush=True)


if __name__ == "__main__":
    main()
