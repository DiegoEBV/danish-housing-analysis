"""
prepare_data.py — Examen Parcial Data Visualization UPC 2026-01
Patrón: análogo a scripts/generate_tableau.py pero lee CSVs reales del examen.
Salida: viz_data.json con todos los datos agregados para embeber en el HTML.
"""
import json
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
OUT_FILE = Path(__file__).parent / "viz_data.json"


# ─── Caso 1: ONPE pie chart ───────────────────────────────────────────────────

def aggregate_caso1():
    df = pd.read_csv(DATA_DIR / "caso1_onpe_resumen_sintetico.csv")

    votos_validos_total = df["votos_validos_total"].iloc[0]
    votos_emitidos_total = df["votos_emitidos_total"].iloc[0]
    electores_habiles = df["electores_habiles_referencial"].iloc[0]

    por_agrupacion = (
        df.groupby("agrupacion", as_index=False)["votos"].sum()
        .sort_values("votos", ascending=False)
    )
    por_agrupacion["pct_validos"] = (por_agrupacion["votos"] / votos_validos_total * 100).round(2)
    por_agrupacion["pct_emitidos"] = (por_agrupacion["votos"] / votos_emitidos_total * 100).round(2)
    por_agrupacion["pct_padron"] = (por_agrupacion["votos"] / electores_habiles * 100).round(2)

    return {
        "agrupaciones": por_agrupacion["agrupacion"].tolist(),
        "votos": por_agrupacion["votos"].tolist(),
        "pct_validos": por_agrupacion["pct_validos"].tolist(),
        "pct_emitidos": por_agrupacion["pct_emitidos"].tolist(),
        "pct_padron": por_agrupacion["pct_padron"].tolist(),
        "totales": {
            "votos_validos": int(votos_validos_total),
            "votos_emitidos": int(votos_emitidos_total),
            "electores_habiles": int(electores_habiles),
            "participacion_pct": round(votos_emitidos_total / electores_habiles * 100, 2),
        },
    }


# ─── Caso 2: Mesas 900001 – doble eje ─────────────────────────────────────────

def aggregate_caso2():
    df = pd.read_csv(DATA_DIR / "caso2_avance_elecciones_sintetico.csv")

    panel = df[df["fila_panel_resumen"].astype(str).str.lower() == "true"].copy()

    return {
        "elecciones": panel["eleccion"].tolist(),
        "ambito": panel["ambito_mostrado"].tolist(),
        "pct_contabilizadas": panel["pct_contabilizadas"].round(2).tolist(),
        "total_actas": panel["total_actas"].tolist(),
        "actas_pendientes": panel["actas_pendientes"].tolist(),
        "votos_validos_millones": (panel["votos_validos"] / 1e6).round(2).tolist(),
        "riesgo_cambio_visual": (panel["riesgo_cambio_visual"] * 100).round(4).tolist(),
    }


# ─── Caso 3: Pobreza-voto scatter ─────────────────────────────────────────────

def aggregate_caso3():
    df = pd.read_csv(DATA_DIR / "caso3_pobreza_voto_sintetico.csv")

    records = []
    for _, row in df.iterrows():
        records.append({
            "departamento": row["departamento"],
            "distrito": row["distrito_sintetico"],
            "tipo_area": row["tipo_area_sintetica"],
            "pobreza": round(float(row["pobreza_monetaria_pct_2024_sintetica"]), 1),
            "voto_x": round(float(row["pct_votos_validos_candidatura_x_2026_sintetico"]), 2),
            "electores": int(row["electores_habiles_sintetico"]),
        })

    tipos = sorted(df["tipo_area_sintetica"].unique().tolist())
    return {"puntos": records, "tipos_area": tipos}


# ─── Caso 4: Obras paralizadas ────────────────────────────────────────────────

