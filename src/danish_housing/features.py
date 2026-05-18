"""
features.py — Feature engineering portado del legacy R0SEWT/Denmark-HousePrices-Analysis.

Solo incluye las funciones auditadas como **clean** en docs/legacy-leakage-audit.md.
Funciones leaky del legacy (`create_size_derived_features`, `apply_target_encoding`,
`create_geographic_aggregated_features`, etc.) NO se portan.

Convencion de causalidad:
- Una feature es clean si y solo si NO usa el target del row actual ni filas futuras.
- Agregaciones regionales usan estrictamente datos de `[year - k, year - 1]`.
- Splits temporales: train 1992-2017, test 2018-2024.

Uso tipico (despues de cleaning):

    from danish_housing.features import build_feature_matrix

    df_silver = pd.read_parquet("data/processed/silver/danish_housing_clean.parquet")
    df_features, feature_names, audit = build_feature_matrix(
        df_silver, target_col="purchase_price"
    )
    # df_features tiene las features + target. audit lista las excluidas y por que.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Constantes anti-leakage ───────────────────────────────────────────────────

# Cualquier columna en este set NO debe entrar al feature matrix bajo ningun
# concepto. Es la lista FORBIDDEN del legacy mas las flags Silver-only.
FORBIDDEN_FEATURE_COLUMNS = {
    # Target y derivadas directas del precio
    "purchase_price", "sqm_price", "sqm_price_real", "sqm_price_nom",
    "price_per_sqm", "price_per_sqm_real", "price_zscore",
    "price_category", "price_per_sqm_x_region", "sqm_x_region",
    "is_premium", "price_deviation_from_median",
    "regional_p90", "regional_median",
    "regional_price_mean", "regional_price_median", "regional_price_std",
    "regional_price_cv", "regional_price_rank",
    "region_target_encoded", "region_count",
    # Diferencias que incluyen precio
    "pct_change_offer_purchase", "%_change_between_offer_and_purchase",
    # Identificadores (no informativos para modelado)
    "house_id", "address",
    # Flags de Silver que son meta-data, no features
    "macro_nulo", "sales_type_valido", "purchase_price_outlier",
    "sqm_price_outlier", "periodo_preliminar", "year_build_flag",
    # Versiones con sufijo legacy de macro vars (usar las _pct ya renombradas)
    "nom_interest_rate%", "dk_ann_infl_rate%", "yield_on_mortgage_credit_bonds%",
    "nom_interest_rate%25", "dk_ann_infl_rate%25", "yield_on_mortgage_credit_bonds%25",
}

ROLLING_FEATURE_COLUMNS = [
    "rolling_regional_mean",
    "rolling_regional_median",
    "rolling_regional_std",
    "rolling_regional_cv",
    "rolling_regional_count",
    "rolling_regional_p90",
]

CRISIS_YEARS = list(range(2007, 2013)) + [2020, 2021, 2022]


# ── Features temporales ───────────────────────────────────────────────────────

def add_date_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Extrae year/month/quarter/season + month_sin/cos, quarter_sin/cos."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["year"] = df[date_col].dt.year.astype("int16")
    df["month"] = df[date_col].dt.month.astype("int8")
    df["quarter_num"] = df[date_col].dt.quarter.astype("int8")
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["quarter_sin"] = np.sin(2 * np.pi * df["quarter_num"] / 4)
    df["quarter_cos"] = np.cos(2 * np.pi * df["quarter_num"] / 4)
    return df


def add_property_age(df: pd.DataFrame) -> pd.DataFrame:
    """property_age = year - year_build. Clipa a [0, 200]."""
    df = df.copy()
    if "year" not in df.columns:
        df["year"] = pd.to_datetime(df["date"]).dt.year
    df["property_age"] = (df["year"] - pd.to_numeric(df["year_build"], errors="coerce")).clip(0, 200)
    return df


def add_crisis_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Binary flag para anios de crisis (GFC + COVID)."""
    df = df.copy()
    df["crisis_period"] = df["year"].isin(CRISIS_YEARS).astype("int8")
    return df


