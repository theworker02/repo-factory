# repo-factory

High-throughput publisher for focused Node toolkits under `theworker02`, plus a **v1.0 thickener** that expands docs, logos, badges, and GitHub Releases.

## Scripts

| Script | Purpose |
| --- | --- |
| `factory.py` | Create unique tool repos with Pages + v1.0.0 release |
| `thicken.py` | Retrofit existing repos: thick README, logo, badges, CHANGELOG, diligence docs, `v1.0.0` release |

## Run

```bash
export PORTFOLIO_TARGET=4000
export PORTFOLIO_WORKERS=2
python3 -u factory.py

export THICKEN_WORKERS=4
python3 -u thicken.py
```
