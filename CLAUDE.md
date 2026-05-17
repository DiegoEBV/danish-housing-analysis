# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Danish Residential Housing Analysis (1992–2024) — a data pipeline and visualization project exploring how housing prices diverged between Copenhagen and Danish provinces across interest-rate and inflation regimes. Built as a university course deliverable (UPC 2026-01, Data Visualization).

**Research question**: Which housing typologies show the highest volatility and drawdowns during financial crises?

## Common Commands

```bash
# Run the Bronze→Silver cleaning pipeline
python scripts/run_cleaning.py --config configs/analysis.yaml

# Sample run (faster, limits rows for testing)
python scripts/run_cleaning.py --config configs/analysis.yaml --sample 50000

# Run full pipeline (Silver + Gold marts)
python scripts/run_pipeline.py

# Generate synthetic Tableau marts (no real data required)
python scripts/generate_tableau.py

# Upload processed layers to GCP
python scripts/upload_to_gcs.py

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/danish_housing

# Lint / format
ruff check .
black .
mypy src/
```

## Architecture: Medallion Pipeline

Data flows through three layers (Kaggle → Bronze → Silver → Gold → Tableau):

```
Kaggle CSV (~1.5M rows)
    ↓  run_cleaning.py
Bronze: data/raw/DKHousingPrices.csv
    ↓  src/danish_housing/cleaning.py  (rules P1–P8)
Silver: data/processed/danish_housing_clean.parquet
    ↓  src/danish_housing/kpis.py      (KPIs 1–5)
Gold:   data/processed/gold/           (5 mart CSVs)
    ↓  tableau/marts/                  (Tableau-ready exports)
Tableau Desktop (.twbx)
```

All pipeline parameters are centralized in [configs/analysis.yaml](configs/analysis.yaml) — paths, KPI thresholds, cleaning rule values, crisis periods, house types, and regions. Scripts read from this config; avoid hardcoding values that belong there.

## Source Module: `src/danish_housing/`

**[cleaning.py](src/danish_housing/cleaning.py)** — 8 discrete cleaning rules (P1–P8), each a standalone function:
- P1: Fill missing city with "Unknown"
- P2: Flag missing macro variables (2023–2024 gap)
- P3: Flag non-market sales (family transfers, `"-"` type)
- P4: Flag `year_build < 1800`
- P5: IQR × 3.0 outlier detection on price columns
- P6: Flag 1992–1994 as preliminary period (lower data completeness)
- P7: Pad zip codes to 4-digit strings
- P8: Rename columns with `%25` URL encoding → `_pct`

Entry point: `run_cleaning_pipeline(df, config)` — applies all 8 rules in order, returns `(cleaned_df, audit_log_df)`.

**[kpis.py](src/danish_housing/kpis.py)** — 5 KPI functions operating on the Silver layer:
1. `compute_real_price_per_sqm` — CPI-deflated price (base year 2024)
2. `compute_regional_index` — quarterly index normalized to 1992 = 100 per region
3. `compute_drawdown` — peak-to-trough decline for crisis analysis
4. `compute_volatility` — 4-quarter rolling std dev of % price changes
5. `compute_volume_bond_correlation` — sales volume vs. mortgage bond yield (2-quarter lag)

## Scripts vs. Notebooks

- **Scripts** (`scripts/`) are the authoritative pipeline executors — use these for reproducible runs.
- **Notebooks** (`notebook/`) are deliverable artifacts (TB2, TB3) for grading; they duplicate some pipeline logic for demonstration purposes.
- When modifying cleaning logic, update `src/danish_housing/cleaning.py` first; notebooks reference these functions.

## Gold Marts (Tableau Exports)

Five CSV files under `tableau/marts/` (and generated to `data/processed/gold/`):

| File | Content |
|------|---------|
| `mart_quarterly_regional_index.csv` | Quarterly prices & index by region |
| `mart_drawdowns.csv` | Drawdown % by quarter, region, house type |
| `mart_volatility.csv` | Rolling 4Q volatility by house type |
| `mart_macro_correlation.csv` | Volume vs. bond yields with 2Q lag |
| `mart_transactions_map.csv` | Aggregated by zip_code for map view |

Synthetic versions can be generated without real data using `generate_tableau.py`.

## Data Conventions

- **Data is not in the repo** — all CSV/parquet files are gitignored. Raw data (~1.5 GB) must be downloaded from Kaggle separately.
- **Regions** (5): København, Midtjylland, Nordjylland, Sjælland, Syddanmark
- **House types** (4): Villa, Ejerlejlighed (condo), Fritidshus (summerhouse), Rækkehus (townhouse)
- **Crisis periods** defined in config: 2007–2012 (GFC) and 2006–2009 (housing bubble)
- Silver layer uses Snappy-compressed Parquet; scripts use garbage collection explicitly to handle peak memory on full 1.5M-row runs.

## Language Conventions

- Code and variable names: English
- Comments, documentation, and notebooks: Spanish
- Config keys: English