# ── Features fisicas ──────────────────────────────────────────────────────────

def add_size_features(df: pd.DataFrame) -> pd.DataFrame:
    """sqm_per_room, rooms_sqm_ratio, rooms_category, size_category. Sin target."""
    df = df.copy()
    df["sqm"] = pd.to_numeric(df["sqm"], errors="coerce")
    df["no_rooms"] = pd.to_numeric(df["no_rooms"], errors="coerce")

    # Evita division por cero: convertir 0 -> NaN antes del split
    rooms_safe = df["no_rooms"].replace(0, np.nan)
    sqm_safe = df["sqm"].replace(0, np.nan)
    df["sqm_per_room"] = (df["sqm"] / rooms_safe).replace([np.inf, -np.inf], np.nan)
    df["rooms_sqm_ratio"] = (df["no_rooms"] / sqm_safe).replace([np.inf, -np.inf], np.nan)
    df["sqm_per_room_squared"] = df["sqm_per_room"] ** 2
    df["rooms_sqm_interaction"] = df["no_rooms"] * df["sqm"]

    df["rooms_category"] = pd.cut(
        df["no_rooms"], bins=[-np.inf, 2, 4, 6, np.inf],
        labels=["Small", "Medium", "Large", "XLarge"],
    )
    sqm_q = df["sqm"].quantile([0.33, 0.67])
    df["size_category"] = pd.cut(
        df["sqm"], bins=[-np.inf, sqm_q[0.33], sqm_q[0.67], np.inf],
        labels=["Small", "Medium", "Large"],
    )
    return df


# ── Features regionales causales (rolling sobre anios pasados) ────────────────

def _compute_rolling_window_stats(
    region_frame: pd.DataFrame, year_col: str, price_col: str,
    year_ref: int, window_years: int, min_obs: int,
) -> dict[str, Any]:
    """Estadisticos sobre `[year_ref - window_years, year_ref - 1]` (excluye `year_ref`)."""
    mask = (region_frame[year_col] >= year_ref - window_years) & (region_frame[year_col] <= year_ref - 1)
    window_prices = region_frame.loc[mask, price_col].dropna()
    obs = int(window_prices.shape[0])

    if obs < min_obs:
        return {c: np.nan for c in ROLLING_FEATURE_COLUMNS} | {"rolling_regional_count": obs}

    mean_v = float(window_prices.mean())
    std_v = float(window_prices.std(ddof=1)) if obs > 1 else 0.0
    return {
        "rolling_regional_mean": mean_v,
        "rolling_regional_median": float(window_prices.median()),
        "rolling_regional_std": std_v,
        "rolling_regional_cv": std_v / mean_v if mean_v else np.nan,
        "rolling_regional_count": obs,
        "rolling_regional_p90": float(window_prices.quantile(0.9)),
    }


def add_rolling_regional_features(
    df: pd.DataFrame, region_col: str = "region", price_col: str = "purchase_price",
    year_col: str = "year", window_years: int = 12, min_obs: int = 30,
) -> pd.DataFrame:
    """
    Agrega 6 estadisticos regionales causales por (region, year).

    Para cada (region, year_ref) computa mean/median/std/cv/count/p90 de
    `price_col` sobre transacciones en la misma region en
    `[year_ref - window_years, year_ref - 1]`. El row actual y futuros NO entran.

    Si la ventana tiene menos de `min_obs` observaciones, retorna NaN.
    """
    required = {region_col, price_col, year_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"add_rolling_regional_features: columnas faltantes {sorted(missing)}")

    logger.info(f"Rolling regional features: ventana={window_years}a, min_obs={min_obs}")

    df_out = df.copy()
    # Limpieza previa (idempotente)
    df_out = df_out.drop(columns=[c for c in ROLLING_FEATURE_COLUMNS if c in df_out.columns])

    pairs = df_out[[region_col, year_col]].dropna().drop_duplicates().sort_values([region_col, year_col])

    records: list[dict[str, Any]] = []
    for region_value, region_frame in df_out[[region_col, year_col, price_col]].groupby(region_col, observed=True):
        region_frame = region_frame.sort_values(year_col)
        years_in_region = pairs.loc[pairs[region_col] == region_value, year_col].astype(int).tolist()
        for y in years_in_region:
            stats = _compute_rolling_window_stats(region_frame, year_col, price_col, y, window_years, min_obs)
            records.append({region_col: region_value, year_col: int(y), **stats})

    rolling = pd.DataFrame.from_records(records)
    df_out = df_out.merge(rolling, on=[region_col, year_col], how="left")

    n_nan = int(df_out["rolling_regional_mean"].isna().sum())
    logger.info(f"Rolling aplicado a {len(df_out):,} filas; {n_nan:,} NaN (sin ventana valida)")
    return df_out


