# repo-factory

High-throughput publisher for focused Node toolkits under `theworker02`.

Each generated repository includes:

- Working zero-dependency library + CLI (`src/`)
- Tests via `node:test`
- Polished GitHub Pages site in `docs/`
- MIT license and `.github/FUNDING.yml`

## Run

```bash
export PORTFOLIO_TARGET=4000
export PORTFOLIO_WORKERS=2
export PORTFOLIO_BACKOFF_SECS=1200
export PORTFOLIO_PACE_SECS=8
python3 -u factory.py
```

`fix_pages.py` enables `/docs` Pages for existing public repos missing a live site.
