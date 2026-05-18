"""
tests/test_cleaning.py — Tests unitarios para las reglas de limpieza P1–P8.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from danish_housing.cleaning import (
    fix_city_nulls,
    fix_zip_code,
    flag_invalid_sales,
    flag_macro_nulls,
    flag_old_year_build,
    flag_preliminary_period,
    flag_price_outliers,
    rename_rate_columns,
    run_cleaning_pipeline,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """DataFrame mínimo para tests."""
    return pd.DataFrame(
        {
            "house_id": [1, 2, 3, 4, 5],
            "date": ["2020-01-15", "1993-06-01", "2010-03-20", "2008-07-10", "2023-11-05"],
            "city": ["Copenhagen", None, "Aarhus", "Odense", None],
            "sales_type": ["Normal salg", "-", "Normal salg", "Familiehandel", "Normal salg"],
            "house_type": ["Villa", "Ejerlejlighed", "Fritidshus", "Villa", "Rækkehus"],
            "purchase_price": [2_000_000, 1_500_000, 800_000, 50_000_000, 1_200_000],
            "sqm": [120.0, 80.0, 60.0, 200.0, 100.0],
            "sqm_price": [16_667, 18_750, 13_333, 250_000, 12_000],
            "year_build": [1990, 1750, 2005, 1965, 2018],
            "zip_code": [1050, 8000, 5000, 9000, 2100],
            "region": ["København", "Midtjylland", "Syddanmark", "Nordjylland", "København"],
            "nom_interest_rate%25": [5.0, 8.0, 4.0, 6.0, None],
            "dk_ann_infl_rate%25": [2.1, 3.0, 2.5, 1.8, None],
            "yield_on_mortgage_credit_bonds%25": [4.5, 7.0, 3.8, 5.2, None],
        }
    )


def test_fix_city_nulls(sample_df):
    bitacora = []
    df = fix_city_nulls(sample_df.copy(), bitacora)
    assert df["city"].isna().sum() == 0
    assert (df["city"] == "Unknown").sum() == 2
    assert bitacora[0]["problema_id"] == "P1"


def test_flag_macro_nulls(sample_df):
    # Primero renombramos para que las columnas tengan los nombres correctos
    df = sample_df.copy()
    bitacora = []
    df = rename_rate_columns(df, bitacora)
    bitacora = []
    df = flag_macro_nulls(df, bitacora)
    # El último registro tiene nulos en macro
    assert bool(df.loc[4, "macro_nulo"]) is True
    assert bool(df.loc[0, "macro_nulo"]) is False


def test_flag_invalid_sales(sample_df):
    bitacora = []
    df = flag_invalid_sales(sample_df.copy(), bitacora)
    assert bool(df.loc[1, "sales_type_valido"]) is False  # "-"
    assert bool(df.loc[3, "sales_type_valido"]) is False  # "Familiehandel"
    assert bool(df.loc[0, "sales_type_valido"]) is True


def test_flag_old_year_build(sample_df):
    bitacora = []
    df = flag_old_year_build(sample_df.copy(), bitacora, min_year=1800)
    assert bool(df.loc[1, "year_build_flag"]) is True  # 1750
    assert bool(df.loc[0, "year_build_flag"]) is False  # 1990


def test_flag_price_outliers(sample_df):
    bitacora = []
    df = flag_price_outliers(sample_df.copy(), bitacora, iqr_multiplier=3.0)
    # El registro con purchase_price=50_000_000 debería ser outlier
    assert bool(df.loc[3, "purchase_price_outlier"]) is True


def test_flag_preliminary_period(sample_df):
    bitacora = []
    df = flag_preliminary_period(sample_df.copy(), bitacora, before_year=1995)
    # Registro con date 1993-06-01 debe ser preliminar
    assert bool(df.loc[1, "periodo_preliminar"]) is True
    assert bool(df.loc[0, "periodo_preliminar"]) is False


def test_fix_zip_code(sample_df):
    bitacora = []
    df = fix_zip_code(sample_df.copy(), bitacora, pad=4)
    # En pandas 2.x con astype(str), el dtype puede ser object o StringDtype/str
    assert str(df["zip_code"].dtype) in ("object", "string", "str")
    assert df.loc[0, "zip_code"] == "1050"


def test_rename_rate_columns(sample_df):
    bitacora = []
    df = rename_rate_columns(sample_df.copy(), bitacora)
    assert "nom_interest_rate_pct" in df.columns
    assert "dk_ann_infl_rate_pct" in df.columns
    assert "yield_mortgage_bonds_pct" in df.columns
    assert "nom_interest_rate%25" not in df.columns


def test_full_pipeline(sample_df):
    df_clean, bitacora = run_cleaning_pipeline(sample_df.copy())
    assert "macro_nulo" in df_clean.columns
    assert "periodo_preliminar" in df_clean.columns
    assert "purchase_price_outlier" in df_clean.columns
    assert len(bitacora) > 0
    print(f"\nBitácora ({len(bitacora)} entradas):\n{bitacora.to_string()}")