def add_causal_derived_features(
    df: pd.DataFrame, target_col: str = "purchase_price",
) -> pd.DataFrame:
    """
    Features derivadas DE LA VENTANA CAUSAL (no del row actual):
    - is_premium_causal: 1 si target > rolling_regional_p90
    - price_deviation_from_rolling_median: target - rolling_regional_median

    Estas SI usan el target del row, pero la comparacion es contra ventana
    pasada — equivale a "es este precio anomalo respecto a la historia de la
    region?". Es informativo y causal porque la ventana es pasada.

    ADVERTENCIA: estas features INCLUYEN el target del row. Solo usar como
    features de **diagnostico** para entender outliers. Si entran al feature
    matrix de modelado, el modelo puede recuperar el target trivialmente
    sumando rolling_regional_median + price_deviation_from_rolling_median.
    Por defecto el feature matrix las EXCLUYE.
    """
    df = df.copy()
    if "rolling_regional_p90" not in df.columns or "rolling_regional_median" not in df.columns:
        raise ValueError("Llama primero a add_rolling_regional_features().")

    p90 = df["rolling_regional_p90"]
    median = df["rolling_regional_median"]

    df["is_premium_causal"] = np.where(p90.notna(), (df[target_col] > p90).astype(float), np.nan)
    df["price_deviation_from_rolling_median"] = df[target_col] - median
    return df


# ── Interacciones (todas sobre features ya clean) ─────────────────────────────

def add_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Interacciones simples entre features fisicas y house_type.
    Requiere que las one-hot de house_type ya esten presentes.
    """
    df = df.copy()
    for ht in ("Villa", "Apartment", "Ejerlejlighed", "Fritidshus", "Raekkehus"):
        ohc = f"house_type_{ht}"
        if ohc in df.columns and "property_age" in df.columns:
            df[f"age_x_{ht.lower()}"] = df["property_age"] * df[ohc]
    return df


# ── Encoding categorico (no-target) ───────────────────────────────────────────

def encode_categoricals(
    df: pd.DataFrame, cols: list[str], drop_first: bool = True,
) -> pd.DataFrame:
    """One-hot encoding seguro (sin target). drop_first=True evita multicolinealidad."""
    df = df.copy()
    present = [c for c in cols if c in df.columns]
    if not present:
        return df
    return pd.get_dummies(df, columns=present, drop_first=drop_first, dtype="int8")


def add_frequency_encoding(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Frequency encoding (count del valor en el dataset) para categoricas de
    alta cardinalidad como city o zip_code. Convierte 1 categorica en 1
    feature numerica en vez de explosion one-hot. No usa target.

    Crea columna `{col}_frequency` por cada cole de cols.
    """
    df = df.copy()
    for col in cols:
        if col not in df.columns:
            continue
        freq = df[col].value_counts(dropna=False).to_dict()
        df[f"{col}_frequency"] = df[col].map(freq).astype("int32")
    return df


# ── Pipeline completo + guardas anti-leak ─────────────────────────────────────

