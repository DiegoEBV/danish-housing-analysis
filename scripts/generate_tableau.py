"""
generate_tableau.py
Genera marts Gold sintéticos + workbook preliminar de Tableau (.twbx)
para Entrega 3 del proyecto Danish Housing Analysis 1992-2024.
"""


import numpy as np
import pandas as pd

np.random.seed(42)

# ── CONFIG ────────────────────────────────────────────────────────────────────
REGIONS = ["København", "Sjælland", "Syddanmark", "Midtjylland", "Nordjylland"]
HOUSE_TYPES = ["Villa", "Ejerlejlighed", "Fritidshus", "Rækkehus"]

# Base prices (DKK/m², real 2024) por región en 1992Q1
BASE_PRICES = {
    "København":   8_500,
    "Sjælland":    5_200,
    "Syddanmark":  4_800,
    "Midtjylland": 4_600,
    "Nordjylland": 4_200,
}
# Multiplicador por tipología sobre el precio regional
TYPE_MULT = {"Villa": 1.00, "Ejerlejlighed": 1.10, "Fritidshus": 0.85, "Rækkehus": 0.90}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def quarters_range(start="1992Q1", end="2024Q4"):
    periods = pd.period_range(start=start, end=end, freq="Q")
    return [str(p) for p in periods]

def danish_price_multiplier(year_float: float) -> float:
    """
    Índice multiplicador que simula el ciclo de precios danés:
    - Crecimiento gradual 1992-2006 (boom pre-crisis)
    - Pico 2006-2007
    - Caída 2007-2012 (GFC)
    - Recuperación lenta 2012-2015
    - Nuevo boom 2015-2022 (bajos tipos)
    - Corrección 2022-2024 (subida tipos)
    """
    if year_float < 1993:
        return 1.00
    elif year_float < 2007:
        # Boom: de 1.0 a ~3.2
        t = (year_float - 1992) / 15
        return 1.0 + 2.2 * t
    elif year_float < 2009:
        # Crash rápido: de 3.2 a ~2.4
        t = (year_float - 2007) / 2
        return 3.2 - 0.8 * t
    elif year_float < 2012:
        # Caída lenta: de 2.4 a ~2.0
        t = (year_float - 2009) / 3
        return 2.4 - 0.4 * t
    elif year_float < 2015:
        # Estabilización: ~2.0
        return 2.0 + 0.05 * (year_float - 2012)
    elif year_float < 2022:
        # Nuevo boom: de 2.15 a ~4.5
        t = (year_float - 2015) / 7
        return 2.15 + 2.35 * t
    elif year_float < 2024:
        # Corrección: de 4.5 a ~4.1
        t = (year_float - 2022) / 2
        return 4.5 - 0.4 * t
    else:
        return 4.1

def bond_yield(year_float: float) -> float:
    """Rendimiento bonos hipotecarios 30Y daneses simulado."""
    if year_float < 1994:
        return 10.5
    elif year_float < 2000:
        return 10.5 - 3.5 * (year_float - 1994) / 6
    elif year_float < 2009:
        return 6.5 - 1.0 * (year_float - 2000) / 9
    elif year_float < 2013:
        return 5.5 - 1.5 * (year_float - 2009) / 4
    elif year_float < 2020:
        return 2.5 - 1.5 * (year_float - 2013) / 7
    elif year_float < 2022:
        return 1.0 - 0.3 * (year_float - 2020) / 2
    elif year_float < 2023:
        return 0.7 + 3.3 * (year_float - 2022)
    else:
        return 4.0 - 0.5 * (year_float - 2023)

def quarter_to_float(q: str) -> float:
    year = int(q[:4])
    qnum = int(q[5])
    return year + (qnum - 1) * 0.25

# ── MART 1: mart_quarterly_regional_index ────────────────────────────────────
print("Generando mart_quarterly_regional_index...")
rows = []
quarters = quarters_range()
for q in quarters:
    yf = quarter_to_float(q)
    mult = danish_price_multiplier(yf)
    noise = np.random.normal(0, 0.012)
    for region in REGIONS:
        base = BASE_PRICES[region]
        # Regiones fuera de Copenhague tienen ciclos más amortiguados
        regional_amp = 1.0 if region == "København" else 0.82 + np.random.normal(0, 0.02)
        price = base * (1 + (mult - 1) * regional_amp) * (1 + noise)
        rows.append({
            "quarter": q,
            "year": int(q[:4]),
            "region": region,
            "avg_sqm_price_real": round(max(price, 1000), 1),
        })

