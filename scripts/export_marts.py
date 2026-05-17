"""
scripts/export_marts.py

Genera los marts analíticos de la capa Gold a partir del Silver layer.
Cada mart es un CSV optimizado para una vista específica del dashboard Tableau.

Uso:
    python scripts/export_marts.py --config configs/analysis.yaml
    python scripts/export_marts.py --config configs/analysis.yaml --sample 100000
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from danish_housing.kpis import (
    compute_regional_index,
    compute_regional_drawdowns,
    compute_volatility,
    compute_volume_bond_correlation,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Preparacion del dataframe ─────────────────────────────────────────────────

def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columnas derivadas necesarias para los marts.
    sqm_price_real: precio por m2 deflactado (simplificado sin IPC externo).
    """
    df = df.copy()

    # Crear sqm_price_real si no existe
    if "sqm_price_real" not in df.columns:
        # Deflactor simple basado en inflacion promedio historica danesa (~2% anual)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["year"] = df["date"].dt.year
        base_year = 2024
        price_col = "sqm_price" if "sqm_price" in df.columns else "purchase_price"
        df["deflactor"] = (1.02) ** (base_year - df["year"])
        df["sqm_price_real"] = df[price_col] * df["deflactor"]
        df = df.drop(columns=["deflactor"])
        logger.info("Columna sqm_price_real creada (deflactor 2% anual)")

    # Crear region si no existe
    if "region" not in df.columns and "area" in df.columns:
        df["region"] = df["area"]
    elif "region" not in df.columns:
        df["region"] = "Unknown"

    # Crear house_type si no existe
    if "house_type" not in df.columns and "property_type" in df.columns:
        df["house_type"] = df["property_type"]
    elif "house_type" not in df.columns:
        df["house_type"] = "Unknown"

    return df


# ── Marts ─────────────────────────────────────────────────────────────────────