def build_feature_matrix(
    df: pd.DataFrame,
    target_col: str = "purchase_price",
    window_years: int = 12,
    min_obs_per_window: int = 30,
    include_causal_derived: bool = False,
    use_log_target: bool = True,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    """
    Construye la matriz de features lista para modelado, con guardas anti-leak.

    Args:
        df: Silver layer (output de run_cleaning_pipeline).
        target_col: columna objetivo (default: purchase_price nominal).
        window_years, min_obs_per_window: parametros de rolling regional.
        include_causal_derived: si True incluye is_premium_causal y
            price_deviation_from_rolling_median (cuidado: ver docstring).
            Default False — son utiles para diagnostico, no para modelado.
        use_log_target: si True agrega log_target = log1p(target). NO usar
            este como target sin back-transformar al reportar metricas.

    Returns:
        df_final: filas x (features + target [+ log_target]).
        feature_names: lista de columnas en df_final que SON features (no target).
        audit: dict con metadatos: excluded_cols, leakage_check_passed, n_rows, etc.
    """
    # 1) Features temporales y fisicas
    df = add_date_features(df)
    df = add_property_age(df)
    df = add_crisis_flag(df)
    df = add_size_features(df)

    # 2) Features regionales causales (lentas)
    df = add_rolling_regional_features(
        df, price_col=target_col, window_years=window_years, min_obs=min_obs_per_window,
    )
    if include_causal_derived:
        df = add_causal_derived_features(df, target_col=target_col)

    # 3) Encoding categorico:
    #    - One-hot SOLO para baja cardinalidad (region: 5, house_type: 4, *_category: 3-4)
    #    - Frequency encoding para alta cardinalidad (city: ~100s, zip_code: ~4000)
    #    El legacy excluye city/zip_code del feature set; aqui los conservamos como
    #    senal de "densidad de transacciones en esa zona", que es informativa y no
    #    leaky.
    df = add_frequency_encoding(df, cols=["city", "zip_code", "sales_type"])
    df = encode_categoricals(df, cols=["region", "house_type", "rooms_category", "size_category"])

    # 4) Interacciones (despues de one-hot)
    df = add_interactions(df)

    # 5) Identificar features candidatas (solo numericas, sin strings/categoricas)
    excluded_for_audit: list[str] = []
    feature_cols: list[str] = []
    for col in df.columns:
        if col == target_col:
            continue
        if col in FORBIDDEN_FEATURE_COLUMNS:
            excluded_for_audit.append(col)
            continue
        dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
            feature_cols.append(col)
        elif pd.api.types.is_bool_dtype(dtype):
            # Booleanas (e.g. de one-hot int8) son OK como numericas
            feature_cols.append(col)
        else:
            # object / string / datetime / categorical / etc. → fuera
            excluded_for_audit.append(col)

    # 6) Guarda anti-leak final
    leak_check = FORBIDDEN_FEATURE_COLUMNS & set(feature_cols)
    if leak_check:
        raise AssertionError(
            f"Anti-leak guard: columnas prohibidas en feature_cols: {sorted(leak_check)}"
        )

    df_final = df[feature_cols + [target_col]].copy()
    if use_log_target:
        df_final["log_target"] = np.log1p(df_final[target_col])

    audit = {
        "n_rows": len(df_final),
        "n_features": len(feature_cols),
        "target_col": target_col,
        "use_log_target": use_log_target,
        "include_causal_derived": include_causal_derived,
        "excluded_cols": excluded_for_audit,
        "leakage_check_passed": True,
        "rolling_window_years": window_years,
        "rolling_min_obs": min_obs_per_window,
    }

    logger.info(
        f"Feature matrix: {len(df_final):,} filas x {len(feature_cols)} features. "
        f"Excluidas: {len(excluded_for_audit)}. Anti-leak: PASS."
    )

    return df_final, feature_cols, audit


# ── Split temporal (clean) ────────────────────────────────────────────────────

def temporal_train_test_split(
    df: pd.DataFrame, year_col: str = "year", train_end: int = 2017, test_start: int = 2018,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split temporal estricto. Train: anios <= train_end. Test: anios >= test_start.

    NO mezclar con train_test_split aleatorio en datos temporales — leakea
    informacion del futuro al train.
    """
    train = df[df[year_col] <= train_end].copy()
    test = df[df[year_col] >= test_start].copy()
    logger.info(f"Split temporal: train {len(train):,} filas (<= {train_end}), test {len(test):,} filas (>= {test_start})")
    return train, test