df_q = pd.DataFrame(rows)
# Calcular índice base 1992
base_prices_df = df_q[df_q["year"] == 1992].groupby("region")["avg_sqm_price_real"].mean().reset_index()
base_prices_df.columns = ["region", "base_year_price"]
df_q = df_q.merge(base_prices_df, on="region")
df_q["regional_index"] = (df_q["avg_sqm_price_real"] / df_q["base_year_price"] * 100).round(2)
REGION_BASE_TRANS = {"København":18000,"Sjælland":10000,"Syddanmark":9000,"Midtjylland":11000,"Nordjylland":7000}

def calc_transactions(row):
    base_t = REGION_BASE_TRANS[row["region"]]
    mult_t = danish_price_multiplier(quarter_to_float(row["quarter"]))
    val = base_t * (0.7 + 0.6 * (mult_t - 1) / 3.5) + np.random.normal(0, 500)
    return max(50, int(val))

df_q["n_transactions"] = df_q.apply(calc_transactions, axis=1)
# Yield de bonos
df_q["yield_mortgage_bonds_pct"] = df_q["quarter"].apply(
    lambda q: round(bond_yield(quarter_to_float(q)) + np.random.normal(0, 0.05), 2)
)
df_q.to_csv("/sessions/fervent-festive-lovelace/mnt/outputs/mart_quarterly_regional_index.csv", index=False)
print(f"  → {len(df_q)} filas")

# ── MART 2: mart_drawdowns ────────────────────────────────────────────────────
print("Generando mart_drawdowns...")
rows2 = []
for q in quarters:
    yf = quarter_to_float(q)
    mult = danish_price_multiplier(yf)
    for region in REGIONS:
        for ht in HOUSE_TYPES:
            base = BASE_PRICES[region] * TYPE_MULT[ht]
            noise = np.random.normal(0, 0.015)
            # Fritidshus es más volátil
            amp = 1.2 if ht == "Fritidshus" else (0.95 if ht == "Villa" else 1.0)
            price = base * (1 + (mult - 1) * amp) * (1 + noise)
            rows2.append({"quarter": q, "region": region, "house_type": ht,
                          "avg_sqm_price_real": round(max(price, 800), 1)})

df_d = pd.DataFrame(rows2)
# Calcular cumulative_max y drawdown
df_d = df_d.sort_values(["region", "house_type", "quarter"])
df_d["cumulative_max"] = df_d.groupby(["region","house_type"])["avg_sqm_price_real"].cummax()
df_d["drawdown_pct"] = ((df_d["avg_sqm_price_real"] - df_d["cumulative_max"]) / df_d["cumulative_max"] * 100).round(2)
df_d.to_csv("/sessions/fervent-festive-lovelace/mnt/outputs/mart_drawdowns.csv", index=False)
print(f"  → {len(df_d)} filas")

# ── MART 3: mart_volatility ───────────────────────────────────────────────────
print("Generando mart_volatility...")
rows3 = []
for ht in HOUSE_TYPES:
    for q in quarters:
        yf = quarter_to_float(q)
        mult = danish_price_multiplier(yf)
        noise = np.random.normal(0, 0.02 if ht == "Fritidshus" else 0.012)
        base = 5_800 * TYPE_MULT[ht]
        price = base * (1 + (mult - 1)) * (1 + noise)
        rows3.append({"quarter": q, "house_type": ht, "avg_sqm_price_real": round(max(price, 800), 1)})

df_v = pd.DataFrame(rows3)
df_v = df_v.sort_values(["house_type", "quarter"])
df_v["pct_change"] = df_v.groupby("house_type")["avg_sqm_price_real"].pct_change() * 100
df_v["volatility_4q"] = df_v.groupby("house_type")["pct_change"].transform(
    lambda x: x.rolling(4, min_periods=2).std()
)
df_v["pct_change"] = df_v["pct_change"].round(2)
df_v["volatility_4q"] = df_v["volatility_4q"].round(3)
df_v.to_csv("/sessions/fervent-festive-lovelace/mnt/outputs/mart_volatility.csv", index=False)
print(f"  → {len(df_v)} filas")

