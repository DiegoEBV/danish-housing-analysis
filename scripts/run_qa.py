"""
scripts/run_qa.py

QA técnico automatizado de la capa Gold (Entrega 6 / TF).

Verifica en una sola corrida:
  A. Presencia y esquema de todos los marts esperados.
  B. Integridad de datos (rangos, nulos, integridad referencial entre marts).
  C. Reconciliación: las cifras citadas en el informe / resumen ejecutivo / dashboard
     se re-derivan de los marts y deben coincidir (tolerancia numérica).

Cada chequeo imprime PASS/FAIL. El script sale con código != 0 si algún chequeo falla,
por lo que puede usarse como quality gate en CI o antes de una entrega.

Uso:
    uv run python scripts/run_qa.py
"""

import sys
from pathlib import Path

import pandas as pd

MARTS = Path("data/marts")

# Esquema esperado por mart (columnas mínimas)
SCHEMA = {
    "mart_quarterly_regional_index": ["quarter", "region", "regional_index", "avg_sqm_price_real"],
    "mart_drawdowns": ["quarter", "region", "house_type", "drawdown_pct", "n_transactions"],
    "mart_volatility": ["quarter", "house_type", "volatility_4q"],
    "mart_macro_correlation": ["quarter", "n_transactions", "volume_bond_corr"],
    "mart_transactions_map": ["year", "zip_code", "region", "avg_sqm_price_real", "n_transactions"],
    "mart_model_comparison": ["model", "test_r2", "test_mae", "test_mape_pct"],
    "mart_zip_segments": ["zip_code", "region", "cluster", "cluster_label", "pca1", "tsne1"],
    "mart_segment_profiles": ["cluster", "cluster_label", "n_zips", "price_level"],
    "mart_segmentation_validation": ["k", "silhouette", "stability_ari", "eta2_risk", "k_cientifico", "k_operativo"],
    "mart_rfm_segments": ["zip_code", "region", "R", "F", "M", "RFM_score", "rfm_segmento"],
}

_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, bool(ok), detail))


def approx(a: float, b: float, tol: float) -> bool:
    return abs(float(a) - float(b)) <= tol


def load(mart: str) -> pd.DataFrame:
    dtype = {"zip_code": str} if mart in ("mart_transactions_map", "mart_zip_segments") else None
    return pd.read_csv(MARTS / f"{mart}.csv", dtype=dtype)


