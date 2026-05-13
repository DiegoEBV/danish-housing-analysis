"""
kpis.py — Cálculo de los 5 KPIs principales del proyecto.

KPI 1: Precio Real por m² (deflactado con IPC danés)
KPI 2: Índice Regional (base 1992 = 100)
KPI 3: Drawdown Pico-Valle
KPI 4: Volatilidad (desv. estándar ventana móvil 4 trimestres)
KPI 5: Elasticidad Volumen-Bonos (correlación descriptiva)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


# ── KPI 1: Precio Real por m² ─────────────────────────────────────────────────

def compute_real_price_per_sqm(
    df: pd.DataFrame,
    cpi_series: pd.Series,
    base_year: int = 2024,
    price_col: str = "purchase_price",
    sqm_col: str = "sqm",
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Calcula el precio real por m² deflactando por IPC danés.

    Args:
        df: DataFrame con transacciones
        cpi_series: Serie con índice IPC, indexada por año (e.g., {2000: 85.3, ...})
        base_year: Año base del IPC (defecto 2024)
        price_col: Columna de precio de compra
        sqm_col: Columna de metros cuadrados
        date_col: Columna de fecha

    Returns:
        DataFrame con columnas adicionales: sqm_price_nom, sqm_price_real
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["year"] = df[date_col].dt.year

    # Precio nominal por m²
    df["sqm_price_nom"] = df[price_col] / df[sqm_col]

    # Deflactor: CPI_base / CPI_year
    cpi_base = cpi_series.get(base_year, 100.0)
    df["cpi_year"] = df["year"].map(cpi_series)
    df["deflactor"] = cpi_base / df["cpi_year"]

    df["sqm_price_real"] = df["sqm_price_nom"] * df["deflactor"]
    return df.drop(columns=["cpi_year", "deflactor"])


# ── KPI 2: Índice Regional ────────────────────────────────────────────────────

def compute_regional_index(
    df: pd.DataFrame,
    base_year: int = 1992,
    price_col: str = "sqm_price_real",
    region_col: str = "region",
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Normaliza el precio promedio por región con base en base_year = 100.

    Returns:
        DataFrame con columnas: year, quarter, region, avg_price, regional_index
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["year"] = df[date_col].dt.year
    df["quarter"] = df[date_col].dt.to_period("Q").astype(str)

    quarterly = (
        df.groupby([region_col, "year", "quarter"])[price_col]
        .mean()
        .reset_index()
        .rename(columns={price_col: "avg_price"})
    )

    # Precio base (promedio año base) por región
    base_prices = (
        quarterly[quarterly["year"] == base_year]
        .groupby(region_col)["avg_price"]
        .mean()
        .rename("base_price")
    )

    quarterly = quarterly.merge(base_prices, on=region_col, how="left")
    quarterly["regional_index"] = (quarterly["avg_price"] / quarterly["base_price"]) * 100
    return quarterly.drop(columns=["base_price"])


# ── KPI 3: Drawdown Pico-Valle ────────────────────────────────────────────────

def compute_drawdown(
    series: pd.Series,
) -> pd.Series:
    """
    Calcula el drawdown pico-valle para una serie temporal de precios.

    El drawdown en tiempo t es: (precio_t - max_precio_hasta_t) / max_precio_hasta_t

    Returns:
        Serie de drawdowns (valores negativos o cero)
    """
    rolling_max = series.cummax()
    drawdown = (series - rolling_max) / rolling_max
    return drawdown


def compute_regional_drawdowns(
    index_df: pd.DataFrame,
    region_col: str = "region",
    index_col: str = "regional_index",
    quarter_col: str = "quarter",
) -> pd.DataFrame:
    """
    Aplica compute_drawdown por región sobre el índice trimestral.

    Returns:
        DataFrame con columna adicional 'drawdown'
    """
    df = index_df.copy().sort_values([region_col, quarter_col])
    df["drawdown"] = (
        df.groupby(region_col)[index_col]
        .transform(compute_drawdown)
    )
    return df


# ── KPI 4: Volatilidad ────────────────────────────────────────────────────────

def compute_volatility(
    index_df: pd.DataFrame,
    window: int = 4,
    region_col: str = "region",
    index_col: str = "regional_index",
    quarter_col: str = "quarter",
) -> pd.DataFrame:
    """
    Calcula la volatilidad como desv. estándar del cambio % del índice
    en una ventana móvil de `window` trimestres.

    Returns:
        DataFrame con columna adicional 'volatility'
    """
    df = index_df.copy().sort_values([region_col, quarter_col])
    df["pct_change"] = (
        df.groupby(region_col)[index_col]
        .pct_change()
    )
    df["volatility"] = (
        df.groupby(region_col)["pct_change"]
        .transform(lambda x: x.rolling(window, min_periods=window).std())
    )
    return df.drop(columns=["pct_change"])


# ── KPI 5: Elasticidad Volumen-Bonos ─────────────────────────────────────────

def compute_volume_bond_correlation(
    df: pd.DataFrame,
    volume_col: str = "n_transactions",
    bond_col: str = "yield_mortgage_bonds_pct",
    date_col: str = "date",
    lag_quarters: int = 2,
) -> pd.DataFrame:
    """
    Calcula la correlación descriptiva entre volumen de ventas trimestrales
    y el rendimiento de bonos hipotecarios, con rezago configurable.

    Returns:
        DataFrame trimestral con correlación por ventana rolling de 8 trimestres
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["quarter"] = df[date_col].dt.to_period("Q").astype(str)

    quarterly = (
        df.groupby("quarter")
        .agg(
            n_transactions=(date_col, "count"),
            avg_bond_yield=(bond_col, "mean"),
        )
        .reset_index()
        .sort_values("quarter")
    )

    # Rezago: volumen de ventas responde a cambios en bonos con lag_quarters trimestres
    quarterly["bond_yield_lagged"] = quarterly["avg_bond_yield"].shift(lag_quarters)
    quarterly["volume_bond_corr"] = (
        quarterly["n_transactions"]
        .rolling(8, min_periods=4)
        .corr(quarterly["bond_yield_lagged"])
    )
    return quarterly