# ── MART 4: mart_macro_correlation ───────────────────────────────────────────
print("Generando mart_macro_correlation...")
macro_rows = []
total_q = df_q.groupby("quarter").agg(
    n_transactions=("n_transactions","sum"),
    year=("year","first")
).reset_index()
total_q["yield_avg"] = total_q["quarter"].apply(
    lambda q: round(bond_yield(quarter_to_float(q)) + np.random.normal(0,0.04), 2)
)
total_q["bond_yield_lag2q"] = total_q["yield_avg"].shift(2).round(2)
total_q["periodo_macro"] = pd.cut(
    total_q["year"],
    bins=[1991,1999,2006,2012,2019,2024],
    labels=["Expansión 90s","Boom Pre-Crisis","GFC 2007-2012","Recuperación","Boom Post-2015"]
)
total_q["volume_bond_corr"] = total_q["bond_yield_lag2q"].rolling(8, min_periods=4).corr(total_q["n_transactions"]).round(3)
total_q.to_csv("/sessions/fervent-festive-lovelace/mnt/outputs/mart_macro_correlation.csv", index=False)
print(f"  → {len(total_q)} filas")

# ── MART 5: mart_transactions_map ────────────────────────────────────────────
print("Generando mart_transactions_map...")
# Muestra de códigos postales reales daneses (representativos)
zip_city_region = [
    ("1050","København K","København"),("1300","København K","København"),
    ("1600","København V","København"),("2000","Frederiksberg","København"),
    ("2100","København Ø","København"),("2200","København N","København"),
    ("2300","København S","København"),("2400","København NV","København"),
    ("2500","Valby","København"),("2600","Glostrup","København"),
    ("2800","Kongens Lyngby","Sjælland"),("3000","Helsingør","Sjælland"),
    ("3400","Hillerød","Sjælland"),("4000","Roskilde","Sjælland"),
    ("4200","Slagelse","Sjælland"),("4600","Køge","Sjælland"),
    ("4700","Næstved","Sjælland"),("4900","Nakskov","Sjælland"),
    ("5000","Odense C","Syddanmark"),("5200","Odense V","Syddanmark"),
    ("5500","Middelfart","Syddanmark"),("6000","Kolding","Syddanmark"),
    ("6400","Sønderborg","Syddanmark"),("6700","Esbjerg","Syddanmark"),
    ("7000","Fredericia","Syddanmark"),("7100","Vejle","Midtjylland"),
    ("7400","Herning","Midtjylland"),("7500","Holstebro","Midtjylland"),
    ("8000","Aarhus C","Midtjylland"),("8200","Aarhus N","Midtjylland"),
    ("8600","Silkeborg","Midtjylland"),("8700","Horsens","Midtjylland"),
    ("8900","Randers C","Midtjylland"),("9000","Aalborg","Nordjylland"),
    ("9200","Aalborg SV","Nordjylland"),("9400","Nørresundby","Nordjylland"),
    ("9700","Brønderslev","Nordjylland"),("9800","Hjørring","Nordjylland"),
    ("9900","Frederikshavn","Nordjylland"),("9990","Skagen","Nordjylland"),
]
map_rows = []
for year in range(1992, 2025):
    yf = float(year)
    mult = danish_price_multiplier(yf)
    for zip_code, city, region in zip_city_region:
        base = BASE_PRICES[region]
        noise = np.random.normal(0, 0.03)
        price = base * (1 + (mult - 1) * (1.0 if region == "København" else 0.82)) * (1 + noise)
        # CPH inner has premium
        if zip_code.startswith("1") or zip_code in ["2000","2100"]:
            price *= 1.25
        n = max(20, int(800 * (0.7 + 0.6*(mult-1)/3.5) + np.random.normal(0, 80)))
        map_rows.append({
            "year": year, "zip_code": zip_code, "city": city,
            "region": region, "avg_sqm_price_real": round(max(price, 1000), 1),
            "n_transactions": n
        })
df_map = pd.DataFrame(map_rows)
df_map.to_csv("/sessions/fervent-festive-lovelace/mnt/outputs/mart_transactions_map.csv", index=False)
print(f"  → {len(df_map)} filas")

print("\n✅ Todos los marts generados.")
df_preview = pd.read_csv("/sessions/fervent-festive-lovelace/mnt/outputs/mart_quarterly_regional_index.csv")
print("Preview done.")
