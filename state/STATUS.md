# Status

- **public repos audited:** 3983 (non-fork)
- **with ACQUISITION.md + docs/logo.svg:** 3983 / 3983
- **updated:** 2026-09-29T15:20:00Z

## Acquisition + logo standard

Every portfolio repository includes:

1. Official logo at `docs/logo.svg` (unique accent; featured in README)
2. Diligence brief at `ACQUISITION.md` (executive summary, asset map, technical due diligence, commercial posture)
3. README references to the logo and acquisition brief (backfilled where needed)

## Tooling

- `factory.py` / `thicken.py` — write logo + ACQUISITION on create / v1.0 thicken
- `ensure_acq_logo.py` — portfolio-wide backfill for acquisition docs + official logos
- Verified via raw content checks; hard cases (branch protection) merged via PR / Git Data API

## Notes

- Factory publish target (4000 public) previously met
- v1.0.0 releases + badge packs already shipped in prior thicken pass