def main() -> int:
    # ── A. Presencia + esquema ────────────────────────────────────────────────
    marts = {}
    for mart, cols in SCHEMA.items():
        path = MARTS / f"{mart}.csv"
        if not path.exists():
            check(f"A · existe {mart}.csv", False, "archivo no encontrado")
            continue
        df = load(mart)
        marts[mart] = df
        faltan = [c for c in cols if c not in df.columns]
        check(f"A · esquema {mart}", not faltan and len(df) > 0,
              f"faltan {faltan}" if faltan else f"{len(df)} filas OK")

    # ── B. Integridad de datos ────────────────────────────────────────────────
    if "mart_drawdowns" in marts:
        dd = marts["mart_drawdowns"]
        check("B · drawdown_pct en [-100, 0]",
              dd["drawdown_pct"].between(-100, 0.001).all(),
              f"min={dd.drawdown_pct.min():.2f} max={dd.drawdown_pct.max():.2f}")
        check("B · drawdowns sin nulos en claves",
              dd[["quarter", "region", "house_type", "drawdown_pct"]].notna().all().all())

    if "mart_quarterly_regional_index" in marts:
        ri = marts["mart_quarterly_regional_index"]
        check("B · regional_index > 0", (ri["regional_index"] > 0).all(),
              f"min={ri.regional_index.min():.2f}")

    if "mart_zip_segments" in marts and "mart_transactions_map" in marts:
        seg, mp = marts["mart_zip_segments"], marts["mart_transactions_map"]
        orphan = set(seg["zip_code"]) - set(mp["zip_code"])
        check("B · integridad referencial (zips segmentados ⊆ mapa)", not orphan,
              f"{len(orphan)} zips huérfanos" if orphan else "0 huérfanos")
        check("B · segmentos sin nulos", seg.notna().all().all())

    if "mart_zip_segments" in marts and "mart_segment_profiles" in marts:
        seg, prof = marts["mart_zip_segments"], marts["mart_segment_profiles"]
        check("B · clusters segmentos == perfiles",
              set(seg["cluster"].unique()) == set(prof["cluster"].unique()),
              f"segmentos={sorted(seg.cluster.unique())} perfiles={sorted(prof.cluster.unique())}")
        check("B · suma n_zips de perfiles == filas de segmentos",
              int(prof["n_zips"].sum()) == len(seg),
              f"{int(prof.n_zips.sum())} vs {len(seg)}")

    # ── C. Reconciliación con cifras del informe / dashboard ──────────────────
    if "mart_drawdowns" in marts:
        dd = marts["mart_drawdowns"]
        worst = dd.loc[dd["drawdown_pct"].idxmin()]
        check("C · peor drawdown = -92.1% (Bornholm/Apartment/2018Q3)",
              approx(worst["drawdown_pct"], -92.11, 0.1)
              and worst["region"] == "Bornholm" and worst["house_type"] == "Apartment",
              f"{worst['region']}/{worst['house_type']}/{worst['quarter']} = {worst['drawdown_pct']:.2f}%")
        # ranking de drawdown por tipología (informe: Apartment peor, Villa mejor)
        rank = dd.groupby("house_type")["drawdown_pct"].min().sort_values()
        check("C · ranking drawdown: Apartment peor, Villa mejor",
              rank.index[0] == "Apartment" and rank.index[-1] == "Villa",
              " > ".join(rank.index))

    if "mart_volatility" in marts:
        vr = marts["mart_volatility"].groupby("house_type")["volatility_4q"].mean().sort_values(ascending=False)
        check("C · volatilidad: Townhouse/Apartment top, Villa fondo",
              vr.index[0] in ("Townhouse", "Apartment") and vr.index[-1] == "Villa",
              " > ".join(vr.index))

    if "mart_quarterly_regional_index" in marts:
        ri = marts["mart_quarterly_regional_index"]
        last = ri[ri["quarter"] == ri["quarter"].max()].set_index("region")["regional_index"]
        check("C · índice Zealand 2024Q4 ≈ 210 (más que duplica base 1992)",
              approx(last.get("Zealand", 0), 210.3, 2.0),
              f"Zealand={last.get('Zealand', float('nan')):.1f}")
        check("C · Fyn & islands por debajo de 100 (bajo su nivel 1992)",
              last.get("Fyn & islands", 999) < 100,
              f"Fyn={last.get('Fyn & islands', float('nan')):.1f}")

    if "mart_model_comparison" in marts:
        mc = marts["mart_model_comparison"]
        champ = mc.loc[mc["test_r2"].idxmax()]
        check("C · modelo campeón XGBoost R²≈0.44, MAE≈867k DKK",
              "XGBoost" in champ["model"] and approx(champ["test_r2"], 0.44, 0.03)
              and approx(champ["test_mae"], 867000, 15000),
              f"{champ['model']} R²={champ['test_r2']:.3f} MAE={champ['test_mae']:,.0f}")

    if "mart_segment_profiles" in marts:
        prof = marts["mart_segment_profiles"]
        # k operativo = 4 perfiles de negocio (el 'cientifico' por consenso es 2, ver
        # mart_segmentation_validation.csv). Se elige 4 por informatividad riesgo-retorno.
        check("C · segmentación: 4 perfiles de negocio (k operativo)",
              len(prof) == 4, f"{len(prof)} clusters")
        arquetipos_esperados = {
            "Premium estable/liquido", "Volatil / alto riesgo",
            "Value estable/liquido", "Value con crecimiento",
        }
        check("C · arquetipos de inversión correctos",
              set(prof["cluster_label"]) == arquetipos_esperados,
              f"{sorted(prof['cluster_label'])}")
        alto = prof.loc[prof["price_level"].idxmax()]
        bajo = prof.loc[prof["price_level"].idxmin()]
        check("C · cluster de precio alto (Premium) tiene menor drawdown que el más bajo",
              alto["max_drawdown"] > bajo["max_drawdown"],
              f"alto={alto['max_drawdown']:.1f}% vs bajo={bajo['max_drawdown']:.1f}%")

    if "mart_segmentation_validation" in marts:
        val = marts["mart_segmentation_validation"]
        check("C · validación consenso: k científico=2, operativo=4",
              int(val["k_cientifico"].iloc[0]) == 2 and int(val["k_operativo"].iloc[0]) == 4,
              f"científico={val['k_cientifico'].iloc[0]} operativo={val['k_operativo'].iloc[0]}")
        # el experimento: k=4 explica más varianza de riesgo que k=2
        er = val.set_index("k")["eta2_risk"]
        check("C · experimento η²: k=4 más informativo en riesgo que k=2",
              er.get(4, 0) > er.get(2, 0),
              f"η²_riesgo k=2→{er.get(2, float('nan')):.3f} vs k=4→{er.get(4, float('nan')):.3f}")

    if "mart_rfm_segments" in marts:
        rfm = marts["mart_rfm_segments"]
        in_range = rfm[["R", "F", "M"]].apply(lambda c: c.between(1, 5)).all().all()
        check("C · RFM: scores R/F/M en [1,5]", bool(in_range))
        champ = rfm[rfm["rfm_segmento"].str.startswith("Champions")]
        dorm = rfm[rfm["rfm_segmento"].str.startswith("Periferico")]
        champ_ok = (
            len(champ) > 0 and len(dorm) > 0
            and champ["price_level"].mean() > dorm["price_level"].mean()
            and champ["max_drawdown"].mean() > dorm["max_drawdown"].mean()
        )
        check("C · RFM: Champions = premium con mejor drawdown que Periférico dormido", champ_ok,
              f"Champions precio={champ['price_level'].mean():.0f} dd={champ['max_drawdown'].mean():.1f} vs "
              f"Dormido precio={dorm['price_level'].mean():.0f} dd={dorm['max_drawdown'].mean():.1f}")
        if "mart_zip_segments" in marts:
            orphan = set(rfm["zip_code"].astype(str)) - set(marts["mart_zip_segments"]["zip_code"].astype(str))
            check("C · RFM: zips ⊆ zips segmentados (mismo universo)", not orphan,
                  f"{len(orphan)} huérfanos")

    # ── Reporte ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("QA TÉCNICO — capa Gold")
    print("=" * 78)
    passed = 0
    for name, ok, detail in _results:
        icon = "PASS" if ok else "FAIL"
        print(f"[{icon}] {name}" + (f"  — {detail}" if detail else ""))
        passed += ok
    total = len(_results)
    print("-" * 78)
    print(f"Resultado: {passed}/{total} chequeos OK")
    print("=" * 78)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
