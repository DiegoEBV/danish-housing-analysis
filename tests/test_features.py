"""
tests/test_features.py — Tests para src/danish_housing/features.py.

Valida que el feature matrix:
1. No contiene columnas leaky (FORBIDDEN_FEATURE_COLUMNS).
2. Las features rolling son causales (no usan el row actual).
3. El split temporal es estricto.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from danish_housing.features import (
    FORBIDDEN_FEATURE_COLUMNS,
    add_rolling_regional_features,
    build_feature_matrix,
    temporal_train_test_split,
)


@pytest.fixture
def silver_like_df() -> pd.DataFrame:
    """Mini Silver con todas las columnas que el pipeline genera."""
    rng = np.random.default_rng(42)
    n = 200
    years = rng.integers(1992, 2025, size=n)
    return pd.DataFrame({
        "house_id": np.arange(1, n + 1),
        "date": pd.to_datetime([f"{y}-06-15" for y in years]),
        "region": rng.choice(["København", "Sjælland", "Midtjylland"], size=n),
        "house_type": rng.choice(["Villa", "Ejerlejlighed", "Fritidshus"], size=n),
        "city": rng.choice(["Copenhagen", "Aarhus", "Odense"], size=n),
        "sales_type": ["regular_sale"] * n,
        "zip_code": rng.integers(1000, 9999, size=n).astype(str),
        "sqm": rng.gamma(4, 30, size=n).clip(20, 600),
        "no_rooms": rng.integers(1, 8, size=n),
        "year_build": rng.integers(1900, 2024, size=n),
        "purchase_price": rng.lognormal(14, 0.5, size=n).round(0),
        "sqm_price": rng.lognormal(10, 0.3, size=n).round(0),
        "nom_interest_rate_pct": rng.normal(4, 1, n),
        "dk_ann_infl_rate_pct": rng.normal(2, 0.5, n),
        "yield_mortgage_bonds_pct": rng.normal(5, 1.5, n),
        # Flags Silver
        "macro_nulo": False,
        "sales_type_valido": True,
        "purchase_price_outlier": False,
        "sqm_price_outlier": False,
        "year_build_flag": False,
        "periodo_preliminar": False,
    })


def test_build_feature_matrix_no_leakage(silver_like_df):
    df_feat, names, audit = build_feature_matrix(
        silver_like_df, target_col="purchase_price",
        window_years=5, min_obs_per_window=2,
    )
    # Anti-leak guard
    assert audit["leakage_check_passed"] is True
    leaks = FORBIDDEN_FEATURE_COLUMNS & set(names)
    assert not leaks, f"Features leaky en output: {leaks}"
    # Target debe estar en df_feat pero NO en feature_names
    assert "purchase_price" in df_feat.columns
    assert "purchase_price" not in names
    # log_target opcional
    assert "log_target" in df_feat.columns


def test_features_are_numeric_only(silver_like_df):
    df_feat, names, _ = build_feature_matrix(silver_like_df, target_col="purchase_price")
    for col in names:
        dtype = df_feat[col].dtype
        assert pd.api.types.is_numeric_dtype(dtype), f"{col} no es numerica: {dtype}"


def test_rolling_is_causal(silver_like_df):
    """rolling_regional_mean para year=Y solo usa filas con year < Y."""
    df = silver_like_df.copy()
    df["year"] = df["date"].dt.year
    df_roll = add_rolling_regional_features(
        df, price_col="purchase_price", window_years=10, min_obs=2,
    )

    # Para una (region, year) cualquiera, recalcular el mean manualmente con year < Y
    sample = df_roll.dropna(subset=["rolling_regional_mean"]).iloc[0]
    region = sample["region"]
    year_ref = int(sample["year"])

    expected_mask = (
        (df_roll["region"] == region)
        & (df_roll["year"] >= year_ref - 10)
        & (df_roll["year"] <= year_ref - 1)
    )
    expected_mean = df_roll.loc[expected_mask, "purchase_price"].mean()
    actual_mean = sample["rolling_regional_mean"]

    if not np.isnan(expected_mean):
        assert abs(actual_mean - expected_mean) < 1.0, (
            f"Rolling NO es causal: actual={actual_mean}, expected={expected_mean}"
        )


def test_temporal_split_strict(silver_like_df):
    df = silver_like_df.copy()
    df["year"] = df["date"].dt.year
    train, test = temporal_train_test_split(df, train_end=2017, test_start=2018)
    assert train["year"].max() <= 2017
    assert test["year"].min() >= 2018
    # Sin overlap
    assert set(train["house_id"]).isdisjoint(set(test["house_id"]))