def build_quarterly_regional_index(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    mart_quarterly_regional_index.csv
    Índice de precios por región y trimestre (base 1992 = 100).
    """
    base_year = cfg.get("kpis", {}).get("index_base_year", 1992)

    df_filtered = df[
        ~df.get("purchase_price_outlier", pd.Series(False, index=df.index))
        & df.get("sales_type_valido", pd.Series(True, index=df.index))
    ].copy()

    mart = compute_regional_index(df_filtered, base_year=base_year)
    mart = mart.sort_values(["region", "quarter"])
    logger.info(f"mart_quarterly_regional_index: {len(mart):,} filas")
    return mart


def build_drawdowns(df: pd.DataFrame, min_obs: int = 5) -> pd.DataFrame:
    """
    mart_drawdowns.csv
    Drawdown pico-valle por region y tipo de vivienda.
    Filtra celdas con menos de min_obs transacciones (evita artefactos de muestra minima).
    """
    df_filtered = df[
        ~df.get("purchase_price_outlier", pd.Series(False, index=df.index))
        & df.get("sales_type_valido", pd.Series(True, index=df.index))
    ].copy()

    df_filtered["quarter"] = pd.to_datetime(df_filtered["date"]).dt.to_period("Q").astype(str)

    # Precio promedio + conteo por trimestre / region / tipologia
    quarterly = (
        df_filtered.groupby(["quarter", "region", "house_type"])
        .agg(
            avg_sqm_price_real=("sqm_price_real", "mean"),
            n_transactions=("sqm_price_real", "count"),
        )
        .reset_index()
        .sort_values(["region", "house_type", "quarter"])
    )

    # Filtro de muestra minima (fix issue 44y: Bornholm 2018Q3 con drawdown -97.5%)
    n_before = len(quarterly)
    quarterly = quarterly[quarterly["n_transactions"] >= min_obs].copy()
    logger.info(f"mart_drawdowns: filtro n_transactions >= {min_obs}: {n_before:,} -> {len(quarterly):,} filas")

    # Drawdown
    quarterly["cumulative_max"] = quarterly.groupby(["region", "house_type"])["avg_sqm_price_real"].cummax()
    quarterly["drawdown_pct"] = (
        (quarterly["avg_sqm_price_real"] - quarterly["cumulative_max"])
        / quarterly["cumulative_max"] * 100
    )

    return quarterly


def build_volatility(df: pd.DataFrame, window: int = 4) -> pd.DataFrame:
    """
    mart_volatility.csv
    Volatilidad rolling de 4 trimestres por tipología de vivienda.
    """
    df_filtered = df[
        ~df.get("purchase_price_outlier", pd.Series(False, index=df.index))
    ].copy()

    df_filtered["quarter"] = pd.to_datetime(df_filtered["date"]).dt.to_period("Q").astype(str)

    quarterly = (
        df_filtered.groupby(["quarter", "house_type"])["sqm_price_real"]
        .mean()
        .reset_index()
        .rename(columns={"sqm_price_real": "avg_sqm_price_real"})
        .sort_values(["house_type", "quarter"])
    )

    quarterly["pct_change"] = quarterly.groupby("house_type")["avg_sqm_price_real"].pct_change()
    quarterly["volatility_4q"] = (
        quarterly.groupby("house_type")["pct_change"]
        .transform(lambda x: x.rolling(window, min_periods=window).std())
    )

    logger.info(f"mart_volatility: {len(quarterly):,} filas")
    return quarterly


def build_macro_correlation(df: pd.DataFrame, lag_quarters: int = 2) -> pd.DataFrame:
    bond_col = next(
        (c for c in ["yield_mortgage_bonds_pct", "yield_on_mortgage_credit_bonds%25", "yield_on_mortgage_credit_bonds%"] if c in df.columns),
        None
    )
    if bond_col is None:
        logger.warning("Columna de bonos no encontrada. Mart macro omitido.")
        return pd.DataFrame()

    df_filtered = df[df.get("sales_type_valido", pd.Series(True, index=df.index))].copy()
    df_filtered["date"] = pd.to_datetime(df_filtered["date"])
    df_filtered["quarter"] = df_filtered["date"].dt.to_period("Q").astype(str)

    mart = (
        df_filtered.groupby("quarter")
        .agg(
            n_transactions=("date", "count"),
            avg_bond_yield=(bond_col, "mean"),
        )
        .reset_index()
        .sort_values("quarter")
    )

    mart["bond_yield_lag2q"] = mart["avg_bond_yield"].shift(lag_quarters)
    mart["volume_bond_corr"] = (
        mart["n_transactions"]
        .rolling(8, min_periods=4)
        .corr(mart["bond_yield_lag2q"])
    )

    logger.info(f"mart_macro_correlation: {len(mart):,} filas")
    return mart


def build_transactions_map(df: pd.DataFrame) -> pd.DataFrame:
    """
    mart_transactions_map.csv
    Precios por zip_code y año para el mapa choropleth de Tableau.
    """
    df_filtered = df[
        ~df.get("purchase_price_outlier", pd.Series(False, index=df.index))
        & df.get("sales_type_valido", pd.Series(True, index=df.index))
    ].copy()

    df_filtered["year"] = pd.to_datetime(df_filtered["date"]).dt.year

    mart = (
        df_filtered.groupby(["year", "zip_code"])
        .agg(
            avg_sqm_price_real=("sqm_price_real", "mean"),
            n_transactions=("sqm_price_real", "count"),
            city=("city", lambda x: x.mode()[0] if len(x) > 0 else "Unknown"),
            region=("region", lambda x: x.mode()[0] if len(x) > 0 else "Unknown"),
        )
        .reset_index()
    )

    logger.info(f"mart_transactions_map: {len(mart):,} filas")
    return mart


# ── Pipeline ──────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Exportar marts Gold desde Silver")
    parser.add_argument("--config", default="configs/analysis.yaml")
    parser.add_argument("--sample", type=int, default=None, help="Limitar a N filas para prueba")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    silver_path = Path(cfg["paths"]["silver_parquet"])
    gold_dir = Path(cfg["paths"]["gold_dir"])
    marts_dir = Path(cfg["paths"]["marts_dir"])
    gold_dir.mkdir(parents=True, exist_ok=True)
    marts_dir.mkdir(parents=True, exist_ok=True)

    if not silver_path.exists():
        logger.error(f"Silver layer no encontrado: {silver_path}")
        logger.error("Ejecuta primero: python scripts/run_cleaning.py --config configs/analysis.yaml")
        sys.exit(1)

    logger.info(f"Cargando Silver layer desde {silver_path}")
    df = pd.read_parquet(silver_path)
    if args.sample:
        df = df.sample(args.sample, random_state=42)
    logger.info(f"Registros cargados: {len(df):,}")

    # Agregar columnas derivadas necesarias
    df = add_derived_columns(df)

    # Parametros marts
    marts_cfg = cfg.get("marts", {})
    drawdown_min_obs = marts_cfg.get("drawdown_min_obs", 5)
    volatility_window = cfg.get("kpis", {}).get("volatility_window_quarters", 4)

    # Generar y guardar cada mart
    marts = {
        "mart_quarterly_regional_index": build_quarterly_regional_index(df, cfg),
        "mart_drawdowns": build_drawdowns(df, min_obs=drawdown_min_obs),
        "mart_volatility": build_volatility(df, volatility_window),
        "mart_macro_correlation": build_macro_correlation(df),
        "mart_transactions_map": build_transactions_map(df),
    }

    for nombre, mart in marts.items():
        if mart is not None and len(mart) > 0:
            for d in (gold_dir, marts_dir):
                out = d / f"{nombre}.csv"
                mart.to_csv(out, index=False)
            logger.info(f"✅ {nombre}.csv → {gold_dir} y {marts_dir} ({len(mart):,} filas)")
        else:
            logger.warning(f"⚠️  {nombre} vacío — omitido")

    logger.info(f"\n✅ Gold layer generado en {gold_dir}")
    logger.info("Siguiente paso: python scripts/upload_to_gcs.py --layer gold --config configs/analysis.yaml")


if __name__ == "__main__":
    main()
