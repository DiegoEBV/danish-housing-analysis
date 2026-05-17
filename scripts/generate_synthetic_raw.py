"""
scripts/generate_synthetic_raw.py

Genera un parquet sintetico con el schema de DKHousingPrices.parquet para
smoke tests del pipeline (no para entrega — los marts deben generarse del
dataset real de Kaggle).

Uso:
    uv run python scripts/generate_synthetic_raw.py
    uv run python scripts/generate_synthetic_raw.py --rows 5000 --output data/raw/DKHousingPrices.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = ["København", "Sjælland", "Syddanmark", "Midtjylland", "Nordjylland"]
HOUSE_TYPES = ["Villa", "Ejerlejlighed", "Fritidshus", "Rækkehus"]
SALES_TYPES = ["regular_sale", "family_sale", "other_sale", "auction", "-"]
CITIES = ["Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg", "Randers", "Kolding"]


def generate(rows: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    dates = pd.to_datetime(
        rng.choice(pd.date_range("1992-01-01", "2024-12-31"), size=rows)
    )
    years = dates.year

    region = rng.choice(REGIONS, size=rows, p=[0.3, 0.2, 0.2, 0.2, 0.1])
    house_type = rng.choice(HOUSE_TYPES, size=rows, p=[0.45, 0.30, 0.10, 0.15])

    sqm = rng.gamma(shape=4.0, scale=30.0, size=rows).clip(20, 600).round(0)
    no_rooms = (sqm / 30 + rng.normal(0, 1, rows)).clip(1, 10).round(0).astype(int)
    year_build = rng.integers(1900, 2024, size=rows)

    # Precio base con tendencia regional + temporal + ruido
    base_price = np.where(
        region == "København", 25000,
        np.where(region == "Sjælland", 15000, 12000),
    )
    type_mult = np.where(
        house_type == "Villa", 1.0,
        np.where(house_type == "Ejerlejlighed", 1.1,
                 np.where(house_type == "Fritidshus", 0.7, 0.9)),
    )
    time_trend = 1.0 + (years - 1992) * 0.05  # +5%/anio
    sqm_price = (base_price * type_mult * time_trend * rng.lognormal(0, 0.2, rows)).round(0)
    purchase_price = (sqm_price * sqm).round(0)

    # Inflacion danesa anual aproximada (1992-2024)
    infl_by_year = {y: max(0.5, 2.0 + rng.normal(0, 0.7)) for y in range(1992, 2025)}
    yield_by_year = {y: max(0.5, 7.0 - (y - 1992) * 0.1 + rng.normal(0, 0.5)) for y in range(1992, 2025)}

    df = pd.DataFrame({
        "house_id": np.arange(1, rows + 1),
        "date": dates,
        "city": rng.choice(CITIES + [None], size=rows, p=[0.14] * len(CITIES) + [0.02]),
        "sales_type": rng.choice(SALES_TYPES, size=rows, p=[0.85, 0.05, 0.04, 0.04, 0.02]),
        "house_type": house_type,
        "region": region,
        "zip_code": rng.integers(1000, 9999, size=rows),
        "sqm": sqm,
        "no_rooms": no_rooms,
        "year_build": year_build,
        "purchase_price": purchase_price,
        "sqm_price": sqm_price,
        # Macro vars con sufijo %25 (URL-encoded) como en el real
        "nom_interest_rate%25": [max(0.5, 6 - (d.year - 1992) * 0.1) for d in dates],
        "dk_ann_infl_rate%25": [infl_by_year[d.year] for d in dates],
        "yield_on_mortgage_credit_bonds%25": [yield_by_year[d.year] for d in dates],
        "%_change_between_offer_and_purchase": rng.normal(-2, 5, rows).round(2),
    })

    # Inyecta algunos outliers (~1%) para que P5 los detecte
    outlier_idx = rng.choice(rows, size=max(1, rows // 100), replace=False)
    df.loc[outlier_idx, "purchase_price"] *= 50

    # Macro NaN para 2023-2024 (replicar el gap del real)
    macro_cols = ["dk_ann_infl_rate%25", "yield_on_mortgage_credit_bonds%25"]
    df.loc[df["date"].dt.year >= 2023, macro_cols] = np.nan

    return df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=5000, help="Numero de filas a generar")
    p.add_argument("--output", default="data/raw/DKHousingPrices.parquet")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    df = generate(args.rows, seed=args.seed)
    df.to_parquet(out, index=False, compression="snappy")

    print(f"Generadas {len(df):,} filas en {out}")
    print(f"  Rango fechas: {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"  Outliers de precio inyectados: ~{len(df) // 100}")
    print(f"  Macro NaN (2023-2024): {df['dk_ann_infl_rate%25'].isna().sum()}")


if __name__ == "__main__":
    main()
