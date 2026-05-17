"""
run_pipeline_v2.py — Memory-efficient pipeline
Raw → Silver parquet → 5 Gold marts → rebuild .twbx
"""
import sys, os, zipfile, csv, gc
import pandas as pd
import numpy as np

BASE   = "/sessions/fervent-festive-lovelace/mnt/danish-housing-analysis"
RAW    = f"{BASE}/data/raw/DKHousingPrices.parquet"
SILVER = f"{BASE}/data/processed/silver/danish_housing_clean.parquet"
GOLD   = f"{BASE}/data/processed/gold"
TDIR   = f"{BASE}/tableau/marts"
WB_NAME = "danish_housing_exploratorio"
TWBX   = f"{BASE}/tableau/{WB_NAME}.twbx"

os.makedirs(GOLD, exist_ok=True)
os.makedirs(TDIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════
# FASE A — Cleaning + Silver (liberar raw al terminar)
# ══════════════════════════════════════════════════════════════════════
print("="*60)
print("FASE A: Limpieza P1-P8 → Silver")
df = pd.read_parquet(RAW)

# P8 renombrar
df = df.rename(columns={
    "nom_interest_rate%":              "nom_interest_rate_pct",
    "dk_ann_infl_rate%":               "dk_ann_infl_rate_pct",
    "yield_on_mortgage_credit_bonds%": "yield_mortgage_bonds_pct",
    "%_change_between_offer_and_purchase": "pct_change_offer_purchase",
})

# P1 nulos city
df["city"] = df["city"].fillna("Unknown")

# P2 flag macro nulos
df["macro_nulo"] = df[["dk_ann_infl_rate_pct","yield_mortgage_bonds_pct"]].isna().any(axis=1)

# P3 ventas no mercado
invalid_sales = ["family_sale","other_sale","auction","-"]
df["sales_type_valido"] = ~df["sales_type"].isin(invalid_sales)
print(f"  P3: {(~df['sales_type_valido']).sum():,} ventas no-mercado")

# P4 year_build extremos
df["year_build"] = pd.to_numeric(df["year_build"], errors="coerce")
df["year_build_flag"] = df["year_build"] < 1800

# P5 outliers precio
for col in ["purchase_price","sqm_price"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    q1, q3 = df[col].quantile([0.25,0.75])
    iqr = q3 - q1
    df[f"{col}_outlier"] = (df[col] < q1-3*iqr)|(df[col] > q3+3*iqr)
    print(f"  P5: {df[col+'_outlier'].sum():,} outliers en {col}")

# P6 periodo_preliminar
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year.astype("int16")
df["periodo_preliminar"] = df["year"] < 1995

# P7 zip_code
df["zip_code"] = df["zip_code"].astype(str).str.zfill(4)

# quarter
df["quarter"] = df["date"].dt.to_period("Q").astype(str)

# CPI desde inflación anual real del dataset
infl_by_year = (
    df[["year","dk_ann_infl_rate_pct"]].dropna()
    .groupby("year")["dk_ann_infl_rate_pct"].mean()
    .sort_index()
)
cpi = {}
cpi[int(infl_by_year.index.max())] = 100.0
for yr in sorted(infl_by_year.index, reverse=True)[1:]:
    yr, yp1 = int(yr), int(yr)+1
    rate = infl_by_year.get(yp1, 2.0)
    cpi[yr] = cpi[yp1] / (1 + rate/100)
for yr in range(1992, min(cpi.keys())):
    cpi[yr] = cpi[min(cpi.keys())] / (1.02 ** (min(cpi.keys()) - yr))

df["cpi_year"] = df["year"].map(cpi)
df["sqm_price_real"] = (df["sqm_price"] * 100.0 / df["cpi_year"]).round(2)
df = df.drop(columns=["cpi_year"])

print(f"  sqm_price_real media: {df['sqm_price_real'].mean():.0f} DKK/m²")
print(f"  Shape Silver: {df.shape}")

# Guardar Silver con compresión para reducir memoria pico
df.to_parquet(SILVER, index=False, compression="snappy")
sz = os.path.getsize(SILVER)/1e6
print(f"  Silver guardado: {sz:.1f} MB")

# ══════════════════════════════════════════════════════════════════════
# FASE B — Marts Gold (recargar solo columnas necesarias)
# ══════════════════════════════════════════════════════════════════════
print("\nFASE B: Generando marts Gold desde Silver")
del df; gc.collect()

# Leer Silver con solo las columnas necesarias
COLS_MART = ["quarter","year","region","house_type","sqm_price_real","house_id",
             "sales_type_valido","purchase_price_outlier","zip_code","city",
             "yield_mortgage_bonds_pct"]
sv = pd.read_parquet(SILVER, columns=COLS_MART)
print(f"  Silver recargado ({len(sv):,} filas)")

# Dataset limpio (precios de mercado, sin outliers)
sv_c = sv[
    sv["sales_type_valido"] &
    ~sv["purchase_price_outlier"] &
    sv["sqm_price_real"].notna() &
    (sv["sqm_price_real"] > 500)
].copy()
print(f"  Dataset limpio: {len(sv_c):,} filas ({len(sv_c)/len(sv)*100:.1f}%)")

def save(df, name):
    for d in [GOLD, TDIR]:
        df.to_csv(f"{d}/{name}", index=False)
    r = len(df)
    kb = os.path.getsize(f"{GOLD}/{name}")//1024
    print(f"  ✓ {name:<45} {r:>6} filas  {kb:>5} KB")

# ── mart_quarterly_regional_index ─────────────────────────────────────
q = (
    sv_c.groupby(["quarter","year","region"], observed=True)
    .agg(
        avg_sqm_price_real=("sqm_price_real","mean"),
        n_transactions=("house_id","count"),
        yield_mortgage_bonds_pct=("yield_mortgage_bonds_pct","mean"),
    )
    .reset_index()
    .sort_values(["region","quarter"])
)
base = q[q["year"]==1992].groupby("region")["avg_sqm_price_real"].mean().rename("base_year_price")
q = q.merge(base, on="region", how="left")
# fallback: primer trimestre disponible por región
for reg in q[q["base_year_price"].isna()]["region"].unique():
    q.loc[q["region"]==reg,"base_year_price"] = q[q["region"]==reg]["avg_sqm_price_real"].iloc[0]
q["regional_index"] = (q["avg_sqm_price_real"]/q["base_year_price"]*100).round(2)
q[["avg_sqm_price_real","yield_mortgage_bonds_pct"]] = q[["avg_sqm_price_real","yield_mortgage_bonds_pct"]].round(1)
save(q, "mart_quarterly_regional_index.csv")

# ── mart_drawdowns ─────────────────────────────────────────────────────
dd = (
    sv_c.groupby(["quarter","region","house_type"], observed=True)
    .agg(avg_sqm_price_real=("sqm_price_real","mean"))
    .reset_index()
    .sort_values(["region","house_type","quarter"])
)
dd["cumulative_max"] = dd.groupby(["region","house_type"], observed=True)["avg_sqm_price_real"].cummax()
dd["drawdown_pct"] = ((dd["avg_sqm_price_real"]-dd["cumulative_max"])/dd["cumulative_max"]*100).round(2)
dd[["avg_sqm_price_real","cumulative_max"]] = dd[["avg_sqm_price_real","cumulative_max"]].round(1)
save(dd, "mart_drawdowns.csv")

# ── mart_volatility ────────────────────────────────────────────────────
vol = (
    sv_c.groupby(["quarter","house_type"], observed=True)
    .agg(avg_sqm_price_real=("sqm_price_real","mean"))
    .reset_index()
    .sort_values(["house_type","quarter"])
)
vol["pct_change"] = vol.groupby("house_type", observed=True)["avg_sqm_price_real"].pct_change().mul(100).round(2)
vol["volatility_4q"] = (
    vol.groupby("house_type", observed=True)["pct_change"]
    .transform(lambda x: x.rolling(4, min_periods=2).std())
).round(3)
vol["avg_sqm_price_real"] = vol["avg_sqm_price_real"].round(1)
save(vol, "mart_volatility.csv")

# ── mart_macro_correlation ─────────────────────────────────────────────
del sv_c; gc.collect()
sv_macro = pd.read_parquet(SILVER, columns=["quarter","year","house_id","yield_mortgage_bonds_pct"])
mq = (
    sv_macro.groupby("quarter")
    .agg(n_transactions=("house_id","count"), year=("year","first"),
         yield_avg=("yield_mortgage_bonds_pct","mean"))
    .reset_index().sort_values("quarter")
)
mq["yield_avg"] = mq["yield_avg"].round(2)
mq["bond_yield_lag2q"] = mq["yield_avg"].shift(2).round(2)
mq["periodo_macro"] = pd.cut(
    mq["year"],
    bins=[1991,1999,2006,2012,2019,2024],
    labels=["Expansion 90s","Boom Pre-Crisis","GFC 2007-2012","Recovery","Post-2015 Boom"]
).astype(str)
mq["volume_bond_corr"] = (
    mq["bond_yield_lag2q"].rolling(8, min_periods=4).corr(mq["n_transactions"])
).round(3)
save(mq, "mart_macro_correlation.csv")

# ── mart_transactions_map ──────────────────────────────────────────────
del sv_macro; gc.collect()
sv_map = pd.read_parquet(SILVER, columns=["year","zip_code","city","region",
                                           "sqm_price_real","house_id",
                                           "sales_type_valido","purchase_price_outlier"])
sv_map_c = sv_map[sv_map["sales_type_valido"] & ~sv_map["purchase_price_outlier"] & sv_map["sqm_price_real"].notna()]
mp = (
    sv_map_c.groupby(["year","zip_code","city","region"], observed=True)
    .agg(avg_sqm_price_real=("sqm_price_real","mean"),
         n_transactions=("house_id","count"))
    .reset_index()
)
mp["avg_sqm_price_real"] = mp["avg_sqm_price_real"].round(1)
save(mp, "mart_transactions_map.csv")

print("\n" + "="*60)
print("Pipeline completado exitosamente.")
