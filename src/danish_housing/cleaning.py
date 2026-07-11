"""
cleaning.py — Reglas de limpieza del dataset (TB2).

Implementa los 8 problemas de calidad identificados en el perfilado:
  P1: Nulos en city
  P2: Nulos en variables macro (período 2023–2024)
  P3: sales_type no clasificable
  P4: year_build con valores extremos (< 1800)
  P5: Outliers en purchase_price y sqm_price (IQR ×3)
  P6: Registros 1992–1994 con menor completitud
  P7: zip_code como int64 → string con zfill(4)
  P8: Columnas con %25 en el nombre → renombrar
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ── Bitácora de transformaciones ──────────────────────────────────────────────

def _log(
    bitacora: list[dict[str, Any]],
    problema_id: str,
    columna: str,
    tipo_problema: str,
    accion: str,
    n_afectados: int,
    dato_original: str,
    dato_transformado: str,
) -> None:
    entry = {
        "problema_id": problema_id,
        "columna": columna,
        "tipo_problema": tipo_problema,
        "accion": accion,
        "n_afectados": n_afectados,
        "dato_original": dato_original,
        "dato_transformado": dato_transformado,
    }
    bitacora.append(entry)
    logger.info(f"{problema_id} | {columna} | {n_afectados} afectados | {accion}")


# ── Funciones de limpieza ─────────────────────────────────────────────────────

def fix_city_nulls(df: pd.DataFrame, bitacora: list) -> pd.DataFrame:
    """P1: Imputa nulos en 'city' con 'Unknown'."""
    n = df["city"].isna().sum()
    df["city"] = df["city"].fillna("Unknown")
    _log(bitacora, "P1", "city", "Nulos", "Imputar con Unknown", n, "NaN", "Unknown")
    return df


def flag_macro_nulls(df: pd.DataFrame, bitacora: list) -> pd.DataFrame:
    """P2: Crea flag macro_nulo para registros con variables macro ausentes."""
    macro_cols = [c for c in df.columns if "infl" in c or "yield" in c]
    n = df[macro_cols].isna().any(axis=1).sum()
    df["macro_nulo"] = df[macro_cols].isna().any(axis=1)
    _log(
        bitacora, "P2", str(macro_cols),
        "Nulos macro (2023–2024)",
        "Crear flag macro_nulo=True; no imputar",
        n, "NaN", "Flag macro_nulo=True",
    )
    return df


def flag_invalid_sales(
    df: pd.DataFrame,
    bitacora: list,
    invalid_types: list[str] | None = None,
) -> pd.DataFrame:
    """P3: Marca sales_type no clasificables como sales_type_valido=False."""
    if invalid_types is None:
        # Vocabulario real del dataset Kaggle (verificado en value_counts de TB2):
        # regular_sale (mercado) vs family_sale / other_sale / auction / "-" (no-mercado).
        # "Familiehandel" (danes) NO existe en la data — antes sub-flageaba ~11.6%.
        invalid_types = ["-", "family_sale", "other_sale", "auction"]
    if "sales_type" not in df.columns:
        return df
    mask = df["sales_type"].isin(invalid_types)
    n = mask.sum()
    df["sales_type_valido"] = ~mask
    _log(
        bitacora, "P3", "sales_type",
        "Valor no clasificable",
        "Marcar sales_type_valido=False",
        n, str(invalid_types), "sales_type_valido=False",
    )
    return df


def flag_old_year_build(
    df: pd.DataFrame,
    bitacora: list,
    min_year: int = 1800,
) -> pd.DataFrame:
    """P4: Marca year_build < min_year como year_build_flag=True."""
    if "year_build" not in df.columns:
        return df
    df["year_build"] = pd.to_numeric(df["year_build"], errors="coerce")
    mask = df["year_build"] < min_year
    n = mask.sum()
    df["year_build_flag"] = mask
    _log(
        bitacora, "P4", "year_build",
        "Valor atípico extremo",
        f"Marcar year_build_flag=True para year_build < {min_year}",
        n, f"year_build < {min_year}", "year_build_flag=True",
    )
    return df


def flag_price_outliers(
    df: pd.DataFrame,
    bitacora: list,
    price_cols: list[str] | None = None,
    iqr_multiplier: float = 3.0,
) -> pd.DataFrame:
    """P5: Marca outliers en columnas de precio usando IQR × multiplier."""
    if price_cols is None:
        price_cols = ["purchase_price", "sqm_price"]

    for col in price_cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - iqr_multiplier * iqr
        upper = q3 + iqr_multiplier * iqr
        mask = (df[col] < lower) | (df[col] > upper)
        n = mask.sum()
        df[f"{col}_outlier"] = mask
        _log(
            bitacora, "P5", col,
            f"Outlier extremo (IQR ×{iqr_multiplier})",
            f"Marcar {col}_outlier=True",
            n, f"< {lower:,.0f} o > {upper:,.0f}", f"{col}_outlier=True",
        )
    return df


def flag_preliminary_period(
    df: pd.DataFrame,
    bitacora: list,
    before_year: int = 1995,
) -> pd.DataFrame:
    """P6: Marca registros anteriores a before_year como periodo_preliminar=True."""
    if "date" not in df.columns:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    mask = df["date"].dt.year < before_year
    n = mask.sum()
    df["periodo_preliminar"] = mask
    _log(
        bitacora, "P6", "date",
        "Menor completitud histórica",
        f"Marcar periodo_preliminar=True para año < {before_year}",
        n, f"año < {before_year}", "periodo_preliminar=True",
    )
    return df


def fix_zip_code(df: pd.DataFrame, bitacora: list, pad: int = 4) -> pd.DataFrame:
    """P7: Convierte zip_code a string con zfill(pad)."""
    if "zip_code" not in df.columns:
        return df
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(pad)
    _log(
        bitacora, "P7", "zip_code",
        "Tipo incorrecto",
        f"Convertir a string con zfill({pad})",
        len(df), "int64", f"str con zfill({pad})",
    )
    return df


def rename_rate_columns(
    df: pd.DataFrame,
    bitacora: list,
    renames: dict[str, str] | None = None,
) -> pd.DataFrame:
    """P8: Renombra columnas macro a nombres limpios. Tolera sufijo `%` o `%25`.

    El parquet de Kaggle viene con `%` (single percent); el CSV viene URL-encoded
    con `%25`. Ambas variantes se renombran al mismo nombre canonico `_pct`.
    """
    if renames is None:
        canonical = {
            "nom_interest_rate": "nom_interest_rate_pct",
            "dk_ann_infl_rate": "dk_ann_infl_rate_pct",
            "yield_on_mortgage_credit_bonds": "yield_mortgage_bonds_pct",
        }
        renames = {}
        for base, target in canonical.items():
            for suffix in ("%", "%25"):
                renames[f"{base}{suffix}"] = target
        # Ademas: la columna `%_change_between_offer_and_purchase` se renombra a un nombre limpio
        renames["%_change_between_offer_and_purchase"] = "pct_change_offer_purchase"
    actual = {k: v for k, v in renames.items() if k in df.columns}
    if actual:
        df = df.rename(columns=actual)
        _log(
            bitacora, "P8", str(list(actual.keys())),
            "Nombre de columna con encoding URL/% no estandar",
            "Renombrar a nombres limpios (sufijo _pct)",
            0, str(list(actual.keys())), str(list(actual.values())),
        )
    return df


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_cleaning_pipeline(
    df_raw: pd.DataFrame,
    cfg: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aplica todas las reglas de limpieza P1–P8 en orden.

    Returns:
        df_clean: DataFrame con flags y transformaciones aplicadas
        bitacora: DataFrame con registro de todas las transformaciones
    """
    if cfg is None:
        cfg = {}

    df = df_raw.copy()
    bitacora: list[dict] = []

    df = fix_city_nulls(df, bitacora)
    df = flag_macro_nulls(df, bitacora)
    df = flag_invalid_sales(df, bitacora, cfg.get("invalid_sales_types"))
    df = flag_old_year_build(df, bitacora, cfg.get("year_build_min", 1800))
    df = flag_price_outliers(
        df, bitacora,
        cfg.get("price_columns"),
        cfg.get("iqr_multiplier", 3.0),
    )
    df = flag_preliminary_period(
        df, bitacora, cfg.get("preliminary_period_before", 1995)
    )
    df = fix_zip_code(df, bitacora, cfg.get("zip_code_pad", 4))
    df = rename_rate_columns(df, bitacora, cfg.get("column_renames"))

    df_bitacora = pd.DataFrame(bitacora)
    logger.info(f"Limpieza completa: {len(df):,} filas, {len(df.columns)} columnas")
    return df, df_bitacora
