"""Tests del IPC canónico compartido (kpis.build_cpi_from_inflation / deflate_sqm_price).

Garantizan que la función unificada reproduce EXACTAMENTE la lógica inline previa de
run_pipeline.py, para que unificar la definición de sqm_price_real no cambie los valores.
"""

import numpy as np
import pandas as pd

from danish_housing.kpis import build_cpi_from_inflation, deflate_sqm_price


def _cpi_inline_legacy(infl_by_year: pd.Series) -> dict:
    """Réplica de la lógica inline original de run_pipeline.py (referencia de equivalencia)."""
    cpi: dict[int, float] = {}
    cpi[int(infl_by_year.index.max())] = 100.0
    for yr in sorted(infl_by_year.index, reverse=True)[1:]:
        yr, yp1 = int(yr), int(yr) + 1
        rate = infl_by_year.get(yp1, 2.0)
        cpi[yr] = cpi[yp1] / (1 + rate / 100)
    for yr in range(1992, min(cpi.keys())):
        cpi[yr] = cpi[min(cpi.keys())] / (1.02 ** (min(cpi.keys()) - yr))
    return cpi


def test_cpi_base_year_is_100():
    infl = pd.Series({2020: 1.5, 2021: 2.0, 2022: 8.5}).sort_index()
    cpi = build_cpi_from_inflation(infl)
    assert cpi[2022] == 100.0  # año más reciente = base


def test_cpi_equivalence_with_legacy_inline():
    # Escenario REAL del dataset: inflación cubre 1992..2022 (contigua desde start_year).
    # En este caso el pre-loop legacy queda vacío y la función canónica reproduce EXACTAMENTE
    # los valores que generaron los marts entregados. (La función además corrige un quirk
    # latente del legacy en el relleno pre-min cuando la serie NO arranca en start_year.)
    rng = np.random.default_rng(0)
    years = range(1992, 2023)
    infl = pd.Series({y: float(rng.uniform(-0.5, 9.0)) for y in years}).sort_index()
    got = build_cpi_from_inflation(infl)
    expected = _cpi_inline_legacy(infl)
    assert got.keys() == expected.keys()
    for yr in expected:
        assert got[yr] == expected[yr], f"CPI divergente en {yr}"


def test_cpi_extends_to_start_year_with_fallback():
    infl = pd.Series({2000: 2.0, 2001: 2.0}).sort_index()
    cpi = build_cpi_from_inflation(infl, start_year=1992)
    assert min(cpi) == 1992  # se extiende hacia atrás hasta start_year
    # cada año pre-2000 baja ~2% respecto al siguiente
    assert cpi[1999] < cpi[2000]
    assert np.isclose(cpi[1999], cpi[2000] / 1.02)


def test_deflate_sqm_price_formula():
    cpi = {2020: 80.0, 2021: 90.0, 2022: 100.0}
    df = pd.DataFrame({"sqm_price": [8000.0, 9000.0, 10000.0], "year": [2020, 2021, 2022]})
    real = deflate_sqm_price(df, cpi)
    # sqm_price * 100 / cpi_year → todo re-expresado a base 2022
    assert np.isclose(real.iloc[0], 8000.0 * 100 / 80.0)   # 10000
    assert np.isclose(real.iloc[2], 10000.0)               # base = nominal
