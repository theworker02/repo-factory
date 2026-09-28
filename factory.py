#!/usr/bin/env python3
"""High-throughput factory: unique useful micro-tools → GitHub + Pages.

Creates public repos under theworker02 until TARGET public repos exist.
Each repo ships working JS (library + CLI), polished docs site, LICENSE, FUNDING.
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

OWNER = "theworker02"
TARGET = int(os.environ.get("PORTFOLIO_TARGET", "4000"))
WORKERS = int(os.environ.get("PORTFOLIO_WORKERS", "2"))
ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
STYLES = (ROOT / "styles.css").read_text(encoding="utf-8")
LOGO = (ROOT / "logo.svg").read_text(encoding="utf-8")
LOCK = threading.Lock()
PROGRESS = STATE / "progress.jsonl"
CREATED = STATE / "created_names.txt"
RATE_LIMIT_HITS = 0
RATE_LIMIT_LOCK = threading.Lock()


STATE.mkdir(parents=True, exist_ok=True)

# --- vocabulary for unique, pronounceable tool names ---
VERBS = [
    "audit", "bake", "bind", "bolt", "boost", "brace", "brew", "carve", "cast",
    "check", "clamp", "clean", "clip", "clock", "coil", "count", "craft",
    "crush", "deck", "delta", "diff", "drill", "edge", "etch", "fetch",
    "field", "fill", "filter", "fix", "forge", "frame", "fuse", "gate",
    "gauge", "grind", "guard", "hatch", "heap", "hinge", "index", "join",
    "keep", "knit", "latch", "lint", "lift", "map", "mark", "match", "meld",
    "mesh", "mint", "mold", "norm", "pack", "parse", "peek", "pick", "ping",
    "pipe", "plan", "plot", "plug", "press", "probe", "proof", "prune",
    "pulse", "punch", "purge", "push", "rank", "read", "reef", "render",
    "rift", "ring", "roll", "route", "scan", "scoop", "score", "seal",
    "shape", "shear", "shift", "ship", "sift", "sign", "sink", "slice",
    "slot", "sort", "span", "spark", "split", "stack", "stamp", "steer",
    "stitch", "strip", "sync", "tag", "tape", "tally", "tap", "tilt",
    "trace", "trim", "tune", "vault", "vet", "warp", "weave", "weld",
    "wrap", "yard", "zip", "zone",
]
NOUNS = [
    "argv", "atom", "beam", "blob", "bolt", "byte", "case", "cell", "chord",
    "cidr", "clip", "code", "cron", "csv", "cue", "data", "diff", "dock",
    "edge", "env", "epoch", "etag", "file", "flag", "flux", "font", "form",
    "frame", "glob", "graph", "grid", "hash", "head", "heap", "hex", "hive",
    "html", "http", "icon", "idem", "ipv4", "ipv6", "json", "jwt", "key",
    "kit", "lane", "leaf", "line", "link", "list", "log", "map", "mark",
    "mask", "mesh", "meta", "mime", "net", "node", "note", "null", "pack",
    "page", "path", "port", "prob", "proc", "prot", "query", "queue", "raft",
    "range", "rate", "ref", "regex", "repo", "rest", "row", "rss", "rule",
    "schema", "scope", "semver", "set", "slug", "span", "spec", "sql",
    "stack", "stat", "stream", "svg", "table", "tag", "text", "time",
    "token", "toml", "trace", "tree", "type", "unit", "uri", "url", "uuid",
    "wasm", "xml", "yaml", "zone",
]
SUFFIXES = [
    "", "kit", "lab", "cli", "ops", "fx", "io", "hq", "box", "hub", "pro",
    "lite", "core", "tools", "craft", "works", "smith", "yard",
]
CATEGORIES = [
    "text", "json", "csv", "time", "url", "hash", "color", "number", "path",
    "encode", "validate", "list", "stat", "markup", "id", "net", "config",
]


def run(cmd, cwd=None, check=True, input_text=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        input=input_text,
        capture_output=True,
    )


def existing_names() -> set[str]:
    names: set[str] = set()
    # Authenticated listing covers private + public owned repos.
    proc = run(
        [
            "gh",
            "api",
            "--paginate",
            "/user/repos?per_page=100&affiliation=owner",
            "--jq",
            ".[].name",
        ]
    )
    for line in proc.stdout.splitlines():
        n = line.strip()
        if n:
            names.add(n.lower())
    if CREATED.exists():
        for line in CREATED.read_text().splitlines():
            if line.strip():
                names.add(line.strip().lower())
    return names


def public_count() -> int:
    out = run(["gh", "api", f"/users/{OWNER}", "--jq", ".public_repos"])
    return int(out.stdout.strip())


def slugify_parts(verb: str, noun: str, suffix: str) -> str:
    base = f"{verb}{noun}" if not verb.endswith(noun[:2]) else f"{verb}-{noun}"
    if suffix:
        name = f"{base}{suffix}" if len(base) + len(suffix) <= 20 else f"{base}-{suffix}"
    else:
        name = base
    name = re.sub(r"[^a-z0-9-]", "", name.lower())
    name = re.sub(r"-{2,}", "-", name).strip("-")
    if len(name) < 3:
        name = f"{name}kit"
    if len(name) > 40:
        name = name[:40].rstrip("-")
    if name[0].isdigit():
        name = f"tool-{name}"
    return name


def generate_catalog(needed: int, taken: set[str]) -> list[dict]:
    rng = random.Random(20260928)
    catalog: list[dict] = []
    seen = set(taken)
    reserved = {"test", "src", "docs", "main", "null", "undefined", "package", "node"}

    def add(name: str, verb: str, noun: str) -> bool:
        if len(catalog) >= needed:
            return False
        if name in seen or name in reserved or len(name) < 4:
            return False
        seen.add(name)
        cat = CATEGORIES[(len(catalog) + sum(map(ord, name))) % len(CATEGORIES)]
        catalog.append(make_spec(name, verb, noun, cat, rng))
        return True

    # Pass 1: unique verb+noun pairs (most interesting names)
    pairs = [(v, n) for v in VERBS for n in NOUNS]
    rng.shuffle(pairs)
    for verb, noun in pairs:
        add(slugify_parts(verb, noun, ""), verb, noun)
        if len(catalog) >= needed:
            return catalog

    # Pass 2: light suffixes only when needed
    for verb, noun in pairs:
        for suffix in ("kit", "cli", "ops", "lab", "fx", "io", "hub", "core", "tools"):
            add(slugify_parts(verb, noun, suffix), verb, noun)
            if len(catalog) >= needed:
                return catalog

    # Pass 3: salted fallbacks
    i = 0
    while len(catalog) < needed:
        i += 1
        verb = rng.choice(VERBS)
        noun = rng.choice(NOUNS)
        name = slugify_parts(verb, noun, f"v{i}")
        if name in seen:
            name = f"{verb}-{noun}-{i}"
        add(name, verb, noun)
    return catalog


def make_spec(name: str, verb: str, noun: str, category: str, rng: random.Random) -> dict:
    title = name
    tagline = {
        "text": f"{verb.title()} and reshape {noun} text streams with deterministic transforms.",
        "json": f"{verb.title()} structured JSON {noun} payloads without a heavyweight toolkit.",
        "csv": f"{verb.title()} CSV/TSV {noun} tables for quick inspection and cleanup.",
        "time": f"{verb.title()} timestamps and {noun} durations for scripts and CI receipts.",
        "url": f"{verb.title()} URLs and {noun} query parts with stable normalization.",
        "hash": f"{verb.title()} digests and {noun} fingerprints for local integrity checks.",
        "color": f"{verb.title()} color {noun} values and contrast-safe presentation helpers.",
        "number": f"{verb.title()} numeric {noun} values, ranges, and human-readable units.",
        "path": f"{verb.title()} filesystem {noun} paths across POSIX and Windows conventions.",
        "encode": f"{verb.title()} encode/decode helpers for {noun} payloads in pipelines.",
        "validate": f"{verb.title()} validation gates for {noun} inputs before they hit prod.",
        "list": f"{verb.title()} list/{noun} set operations for shell-friendly data wrangling.",
        "stat": f"{verb.title()} lightweight {noun} statistics from stdin samples.",
        "markup": f"{verb.title()} HTML/Markdown {noun} fragments safely for docs pipelines.",
        "id": f"{verb.title()} identifiers and {noun} tokens for idempotent workflows.",
        "net": f"{verb.title()} host/{noun} network string helpers for config audits.",
        "config": f"{verb.title()} config/{noun} key checks for twelve-factor services.",
    }[category]
    return {
        "name": name,
        "verb": verb,
        "noun": noun,
        "category": category,
        "version": "1.0.0",
        "description": tagline,
        "keywords": [verb, noun, category, "cli", "toolkit"],
    }


def js_impl(spec: dict) -> str:
    cat = spec["category"]
    preamble = r'''
function readInput(fallback) {
  if (fallback != null && String(fallback).length) return String(fallback);
  if (process.stdin && process.stdin.isTTY) return "";
  try {
    const fs = require("fs");
    if (typeof fs.readFileSync === "function") {
      // Non-blocking when no piped data: use readFileSync only if fd 0 has size or isn't a TTY.
      return fs.readFileSync(0, "utf8");
    }
  } catch (_) {}
  return "";
}
'''
    bodies = {
        "text": r'''
function transform(input, mode = "squash") {
  const s = String(input ?? "");
  switch (mode) {
    case "squash": return s.replace(/\s+/g, " ").trim();
    case "lines": return s.split(/\r?\n/).map(l => l.trimEnd()).join("\n");
    case "reverse": return s.split("").reverse().join("");
    case "words": return s.trim().split(/\s+/).filter(Boolean);
    default: return s;
  }
}
function run(argv) {
  const mode = argv[0] && !argv[0].startsWith("-") ? argv[0] : "squash";
  const rest = argv[0] === mode ? argv.slice(1) : argv;
  const input = rest.join(" ") || "sample text";
  const out = transform(input, mode);
  return typeof out === "string" ? out : JSON.stringify(out, null, 2);
}
''',
        "json": r'''
function pick(obj, path) {
  return String(path || "").split(".").filter(Boolean).reduce((a, k) => (a == null ? undefined : a[k]), obj);
}
function flatten(obj, prefix = "", out = {}) {
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    for (const [k, v] of Object.entries(obj)) flatten(v, prefix ? prefix + "." + k : k, out);
  } else out[prefix || "value"] = obj;
  return out;
}
function run(argv) {
  const mode = argv[0] || "flatten";
  const raw = argv[1] || '{"a":{"b":1},"c":2}';
  const data = JSON.parse(raw);
  if (mode === "pick") return JSON.stringify(pick(data, argv[2] || "a.b"), null, 2);
  return JSON.stringify(flatten(data), null, 2);
}
''',
        "csv": r'''
function parseCsv(text, sep = ",") {
  return String(text).replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n")
    .filter(l => l.length).map(line => {
      const cells = []; let cur = ""; let q = false;
      for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (c === '"') { q = !q; continue; }
        if (c === sep && !q) { cells.push(cur); cur = ""; continue; }
        cur += c;
      }
      cells.push(cur); return cells;
    });
}
function run(argv) {
  const sep = argv[0] === "--tsv" ? "\t" : ",";
  const sample = argv[0] === "--tsv" ? argv.slice(1).join(" ") : argv.join(" ");
  const text = sample || "a,b,c\n1,2,3\n4,5,6";
  const rows = parseCsv(text, sep);
  return JSON.stringify({ rows: rows.length, cols: rows[0]?.length || 0, sample: rows.slice(0, 5) }, null, 2);
}
''',
        "time": r'''
function parseDuration(s) {
  const m = String(s).trim().match(/^(\d+(?:\.\d+)?)(ms|s|m|h|d)?$/i);
  if (!m) throw new Error("bad duration: " + s);
  const n = Number(m[1]);
  const u = (m[2] || "s").toLowerCase();
  const mul = { ms: 1, s: 1000, m: 60000, h: 3600000, d: 86400000 }[u];
  return n * mul;
}
function formatDuration(ms) {
  if (ms < 1000) return ms + "ms";
  if (ms < 60000) return (ms / 1000) + "s";
  if (ms < 3600000) return (ms / 60000) + "m";
  return (ms / 3600000) + "h";
}
function run(argv) {
  const mode = argv[0] || "now";
  if (mode === "now") return new Date().toISOString();
  if (mode === "parse") return String(parseDuration(argv[1] || "1s"));
  if (mode === "format") return formatDuration(Number(argv[1] || 0));
  return new Date().toISOString();
}
''',
        "url": r'''
function normalizeUrl(input) {
  const u = new URL(String(input));
  u.hash = "";
  u.hostname = u.hostname.toLowerCase();
  if ((u.protocol === "http:" && u.port === "80") || (u.protocol === "https:" && u.port === "443")) u.port = "";
  const entries = [...u.searchParams.entries()].sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]));
  u.search = "";
  for (const [k, v] of entries) u.searchParams.append(k, v);
  return u.toString();
}
function run(argv) {
  return normalizeUrl(argv[0] || "https://Example.com:443/a?b=1&a=2");
}
''',
        "hash": r'''
const crypto = require("crypto");
function digest(text, algo = "sha256") {
  return crypto.createHash(algo).update(String(text)).digest("hex");
}
function run(argv) {
  const algo = argv[0] && ["sha256","sha1","md5","sha512"].includes(argv[0]) ? argv[0] : "sha256";
  const text = (algo === argv[0] ? argv.slice(1) : argv).join(" ") || "sample";
  return digest(text, algo);
}
''',
        "color": r'''
function hexToRgb(hex) {
  const h = String(hex).replace(/^#/, "");
  const full = h.length === 3 ? h.split("").map(c => c + c).join("") : h;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) throw new Error("bad hex");
  return { r: parseInt(full.slice(0, 2), 16), g: parseInt(full.slice(2, 4), 16), b: parseInt(full.slice(4, 6), 16) };
}
function contrastRatio(a, b) {
  const lum = ({ r, g, b }) => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const L1 = lum(hexToRgb(a)), L2 = lum(hexToRgb(b));
  const [hi, lo] = L1 > L2 ? [L1, L2] : [L2, L1];
  return (hi + 0.05) / (lo + 0.05);
}
function run(argv) {
  if (argv[0] === "contrast") return contrastRatio(argv[1] || "#000", argv[2] || "#fff").toFixed(3);
  return JSON.stringify(hexToRgb(argv[0] || "#c9a227"));
}
''',
        "number": r'''
function clamp(n, min, max) { return Math.min(max, Math.max(min, n)); }
function parseNumber(s) {
  const m = String(s).trim().match(/^(-?\d+(?:\.\d+)?)([kKmMbB])?$/);
  if (!m) return Number(s);
  const n = Number(m[1]);
  const u = (m[2] || "").toLowerCase();
  return n * ({ k: 1e3, m: 1e6, b: 1e9 }[u] || 1);
}
function run(argv) {
  const mode = argv[0] || "parse";
  if (mode === "clamp") return String(clamp(Number(argv[1]), Number(argv[2]), Number(argv[3])));
  return String(parseNumber(argv[1] || argv[0] || "1.5k"));
}
''',
        "path": r'''
const path = require("path");
function normalizePath(p, style = "posix") {
  const s = style === "win32" ? path.win32.normalize(String(p)) : path.posix.normalize(String(p).replace(/\\/g, "/"));
  return s;
}
function run(argv) {
  const style = argv[0] === "win32" ? "win32" : "posix";
  const p = argv[0] === "win32" || argv[0] === "posix" ? argv[1] : argv[0];
  return normalizePath(p || "./a/../b//c", style);
}
''',
        "encode": r'''
function b64urlEncode(s) {
  return Buffer.from(String(s), "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}
function b64urlDecode(s) {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  return Buffer.from(String(s).replace(/-/g, "+").replace(/_/g, "/") + pad, "base64").toString("utf8");
}
function run(argv) {
  const mode = argv[0] || "encode";
  const text = argv.slice(1).join(" ") || "hello";
  return mode === "decode" ? b64urlDecode(text) : b64urlEncode(text);
}
''',
        "validate": r'''
function validate(value, rules = {}) {
  const errors = [];
  const s = value == null ? "" : String(value);
  if (rules.required && !s) errors.push("required");
  if (rules.min != null && s.length < rules.min) errors.push("min");
  if (rules.max != null && s.length > rules.max) errors.push("max");
  if (rules.pattern && !new RegExp(rules.pattern).test(s)) errors.push("pattern");
  return { ok: errors.length === 0, errors, value: s };
}
function run(argv) {
  const value = argv[0] || "ok";
  const min = Number(argv[1] || 1);
  return JSON.stringify(validate(value, { required: true, min }), null, 2);
}
''',
        "list": r'''
function unique(items) { return [...new Set(items)]; }
function intersect(a, b) { const s = new Set(b); return a.filter(x => s.has(x)); }
function run(argv) {
  const mode = argv[0] || "unique";
  const lines = (argv[1] || "a\nb\na\nc").split(/\r?\n/).filter(Boolean);
  if (mode === "count") return String(lines.length);
  return unique(lines).join("\n");
}
''',
        "stat": r'''
function stats(nums) {
  const xs = nums.filter(n => Number.isFinite(n)).sort((a, b) => a - b);
  if (!xs.length) return { count: 0 };
  const sum = xs.reduce((a, b) => a + b, 0);
  const mid = xs.length % 2 ? xs[(xs.length - 1) / 2] : (xs[xs.length / 2 - 1] + xs[xs.length / 2]) / 2;
  return { count: xs.length, min: xs[0], max: xs[xs.length - 1], mean: sum / xs.length, median: mid, sum };
}
function run(argv) {
  const nums = (argv.join(" ") || "1 2 3 4 5").trim().split(/\s+/).map(Number);
  return JSON.stringify(stats(nums), null, 2);
}
''',
        "markup": r'''
function stripTags(html) { return String(html).replace(/<[^>]+>/g, ""); }
function mdEscape(s) { return String(s).replace(/([\\`*_{}\[\]()#+\-.!])/g, "\\$1"); }
function run(argv) {
  const mode = argv[0] || "strip";
  const text = argv.slice(1).join(" ") || "<b>hi</b>";
  return mode === "escape" ? mdEscape(text) : stripTags(text);
}
''',
        "id": r'''
const crypto = require("crypto");
function id(size = 16) { return crypto.randomBytes(size).toString("hex"); }
function ulike() {
  const t = Date.now().toString(36);
  return t + "-" + crypto.randomBytes(6).toString("hex");
}
function run(argv) {
  if (argv[0] === "ulike") return ulike();
  return id(Number(argv[0] || 16));
}
''',
        "net": r'''
function isIpv4(s) {
  const p = String(s).split(".");
  return p.length === 4 && p.every(x => /^\d+$/.test(x) && Number(x) >= 0 && Number(x) <= 255);
}
function hostport(s) {
  const m = String(s).match(/^\[?([^\]]+?)\]?(?::(\d+))?$/);
  if (!m) throw new Error("bad hostport");
  return { host: m[1], port: m[2] ? Number(m[2]) : null };
}
function run(argv) {
  const mode = argv[0] || "ipv4";
  if (mode === "hostport") return JSON.stringify(hostport(argv[1] || "127.0.0.1:8080"));
  return String(isIpv4(argv[1] || argv[0] || "1.2.3.4"));
}
''',
        "config": r'''
function parseEnv(text) {
  const out = {};
  for (const line of String(text).split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i < 0) continue;
    let v = t.slice(i + 1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    out[t.slice(0, i).trim()] = v;
  }
  return out;
}
function missingKeys(env, required) {
  return required.filter(k => env[k] == null || env[k] === "");
}
function run(argv) {
  const sample = argv[0] && argv[0].includes("=") ? argv.join("\n") : "NODE_ENV=production\nPORT=3000";
  const env = parseEnv(sample);
  if (argv[0] === "keys") return Object.keys(env).sort().join("\n");
  return JSON.stringify({ keys: Object.keys(env).length, missing: missingKeys(env, ["NODE_ENV"]) }, null, 2);
}
''',
    }
    body = preamble + bodies[cat]
    names = re.findall(r"function\s+(\w+)", body)
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return body + "\nmodule.exports = { " + ", ".join(seen) + " };\n"


def cli_js(spec: dict) -> str:
    return f'''#!/usr/bin/env node
const lib = require("./index.js");
try {{
  const out = lib.run(process.argv.slice(2));
  if (out != null) process.stdout.write(String(out).endsWith("\\n") ? String(out) : String(out) + "\\n");
}} catch (err) {{
  console.error("{spec["name"]}:", err.message || err);
  process.exit(1);
}}
'''


def test_js(spec: dict) -> str:
    return f'''const test = require("node:test");
const assert = require("node:assert/strict");
const lib = require("./index.js");

test("{spec["name"]} run returns output", () => {{
  const out = lib.run([]);
  assert.ok(out != null);
  assert.ok(String(out).length > 0);
}});
'''


def docs_html(spec: dict) -> str:
    name = spec["name"]
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name} · {spec["version"]}</title>
  <meta name="description" content="{escape_html(spec["description"])}">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <nav class="nav sans">
    <a class="brand-lockup" href="index.html"><img src="logo.svg" alt=""> {name}</a>
    <div class="links">
      <a href="#overview">Overview</a>
      <a href="#usage">Usage</a>
      <a href="https://github.com/{OWNER}/{name}">GitHub</a>
    </div>
  </nav>
  <header class="hero">
    <img src="logo.svg" alt="{name} mark">
    <div>
      <p class="kicker sans">@{OWNER}/{name} · {spec["version"]}</p>
      <h1>{name}</h1>
      <p class="lede">{escape_html(spec["description"])}</p>
      <div class="badges sans">
        <span class="badge">{spec["version"]}</span>
        <span class="badge">{spec["category"]}</span>
        <span class="badge">MIT</span>
        <span class="badge">CLI</span>
      </div>
    </div>
  </header>
  <div class="wrap">
    <section id="overview">
      <h2>Overview</h2>
      <p>{escape_html(spec["description"])} Built as a tiny zero-dependency Node toolkit with a library API and a stdin-friendly CLI.</p>
    </section>
    <section id="usage">
      <h2>Usage</h2>
      <pre><code>git clone https://github.com/{OWNER}/{name}.git
cd {name}
node src/cli.js --help
node --test</code></pre>
      <p>Library entry: <code>src/index.js</code>. Category: <strong>{spec["category"]}</strong>.</p>
    </section>
  </div>
  <footer class="sans">MIT © 2026 {OWNER} · <strong>{spec["version"]}</strong> · <a href="https://github.com/{OWNER}/{name}">GitHub</a></footer>
</body>
</html>
'''


def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def readme(spec: dict) -> str:
    name = spec["name"]
    return f'''# {name}

{spec["description"]}

**Site:** https://{OWNER}.github.io/{name}/

## Install / run

```bash
git clone https://github.com/{OWNER}/{name}.git
cd {name}
node src/cli.js
node --test
```

## API

Library entrypoint: [`src/index.js`](./src/index.js)

Category: `{spec["category"]}` · Version `{spec["version"]}`

## License

MIT — see [LICENSE](./LICENSE).
'''


def acquisition(spec: dict) -> str:
    return f'''# Acquisition notes — {spec["name"]}

## Product

`{spec["name"]}` is a focused `{spec["category"]}` toolkit: {spec["description"]}

## Assets

- Source: `src/index.js`, `src/cli.js`
- Docs site: `docs/` (GitHub Pages)
- Tests: `src/index.test.js` (node:test)

## Integration

Zero runtime dependencies. Suitable as a CLI in CI or a small library import in Node 18+.

## License

MIT
'''


def license_text() -> str:
    return f'''MIT License

Copyright (c) 2026 {OWNER}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def write_repo(spec: dict, dest: Path) -> None:
    name = spec["name"]
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "src").mkdir(parents=True)
    (dest / "docs").mkdir(parents=True)
    (dest / ".github").mkdir(parents=True)

    (dest / "src" / "index.js").write_text(js_impl(spec), encoding="utf-8")
    (dest / "src" / "cli.js").write_text(cli_js(spec), encoding="utf-8")
    os.chmod(dest / "src" / "cli.js", 0o755)
    (dest / "src" / "index.test.js").write_text(test_js(spec), encoding="utf-8")
    (dest / "docs" / "index.html").write_text(docs_html(spec), encoding="utf-8")
    (dest / "docs" / "styles.css").write_text(STYLES, encoding="utf-8")
    # unique-ish logo color from name hash
    h = hashlib.sha256(name.encode()).hexdigest()
    color = f"#{h[:6]}"
    logo = LOGO.replace("#C9A227", color).replace("#c9a227", color)
    (dest / "docs" / "logo.svg").write_text(logo, encoding="utf-8")
    (dest / "docs" / ".nojekyll").write_text("", encoding="utf-8")
    (dest / "README.md").write_text(readme(spec), encoding="utf-8")
    (dest / "ACQUISITION.md").write_text(acquisition(spec), encoding="utf-8")
    (dest / "LICENSE").write_text(license_text(), encoding="utf-8")
    (dest / ".github" / "FUNDING.yml").write_text(
        "github: [theworker02]\nthanks_dev: u/gh/theworker02\n", encoding="utf-8"
    )
    (dest / ".gitignore").write_text("node_modules/\n.DS_Store\n", encoding="utf-8")
    pkg = {
        "name": f"@{OWNER}/{name}",
        "version": spec["version"],
        "private": True,
        "description": spec["description"],
        "bin": {name: "src/cli.js"},
        "main": "./src/index.js",
        "scripts": {"test": "node --test"},
        "license": "MIT",
        "engines": {"node": ">=18"},
        "repository": {"type": "git", "url": f"https://github.com/{OWNER}/{name}.git"},
        "homepage": f"https://{OWNER}.github.io/{name}/",
        "keywords": spec["keywords"],
    }
    (dest / "package.json").write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")


def enable_pages(name: str) -> None:
    # delete existing broken config if any, then create legacy /docs
    run(["gh", "api", "-X", "DELETE", f"repos/{OWNER}/{name}/pages"], check=False)
    r = run(
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
    if r.returncode != 0 and "already exists" not in (r.stderr + r.stdout):
        # try PUT update
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


def create_one(spec: dict) -> dict:
    name = spec["name"]
    t0 = time.time()
    work = Path(tempfile.mkdtemp(prefix=f"repo-{name}-"))
    try:
        write_repo(spec, work / name)
        repo_dir = work / name
        run(["git", "init", "-b", "main"], cwd=repo_dir)
        run(["git", "config", "user.email", f"{OWNER}@users.noreply.github.com"], cwd=repo_dir)
        run(["git", "config", "user.name", OWNER], cwd=repo_dir)
        run(["git", "add", "-A"], cwd=repo_dir)
        run(["git", "commit", "-m", f"Initial release of {name}"], cwd=repo_dir)

        # create + push
        r = run(
            [
                "gh",
                "repo",
                "create",
                f"{OWNER}/{name}",
                "--public",
                "--description",
                spec["description"][:350],
                "--source=.",
                "--remote=origin",
                "--push",
                "--disable-wiki",
                "--disable-issues",
            ],
            cwd=repo_dir,
            check=False,
        )
        if r.returncode != 0:
            err = (r.stderr or "") + (r.stdout or "")
            low = err.lower()
            if "already exists" in low or "name already exists" in low:
                return {"name": name, "status": "exists", "error": "exists"}
            if "too many repositories" in low or "secondary rate limit" in low or "abuse detection" in low:
                global RATE_LIMIT_HITS
                with RATE_LIMIT_LOCK:
                    RATE_LIMIT_HITS += 1
                return {"name": name, "status": "rate_limit", "error": err[-300:]}
            return {"name": name, "status": "error", "error": err[-500:]}

        enable_pages(name)
        with LOCK:
            with PROGRESS.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"name": name, "category": spec["category"], "t": time.time()}) + "\n")
            with CREATED.open("a", encoding="utf-8") as f:
                f.write(name + "\n")
        return {"name": name, "status": "ok", "seconds": round(time.time() - t0, 2)}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)[:500]}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def wait_for_rate_limit():
    try:
        out = run(["gh", "api", "rate_limit", "--jq", ".resources.core.remaining"])
        rem = int(out.stdout.strip())
        if rem < 50:
            reset = int(run(["gh", "api", "rate_limit", "--jq", ".resources.core.reset"]).stdout)
            sleep_for = max(5, reset - int(time.time()) + 5)
            print(f"[rate-limit] remaining={rem}; sleeping {sleep_for}s", flush=True)
            time.sleep(sleep_for)
    except Exception:
        time.sleep(5)


def main():
    global RATE_LIMIT_HITS
    print(f"[factory] target public repos = {TARGET}, workers={WORKERS}", flush=True)
    taken = existing_names()
    print(f"[factory] existing names tracked: {len(taken)}", flush=True)
    current = public_count()
    print(f"[factory] public_repos now: {current}", flush=True)
    if current >= TARGET:
        print("[factory] already at target", flush=True)
        return 0

    needed = TARGET - current + 50  # buffer for collisions
    catalog = generate_catalog(needed, taken)
    print(f"[factory] catalog size: {len(catalog)}", flush=True)

    idx = 0
    ok = 0
    err = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        while True:
            current = public_count()
            if current >= TARGET:
                print(f"[factory] reached target: {current}", flush=True)
                break
            wait_for_rate_limit()
            batch_n = min(WORKERS * 3, len(catalog) - idx, TARGET - current + WORKERS)
            if batch_n <= 0:
                # generate more names
                more = generate_catalog(500, taken | {c["name"] for c in catalog})
                catalog.extend(more)
                batch_n = min(WORKERS * 3, len(catalog) - idx)
                if batch_n <= 0:
                    print("[factory] catalog exhausted unexpectedly", flush=True)
                    break
            batch = catalog[idx : idx + batch_n]
            idx += batch_n
            for name in [s["name"] for s in batch]:
                taken.add(name)
            futs = [ex.submit(create_one, spec) for spec in batch]
            rate_hits = 0
            for fut in concurrent.futures.as_completed(futs):
                res = fut.result()
                if res["status"] == "ok":
                    ok += 1
                    print(f"[ok] {res['name']} ({res.get('seconds')}s) total_ok={ok}", flush=True)
                elif res["status"] == "exists":
                    print(f"[skip] {res['name']} exists", flush=True)
                elif res["status"] == "rate_limit":
                    rate_hits += 1
                    err += 1
                    print(f"[rate] {res['name']}: GitHub repo-create throttle", flush=True)
                else:
                    err += 1
                    print(f"[err] {res['name']}: {res.get('error')}", flush=True)
            print(
                f"[progress] public≈{public_count()} ok_session={ok} err_session={err} idx={idx}",
                flush=True,
            )
            if rate_hits:
                # Do not rewind the whole batch (successful names already exist).
                # Exponential backoff + single-repo probe before resuming the pool.
                base = int(os.environ.get("PORTFOLIO_BACKOFF_SECS", "1800"))
                with RATE_LIMIT_LOCK:
                    hits = RATE_LIMIT_HITS
                sleep_for = min(7200, base * max(1, hits // 3))
                print(f"[backoff] sleeping {sleep_for}s after {rate_hits} rate-limit hits (total_hits={hits})", flush=True)
                time.sleep(sleep_for)
                # Probe with one create before opening the worker pool again.
                while True:
                    current = public_count()
                    if current >= TARGET:
                        break
                    probe_spec = None
                    created_set = {
                        x.strip().lower()
                        for x in (CREATED.read_text().splitlines() if CREATED.exists() else [])
                    }
                    while idx < len(catalog):
                        cand = catalog[idx]
                        idx += 1
                        if cand["name"].lower() in created_set:
                            continue
                        probe_spec = cand
                        break
                    if probe_spec is None:
                        more = generate_catalog(200, taken)
                        catalog.extend(more)
                        continue
                    print(f"[probe] trying {probe_spec['name']}", flush=True)
                    probe_res = create_one(probe_spec)
                    print(f"[probe] {probe_res}", flush=True)
                    if probe_res["status"] == "ok":
                        ok += 1
                        taken.add(probe_spec["name"])
                        break
                    if probe_res["status"] in {"rate_limit", "error"} and "too many" in str(probe_res.get("error", "")).lower():
                        sleep_for = min(7200, sleep_for + 600)
                        print(f"[probe] still throttled; sleeping {sleep_for}s", flush=True)
                        time.sleep(sleep_for)
                        continue
                    # exists or other — keep probing next
                    continue
            else:
                with RATE_LIMIT_LOCK:
                    # decay hit counter on healthy batches
                    if RATE_LIMIT_HITS > 0:
                        RATE_LIMIT_HITS = max(0, RATE_LIMIT_HITS - 1)
                time.sleep(float(os.environ.get("PORTFOLIO_PACE_SECS", "12")))

    print(f"[factory] done session ok={ok} err={err} public={public_count()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