def aggregate_caso4():
    df = pd.read_csv(DATA_DIR / "caso4_obras_paralizadas_resumen_sintetico.csv")

    depto_total = df[df["nivel_resumen"] == "departamento-total"].copy()
    depto_total["monto_por_obra"] = (
        depto_total["monto_total_soles"] / depto_total["obras_paralizadas"]
    ).round(0)
    depto_total["monto_mm"] = (depto_total["monto_total_soles"] / 1e6).round(2)
    depto_total["monto_por_obra_mm"] = (depto_total["monto_por_obra"] / 1e6).round(3)

    top_monto = depto_total.sort_values("monto_mm", ascending=True).tail(15)
    top_norm = depto_total.sort_values("monto_por_obra_mm", ascending=True).tail(15)

    por_sector = (
        df[df["sector"] != "Total"]
        .groupby("sector", as_index=False)
        .agg(obras=("obras_paralizadas", "sum"), monto=("monto_total_soles", "sum"))
        .sort_values("obras", ascending=False)
    )
    por_sector["monto_mm"] = (por_sector["monto"] / 1e6).round(2)

    nacional = depto_total["obras_paralizadas"].sum()
    monto_nacional = depto_total["monto_mm"].sum()

    return {
        "ranking_monto_bruto": {
            "departamentos": top_monto["departamento"].tolist(),
            "monto_mm": top_monto["monto_mm"].tolist(),
            "n_obras": top_monto["obras_paralizadas"].tolist(),
        },
        "ranking_normalizado": {
            "departamentos": top_norm["departamento"].tolist(),
            "monto_por_obra_mm": top_norm["monto_por_obra_mm"].tolist(),
            "n_obras": top_norm["obras_paralizadas"].tolist(),
        },
        "por_sector": {
            "sectores": por_sector["sector"].tolist(),
            "obras": por_sector["obras"].tolist(),
            "monto_mm": por_sector["monto_mm"].tolist(),
        },
        "totales": {
            "total_obras": int(nacional),
            "monto_total_mm": round(float(monto_nacional), 1),
        },
    }


# ─── Caso 5: Modelado estrella / copo de nieve ────────────────────────────────

def analyze_caso5():
    fact = pd.read_csv(DATA_DIR / "caso5_modelado_fact_mesa_sintetico.csv")
    dim_t = pd.read_csv(DATA_DIR / "caso5_modelado_dim_territorio_sintetico.csv")
    dim_s = pd.read_csv(DATA_DIR / "caso5_modelado_dim_servicios_sintetico.csv")

    n_mesas_fact = fact["mesa_id"].nunique()
    n_distritos_fact = fact["distrito_id"].nunique()
    n_distritos_dim_t = dim_t["distrito_id"].nunique()
    n_distritos_dim_s = dim_s["distrito_id"].nunique()

    dim_t_unica = n_distritos_dim_t == len(dim_t)

    fact_sin_dim = set(fact["distrito_id"].unique()) - set(dim_t["distrito_id"].unique())

    votos_por_mesa = (
        fact.groupby(["mesa_id", "eleccion_id"])["votos_validos_mesa"].nunique()
    )
    fan_trap = (votos_por_mesa > 1).sum()

    fact_joined = fact.merge(dim_t, on="distrito_id", how="left")
    total_votos_correcto = fact["votos"].sum()
    total_votos_joined = fact_joined["votos"].sum()
    fan_trap_inflacion = int(total_votos_joined - total_votos_correcto)

    n_elecciones = fact["eleccion_id"].nunique()
    n_organizaciones = fact["organizacion_politica"].nunique()

    return {
        "cardinalidad": {
            "mesas_unicas": int(n_mesas_fact),
            "distritos_en_fact": int(n_distritos_fact),
            "distritos_en_dim_territorio": int(n_distritos_dim_t),
            "distritos_en_dim_servicios": int(n_distritos_dim_s),
            "dim_territorio_clave_unica": bool(dim_t_unica),
            "distritos_sin_dim": list(fact_sin_dim)[:5],
            "mesas_con_votos_validos_inconsistente": int(fan_trap),
            "total_votos_fact": int(total_votos_correcto),
            "total_votos_tras_join_correcto": int(total_votos_joined),
            "inflacion_votos_si_join_malo": fan_trap_inflacion,
            "elecciones_unicas": int(n_elecciones),
            "organizaciones_unicas": int(n_organizaciones),
        }
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Procesando CSVs del examen...")

    viz_data = {
        "caso1": aggregate_caso1(),
        "caso2": aggregate_caso2(),
        "caso3": aggregate_caso3(),
        "caso4": aggregate_caso4(),
        "caso5": analyze_caso5(),
    }

    OUT_FILE.write_text(json.dumps(viz_data, ensure_ascii=False, indent=2))
    print(f"✓ {OUT_FILE} generado ({OUT_FILE.stat().st_size // 1024} KB)")

    c5 = viz_data["caso5"]["cardinalidad"]
    print("\n── Caso 5: Cardinalidad ──")
    print(f"  Mesas únicas en fact_mesa:          {c5['mesas_unicas']:>8,}")
    print(f"  Distritos en fact_mesa:             {c5['distritos_en_fact']:>8,}")
    print(f"  Distritos en dim_territorio:        {c5['distritos_en_dim_territorio']:>8,}")
    print(f"  dim_territorio.distrito_id único:   {c5['dim_territorio_clave_unica']}")
    print(f"  Votos totales (fact):                {c5['total_votos_fact']:>8,}")
    print(f"  Inflación si join mal construido:   {c5['inflacion_votos_si_join_malo']:>+8,}")
    print(f"  Mesas con votos_validos inconsist.: {c5['mesas_con_votos_validos_inconsistente']:>8,}")


if __name__ == "__main__":
    main()
