"""
scripts/build_star_schema.py

Construye el modelo estrella (Star Schema) desde el Silver layer.
Genera 5 tablas: 1 tabla de hechos + 4 dimensiones.

Uso:
    python scripts/build_star_schema.py --config configs/analysis.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_dim_tiempo(df: pd.DataFrame) -> pd.DataFrame:
    """DIM_TIEMPO — dimension temporal con periodo macro."""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.to_period("Q").astype(str)

    def clasif_periodo(y):
        if y < 2000:
            return "pre_2000"
        elif y < 2008:
            return "boom"
        elif y < 2013:
            return "crisis"
        elif y < 2020:
            return "recuperacion"
        else:
            return "post_covid"

    dim = df[["date", "year", "quarter"]].drop_duplicates().copy()
    dim["periodo_macro"] = dim["year"].apply(clasif_periodo)
    dim["periodo_enc"] = dim["periodo_macro"].astype("category").cat.codes
    dim = dim.sort_values("date").reset_index(drop=True)
    dim.insert(0, "tiempo_id", dim.index + 1)
    logger.info(f"dim_tiempo: {len(dim):,} filas")
    return dim


def build_dim_geografia(df: pd.DataFrame) -> pd.DataFrame:
    """DIM_GEOGRAFIA — dimension geografica con flag capital."""
    cols = [c for c in ["zip_code", "city", "area", "region"] if c in df.columns]
    dim = df[cols].drop_duplicates().copy()

    if "region" not in dim.columns:
        dim["region"] = "Unknown"
    if "area" not in dim.columns:
        dim["area"] = dim.get("region", "Unknown")

    dim["region_enc"] = dim["region"].astype("category").cat.codes
    dim["es_capital"] = dim["region"].str.contains("benhavn|Copenhagen|Capital", case=False, na=False).astype(int)
    dim = dim.reset_index(drop=True)
    dim.insert(0, "geografia_id", dim.index + 1)
    logger.info(f"dim_geografia: {len(dim):,} filas")
    return dim


def build_dim_vivienda(df: pd.DataFrame) -> pd.DataFrame:
    """DIM_VIVIENDA — dimension de tipologia y caracteristicas fisicas."""
    cols = [c for c in ["house_type", "no_rooms", "sqm", "year_build"] if c in df.columns]
    dim = df[cols].drop_duplicates().copy()

    if "house_type" not in dim.columns:
        dim["house_type"] = "Unknown"

    dim["type_enc"] = dim["house_type"].astype("category").cat.codes
    dim["es_summerhouse"] = (dim["house_type"] == "Fritidshus").astype(int)

    if "year_build" in dim.columns:
        current_year = 2024
        dim["year_build"] = pd.to_numeric(dim["year_build"], errors="coerce")
        dim["edad_vivienda"] = (current_year - dim["year_build"]).clip(0, 300)
    else:
        dim["edad_vivienda"] = None

    dim = dim.reset_index(drop=True)
    dim.insert(0, "vivienda_id", dim.index + 1)
    logger.info(f"dim_vivienda: {len(dim):,} filas")
    return dim


def build_dim_macro(df: pd.DataFrame) -> pd.DataFrame:
    """DIM_MACRO — dimension macroeconomica anual."""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["date"].dt.year

    macro_cols = ["year"]
    for col in ["nom_interest_rate_pct", "dk_ann_infl_rate_pct", "yield_mortgage_bonds_pct",
                 "nom_interest_rate%", "dk_ann_infl_rate%", "yield_on_mortgage_credit_bonds%"]:
        if col in df.columns:
            macro_cols.append(col)

    dim = df[macro_cols].drop_duplicates(subset=["year"]).copy()

    # Renombrar si vienen con %
    renames = {
        "nom_interest_rate%": "nom_interest_rate_pct",
        "dk_ann_infl_rate%": "dk_ann_infl_rate_pct",
        "yield_on_mortgage_credit_bonds%": "yield_mortgage_bonds_pct",
    }
    dim = dim.rename(columns={k: v for k, v in renames.items() if k in dim.columns})

    for col in ["nom_interest_rate_pct", "dk_ann_infl_rate_pct", "yield_mortgage_bonds_pct"]:
        if col not in dim.columns:
            dim[col] = None

    dim["macro_nulo"] = dim[["nom_interest_rate_pct", "dk_ann_infl_rate_pct", "yield_mortgage_bonds_pct"]].isna().any(axis=1)
    dim = dim.sort_values("year").reset_index(drop=True)
    dim.insert(0, "macro_id", dim.index + 1)
    logger.info(f"dim_macro: {len(dim):,} filas")
    return dim


def build_fact_transacciones(df: pd.DataFrame, dim_tiempo, dim_geo, dim_viv, dim_macro) -> pd.DataFrame:
    """FACT_TRANSACCIONES — tabla de hechos central con claves foraneas."""
    fact = df.copy()
    fact["date"] = pd.to_datetime(fact["date"], errors="coerce")
    fact["year"] = fact["date"].dt.year
    fact["quarter"] = fact["date"].dt.to_period("Q").astype(str)

    # Join con dim_tiempo
    fact = fact.merge(dim_tiempo[["tiempo_id", "date"]], on="date", how="left")

    # Join con dim_geografia
    geo_key = [c for c in ["zip_code", "city", "region"] if c in fact.columns and c in dim_geo.columns]
    if geo_key:
        fact = fact.merge(dim_geo[["geografia_id"] + geo_key], on=geo_key, how="left")
    else:
        fact["geografia_id"] = None

    # Join con dim_vivienda
    viv_key = [c for c in ["house_type", "sqm", "no_rooms"] if c in fact.columns and c in dim_viv.columns]
    if viv_key:
        fact = fact.merge(dim_viv[["vivienda_id"] + viv_key], on=viv_key, how="left")
    else:
        fact["vivienda_id"] = None

    # Join con dim_macro
    fact = fact.merge(dim_macro[["macro_id", "year"]], on="year", how="left")

    # Columnas de la tabla de hechos
    metric_cols = [c for c in ["purchase_price", "sqm_price", "sqm_price_real",
                                 "sales_type", "purchase_price_outlier",
                                 "sqm_price_outlier", "periodo_preliminar",
                                 "sales_type_valido", "macro_nulo"] if c in fact.columns]

    fk_cols = ["tiempo_id", "geografia_id", "vivienda_id", "macro_id"]
    fact_final = fact[fk_cols + metric_cols].copy()
    fact_final.insert(0, "transaction_id", range(1, len(fact_final) + 1))

    logger.info(f"fact_transacciones: {len(fact_final):,} filas × {len(fact_final.columns)} columnas")
    return fact_final


def parse_args():
    parser = argparse.ArgumentParser(description="Construir Star Schema desde Silver layer")
    parser.add_argument("--config", default="configs/analysis.yaml")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    silver_path = Path(cfg["paths"]["processed_dir"]) / "danish_housing_clean.parquet"
    star_dir = Path(cfg["paths"]["processed_dir"]) / "star_schema"
    star_dir.mkdir(parents=True, exist_ok=True)

    if not silver_path.exists():
        logger.error(f"Silver layer no encontrado: {silver_path}")
        logger.error("Ejecuta primero: python scripts/run_cleaning.py --config configs/analysis.yaml")
        sys.exit(1)

    logger.info(f"Cargando Silver layer desde {silver_path}")
    df = pd.read_parquet(silver_path)

    # Crear sqm_price_real si no existe
    if "sqm_price_real" not in df.columns:
        df["date_tmp"] = pd.to_datetime(df["date"], errors="coerce")
        df["year_tmp"] = df["date_tmp"].dt.year
        price_col = "sqm_price" if "sqm_price" in df.columns else "purchase_price"
        df["sqm_price_real"] = df[price_col] * (1.02) ** (2024 - df["year_tmp"])
        df = df.drop(columns=["date_tmp", "year_tmp"])

    logger.info(f"Registros: {len(df):,}")

    # Construir dimensiones
    dim_tiempo  = build_dim_tiempo(df)
    dim_geo     = build_dim_geografia(df)
    dim_viv     = build_dim_vivienda(df)
    dim_macro   = build_dim_macro(df)

    # Construir tabla de hechos
    fact = build_fact_transacciones(df, dim_tiempo, dim_geo, dim_viv, dim_macro)

    # Guardar todas las tablas
    tablas = {
        "fact_transacciones": fact,
        "dim_tiempo":         dim_tiempo,
        "dim_geografia":      dim_geo,
        "dim_vivienda":       dim_viv,
        "dim_macro":          dim_macro,
    }

    for nombre, tabla in tablas.items():
        out = star_dir / f"{nombre}.csv"
        tabla.to_csv(out, index=False)
        logger.info(f"Guardado: {out} ({len(tabla):,} filas)")

    logger.info(f"\nStar Schema completo en: {star_dir}")
    logger.info("Siguiente paso: subir a GCP con upload_to_gcs.py")


if __name__ == "__main__":
    main()
