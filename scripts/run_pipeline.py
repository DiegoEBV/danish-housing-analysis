"""
scripts/run_pipeline.py — Pipeline memory-efficient end-to-end.

Raw parquet -> Silver parquet -> 5 marts Gold -> rebuild .twbx (opcional).

Lee configuracion desde configs/analysis.yaml. Inlinea las reglas P1-P8 y la
generacion de marts en una sola corrida para minimizar peak memory en 1.2M
filas (libera el raw antes de generar marts, recarga solo columnas necesarias).

Uso:
    python scripts/run_pipeline.py --config configs/analysis.yaml
    python scripts/run_pipeline.py --config configs/analysis.yaml --sample 10000
"""
from __future__ import annotations

import argparse
import gc
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from danish_housing.kpis import build_cpi_from_inflation, deflate_sqm_price  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline medallion end-to-end (raw -> Silver -> Gold marts)")
    p.add_argument("--config", default="configs/analysis.yaml")
    p.add_argument("--sample", type=int, default=None, help="Limitar a N filas para smoke test")
    p.add_argument("--skip-twbx", action="store_true", help="No regenerar el .twbx")
    return p.parse_args()


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    raw_path = Path(cfg["paths"]["raw_parquet"])
    silver_path = Path(cfg["paths"]["silver_parquet"])
    gold_dir = Path(cfg["paths"]["gold_dir"])
    marts_dir = Path(cfg["paths"]["marts_dir"])
    Path(cfg["paths"]["twbx_path"])

    silver_path.parent.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    marts_dir.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        logger.error(f"Raw parquet no encontrado: {raw_path}")
        logger.error("Ajusta paths.raw_parquet en configs/analysis.yaml")
        sys.exit(1)

    marts_cfg = cfg.get("marts", {})
    min_price_real = marts_cfg.get("min_price_real", 500)
    drawdown_min_obs = marts_cfg.get("drawdown_min_obs", 5)
    bond_corr_window = marts_cfg.get("bond_corr_window", 8)

    # ══════════════════════════════════════════════════════════════════════
    # FASE A — Cleaning + Silver
    # ══════════════════════════════════════════════════════════════════════
    print("=" * 60)
    print("FASE A: Limpieza P1-P8 -> Silver")
    df = pd.read_parquet(raw_path)
    if args.sample and len(df) > args.sample:
        df = df.head(args.sample).copy()
    logger.info(f"Raw cargado: {len(df):,} filas")

    # P8 renombrar (tolera tanto '%' como '%25' segun como venga el raw)
    rename_map = {}
    for suffix in ("%", "%25"):
        rename_map.update({
            f"nom_interest_rate{suffix}":              "nom_interest_rate_pct",
            f"dk_ann_infl_rate{suffix}":               "dk_ann_infl_rate_pct",
            f"yield_on_mortgage_credit_bonds{suffix}": "yield_mortgage_bonds_pct",
        })
    rename_map["%_change_between_offer_and_purchase"] = "pct_change_offer_purchase"
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # P1 nulos city
    df["city"] = df["city"].fillna("Unknown")

    # P2 flag macro nulos
    df["macro_nulo"] = df[["dk_ann_infl_rate_pct", "yield_mortgage_bonds_pct"]].isna().any(axis=1)

    # P3 ventas no mercado
    invalid_sales = ["family_sale", "other_sale", "auction", "-"]
    df["sales_type_valido"] = ~df["sales_type"].isin(invalid_sales)
    print(f"  P3: {(~df['sales_type_valido']).sum():,} ventas no-mercado")

    # P4 year_build extremos
    df["year_build"] = pd.to_numeric(df["year_build"], errors="coerce")
    df["year_build_flag"] = df["year_build"] < 1800

    # P5 outliers precio
    for col in ["purchase_price", "sqm_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        df[f"{col}_outlier"] = (df[col] < q1 - 3 * iqr) | (df[col] > q3 + 3 * iqr)
        print(f"  P5: {df[col + '_outlier'].sum():,} outliers en {col}")

    # P6 periodo_preliminar
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year.astype("int16")
    df["periodo_preliminar"] = df["year"] < 1995

    # P7 zip_code
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(4)

    # quarter
    df["quarter"] = df["date"].dt.to_period("Q").astype(str)

    # CPI derivado de inflacion anual real del dataset (definicion canonica en kpis.py,
    # compartida con export_marts.py para evitar divergencias en sqm_price_real).
    infl_by_year = (
        df[["year", "dk_ann_infl_rate_pct"]].dropna()
        .groupby("year")["dk_ann_infl_rate_pct"].mean()
        .sort_index()
    )
    cpi = build_cpi_from_inflation(infl_by_year)
    df["sqm_price_real"] = deflate_sqm_price(df, cpi)

    print(f"  sqm_price_real media: {df['sqm_price_real'].mean():.0f} DKK/m²")
    print(f"  Shape Silver: {df.shape}")

    df.to_parquet(silver_path, index=False, compression="snappy")
    sz = os.path.getsize(silver_path) / 1e6
    print(f"  Silver guardado: {sz:.1f} MB en {silver_path}")

    # ══════════════════════════════════════════════════════════════════════
    # FASE B — Marts Gold
    # ══════════════════════════════════════════════════════════════════════
    print("\nFASE B: Generando marts Gold desde Silver")
    del df
    gc.collect()

    COLS_MART = ["quarter", "year", "region", "house_type", "sqm_price_real", "house_id",
                 "sales_type_valido", "purchase_price_outlier", "zip_code", "city",
                 "yield_mortgage_bonds_pct"]
    sv = pd.read_parquet(silver_path, columns=COLS_MART)
    print(f"  Silver recargado ({len(sv):,} filas)")

    sv_c = sv[
        sv["sales_type_valido"]
        & ~sv["purchase_price_outlier"]
        & sv["sqm_price_real"].notna()
        & (sv["sqm_price_real"] > min_price_real)
    ].copy()
    print(f"  Dataset limpio: {len(sv_c):,} filas ({len(sv_c) / len(sv) * 100:.1f}%)")

    def save(d: pd.DataFrame, name: str) -> None:
        for out_dir in (gold_dir, marts_dir):
            d.to_csv(out_dir / name, index=False)
        kb = os.path.getsize(gold_dir / name) // 1024
        print(f"  ✓ {name:<45} {len(d):>6} filas  {kb:>5} KB")

    # ── mart_quarterly_regional_index ──────────────────────────────────
    q = (
        sv_c.groupby(["quarter", "year", "region"], observed=True)
        .agg(
            avg_sqm_price_real=("sqm_price_real", "mean"),
            n_transactions=("house_id", "count"),
            yield_mortgage_bonds_pct=("yield_mortgage_bonds_pct", "mean"),
        )
        .reset_index()
        .sort_values(["region", "quarter"])
    )
    base = q[q["year"] == 1992].groupby("region")["avg_sqm_price_real"].mean().rename("base_year_price")
    q = q.merge(base, on="region", how="left")
    for reg in q[q["base_year_price"].isna()]["region"].unique():
        q.loc[q["region"] == reg, "base_year_price"] = q[q["region"] == reg]["avg_sqm_price_real"].iloc[0]
    q["regional_index"] = (q["avg_sqm_price_real"] / q["base_year_price"] * 100).round(2)
    q[["avg_sqm_price_real", "yield_mortgage_bonds_pct"]] = q[["avg_sqm_price_real", "yield_mortgage_bonds_pct"]].round(1)
    save(q, "mart_quarterly_regional_index.csv")

    # ── mart_drawdowns (filtra n_transactions >= drawdown_min_obs) ──────
    dd = (
        sv_c.groupby(["quarter", "region", "house_type"], observed=True)
        .agg(
            avg_sqm_price_real=("sqm_price_real", "mean"),
            n_transactions=("house_id", "count"),
        )
        .reset_index()
        .sort_values(["region", "house_type", "quarter"])
    )
    n_pre = len(dd)
    dd = dd[dd["n_transactions"] >= drawdown_min_obs].copy()
    print(f"  drawdowns: filtro n_transactions >= {drawdown_min_obs}: {n_pre:,} -> {len(dd):,}")
    dd["cumulative_max"] = dd.groupby(["region", "house_type"], observed=True)["avg_sqm_price_real"].cummax()
    dd["drawdown_pct"] = ((dd["avg_sqm_price_real"] - dd["cumulative_max"]) / dd["cumulative_max"] * 100).round(2)
    dd[["avg_sqm_price_real", "cumulative_max"]] = dd[["avg_sqm_price_real", "cumulative_max"]].round(1)
    save(dd, "mart_drawdowns.csv")

    # ── mart_volatility ────────────────────────────────────────────────
    vol = (
        sv_c.groupby(["quarter", "house_type"], observed=True)
        .agg(avg_sqm_price_real=("sqm_price_real", "mean"))
        .reset_index()
        .sort_values(["house_type", "quarter"])
    )
    vol["pct_change"] = vol.groupby("house_type", observed=True)["avg_sqm_price_real"].pct_change().mul(100).round(2)
    vol["volatility_4q"] = (
        vol.groupby("house_type", observed=True)["pct_change"]
        .transform(lambda x: x.rolling(4, min_periods=2).std())
    ).round(3)
    vol["avg_sqm_price_real"] = vol["avg_sqm_price_real"].round(1)
    save(vol, "mart_volatility.csv")

    # ── mart_macro_correlation ─────────────────────────────────────────
    del sv_c
    gc.collect()
    sv_macro = pd.read_parquet(silver_path, columns=["quarter", "year", "house_id", "yield_mortgage_bonds_pct"])
    mq = (
        sv_macro.groupby("quarter")
        .agg(n_transactions=("house_id", "count"), year=("year", "first"),
             yield_avg=("yield_mortgage_bonds_pct", "mean"))
        .reset_index().sort_values("quarter")
    )
    mq["yield_avg"] = mq["yield_avg"].round(2)
    mq["bond_yield_lag2q"] = mq["yield_avg"].shift(2).round(2)
    mq["periodo_macro"] = pd.cut(
        mq["year"],
        bins=[1991, 1999, 2006, 2012, 2019, 2024],
        labels=["Expansion 90s", "Boom Pre-Crisis", "GFC 2007-2012", "Recovery", "Post-2015 Boom"],
    ).astype(str)
    mq["volume_bond_corr"] = (
        mq["bond_yield_lag2q"].rolling(bond_corr_window, min_periods=4).corr(mq["n_transactions"])
    ).round(3)
    save(mq, "mart_macro_correlation.csv")

    # ── mart_transactions_map ──────────────────────────────────────────
    del sv_macro
    gc.collect()
    sv_map = pd.read_parquet(silver_path, columns=["year", "zip_code", "city", "region",
                                                    "sqm_price_real", "house_id",
                                                    "sales_type_valido", "purchase_price_outlier"])
    sv_map_c = sv_map[sv_map["sales_type_valido"] & ~sv_map["purchase_price_outlier"] & sv_map["sqm_price_real"].notna()]
    mp = (
        sv_map_c.groupby(["year", "zip_code", "city", "region"], observed=True)
        .agg(avg_sqm_price_real=("sqm_price_real", "mean"),
             n_transactions=("house_id", "count"))
        .reset_index()
    )
    mp["avg_sqm_price_real"] = mp["avg_sqm_price_real"].round(1)
    save(mp, "mart_transactions_map.csv")
    del sv_map, sv_map_c, mp
    gc.collect()

    # FASE C — Segmentacion no supervisada (PCA + KMeans + t-SNE) sobre el mart de mapa.
    # Se aisla en try/except para no invalidar el Gold ya escrito si sklearn fallara.
    print("\nFASE C: Segmentacion no supervisada (PCA + KMeans + t-SNE)")
    try:
        from run_segmentation import run as run_segmentation

        run_segmentation(args.config, make_plot=True, marts_dir=marts_dir)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "FASE C omitida (%s). Ejecuta luego: uv run python scripts/run_segmentation.py", exc
        )

    print("\n" + "=" * 60)
    print(f"Pipeline completado. Silver en {silver_path}; Gold en {gold_dir}.")


if __name__ == "__main__":
    main()
