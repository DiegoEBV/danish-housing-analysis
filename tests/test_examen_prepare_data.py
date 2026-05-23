"""
tests/test_examen_prepare_data.py — QA del pipeline del examen parcial.

Estas pruebas validan que las agregaciones usadas por el HTML conserven las
decisiones analíticas centrales de cada caso.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent.parent
PREPARE_DATA = ROOT / "examen" / "prepare_data.py"
DATA_DIR = ROOT / "examen" / "data"


def load_prepare_data_module():
    spec = importlib.util.spec_from_file_location("examen_prepare_data", PREPARE_DATA)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_cases_are_json_serializable():
    module = load_prepare_data_module()
    viz_data = {
        "caso1": module.aggregate_caso1(),
        "caso2": module.aggregate_caso2(),
        "caso3": module.aggregate_caso3(),
        "caso4": module.aggregate_caso4(),
        "caso5": module.analyze_caso5(),
    }

    assert set(viz_data) == {"caso1", "caso2", "caso3", "caso4", "caso5"}
    json.dumps(viz_data, ensure_ascii=False)


def test_caso1_preserves_otros_and_denominators():
    module = load_prepare_data_module()
    result = module.aggregate_caso1()

    assert "Otros" in result["agrupaciones"]
    assert result["agrupaciones"][0] == "Otros"
    assert len(result["agrupaciones"]) == len(result["pct_validos"]) == len(result["pct_emitidos"])
    assert abs(sum(result["pct_validos"]) - 100) < 0.2
    pct_validos_sobre_emitidos = (
        result["totales"]["votos_validos"] / result["totales"]["votos_emitidos"] * 100
    )
    assert abs(sum(result["pct_emitidos"]) - pct_validos_sobre_emitidos) < 0.2
    assert all(validos >= emitidos for validos, emitidos in zip(
        result["pct_validos"], result["pct_emitidos"], strict=True
    ))


def test_caso2_uses_only_panel_summary_rows_and_keeps_scope():
    module = load_prepare_data_module()
    result = module.aggregate_caso2()
    raw = pd.read_csv(DATA_DIR / "caso2_avance_elecciones_sintetico.csv")
    expected = raw[raw["fila_panel_resumen"].astype(str).str.lower() == "true"]

    assert result["elecciones"] == expected["eleccion"].tolist()
    assert result["ambito"] == expected["ambito_mostrado"].tolist()
    assert result["total_actas"] == expected["total_actas"].tolist()
    assert all(0 <= pct <= 100 for pct in result["pct_contabilizadas"])
    assert len(set(result["total_actas"])) > 1
    assert set(result["ambito"]) == {"Nacional", "Lima Metropolitana"}


def test_caso3_keeps_district_granularity_and_area_types():
    module = load_prepare_data_module()
    result = module.aggregate_caso3()
    raw = pd.read_csv(DATA_DIR / "caso3_pobreza_voto_sintetico.csv")

    assert len(result["puntos"]) == len(raw)
    assert sorted(result["tipos_area"]) == ["mixto", "rural", "urbano"]
    assert {p["tipo_area"] for p in result["puntos"]} == set(result["tipos_area"])
    assert all(0 <= p["pobreza"] <= 100 for p in result["puntos"])
    assert all(0 <= p["voto_x"] <= 100 for p in result["puntos"])
    assert all(p["electores"] > 0 for p in result["puntos"])


def test_caso4_reports_raw_and_normalized_rankings():
    module = load_prepare_data_module()
    result = module.aggregate_caso4()

    bruto = result["ranking_monto_bruto"]
    normalizado = result["ranking_normalizado"]
    assert len(bruto["departamentos"]) == 15
    assert len(normalizado["departamentos"]) == 15
    assert bruto["monto_mm"] == sorted(bruto["monto_mm"])
    assert normalizado["monto_por_obra_mm"] == sorted(normalizado["monto_por_obra_mm"])
    assert result["totales"]["total_obras"] > 0
    assert result["totales"]["monto_total_mm"] > 0


def test_caso5_cardinality_checks_match_source_tables():
    module = load_prepare_data_module()
    result = module.analyze_caso5()["cardinalidad"]
    fact = pd.read_csv(DATA_DIR / "caso5_modelado_fact_mesa_sintetico.csv")
    dim_t = pd.read_csv(DATA_DIR / "caso5_modelado_dim_territorio_sintetico.csv")
    dim_s = pd.read_csv(DATA_DIR / "caso5_modelado_dim_servicios_sintetico.csv")

    assert result["mesas_unicas"] == fact["mesa_id"].nunique()
    assert result["distritos_en_fact"] == fact["distrito_id"].nunique()
    assert result["distritos_en_dim_territorio"] == dim_t["distrito_id"].nunique()
    assert result["distritos_en_dim_servicios"] == dim_s["distrito_id"].nunique()
    assert result["dim_territorio_clave_unica"] is True
    assert result["distritos_sin_dim"] == []
    assert result["mesas_con_votos_validos_inconsistente"] == 0
    assert result["total_votos_fact"] == int(fact["votos"].sum())
