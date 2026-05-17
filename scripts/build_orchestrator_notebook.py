"""
scripts/build_orchestrator_notebook.py — Genera notebook/00_pipeline_medallion.ipynb.

El notebook resultante es el "columna metodologica" que ve el curso: TB1 ->
TB2 -> TB3 end-to-end con narrativa en espanol. No reimplementa logica;
importa de src/danish_housing y de scripts/ para mantener un solo punto
de verdad.

Uso:
    uv run python scripts/build_orchestrator_notebook.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf


def md(s: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(s)


def code(s: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(s)


nb = nbf.v4.new_notebook()
nb["cells"] = [
    md("""# Pipeline Medallion end-to-end — Dinámica de precios residenciales en Dinamarca 1992–2024

**Curso**: Data Visualization — UPC 2026-01
**Entregables cubiertos**: TB1 (ficha), TB2 (limpieza), TB3 (marts + modelado)
**Autores**: Rody Vilchez, Diego Ballón, Christian Velásquez

Este notebook **orquesta** el pipeline completo desde el raw de Kaggle hasta los marts Gold y el reporte de métricas del modelo. No reimplementa lógica — importa de `src/danish_housing/` y `scripts/`.

> **Prerequisito**: `data/raw/DKHousingPrices.parquet` presente. Si no, genera uno sintético con `uv run python scripts/generate_synthetic_raw.py` (sólo smoke test, no entregable).
"""),
    md("""## 0. Setup y configuración"""),
    code("""import sys, yaml, json
from pathlib import Path

# Localizar la raiz del proyecto (donde vive configs/analysis.yaml) y agregar src/
ROOT = Path.cwd()
while ROOT != ROOT.parent and not (ROOT / "configs" / "analysis.yaml").exists():
    ROOT = ROOT.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
import os
os.chdir(ROOT)

import numpy as np
import pandas as pd

from danish_housing.cleaning import run_cleaning_pipeline
from danish_housing.features import build_feature_matrix, temporal_train_test_split

CFG = yaml.safe_load(open("configs/analysis.yaml"))
print("Paths:"); print(json.dumps(CFG["paths"], indent=2))
print("\\nGCP:"); print(json.dumps(CFG["gcp"], indent=2))
"""),

    md("""## 1. TB1 — Ficha del proyecto

**Pregunta analítica**: ¿qué tipologías de vivienda muestran la mayor volatilidad y drawdowns durante crisis financieras, y cómo difieren los precios entre Copenhague y las provincias bajo distintos regímenes de tasas/inflación?

**Dataset**: [Kaggle — martinfrederiksen/danish-residential-housing-prices-1992-2024](https://www.kaggle.com/datasets/martinfrederiksen/danish-residential-housing-prices-1992-2024), ~1.5M transacciones, 1992–2024.

**5 KPIs definidos** (`src/danish_housing/kpis.py`):
1. Precio real por m² (deflactado con IPC danés base 2024)
2. Índice regional (base 1992 = 100)
3. Drawdown pico-valle por (región, tipología)
4. Volatilidad rolling 4 trimestres
5. Elasticidad volumen-bonos (correlación con lag 2Q)

Detalle de la ficha en [`plans/project_plan.md`](../plans/project_plan.md)."""),

    md("""## 2. TB2 — Perfilado y limpieza (Bronze → Silver)

Reglas P1–P8 implementadas en `src/danish_housing/cleaning.py`. La bitácora es un artefacto entregable.
"""),
    code("""raw_path = Path(CFG["paths"]["raw_parquet"])
if not raw_path.exists():
    raise FileNotFoundError(
        f"{raw_path} no encontrado. Genera sintético con:\\n"
        "  uv run python scripts/generate_synthetic_raw.py"
    )

df_raw = pd.read_parquet(raw_path)
print(f"Raw: {df_raw.shape[0]:,} filas × {df_raw.shape[1]} columnas")
df_raw.head(3)
"""),
    code("""df_clean, bitacora = run_cleaning_pipeline(df_raw, CFG.get("cleaning", {}))
print(f"\\nSilver: {df_clean.shape[0]:,} filas × {df_clean.shape[1]} columnas")
print("\\nBitácora:")
bitacora
"""),
    code("""# Guardar Silver + bitácora
silver_path = Path(CFG["paths"]["silver_parquet"])
silver_path.parent.mkdir(parents=True, exist_ok=True)
df_clean.to_parquet(silver_path, index=False, compression="snappy")

bitacora_path = Path(CFG["paths"]["bitacora_csv"])
bitacora_path.parent.mkdir(parents=True, exist_ok=True)
bitacora.to_csv(bitacora_path, index=False)

print(f"Silver -> {silver_path}")
print(f"Bitácora -> {bitacora_path}")
"""),

    md("""## 3. TB3 — Marts Gold (análisis exploratorio)

5 marts trimestrales/regionales para el dashboard de Tableau. La lógica completa está en `scripts/run_pipeline.py` (FASE B) y replicada en `scripts/export_marts.py`. Aquí ejecutamos la versión standalone."""),
    code("""# Ejecuta export_marts.py para regenerar los 5 marts desde Silver
import subprocess
subprocess.run(
    ["uv", "run", "python", "scripts/export_marts.py", "--config", "configs/analysis.yaml"],
    check=True,
)
"""),
    code("""# Inspeccionar marts
gold_dir = Path(CFG["paths"]["gold_dir"])
for csv in sorted(gold_dir.glob("mart_*.csv")):
    df = pd.read_csv(csv)
    print(f"{csv.name}: {len(df):,} filas × {df.shape[1]} cols — {list(df.columns)}")
"""),

    md("""## 4. TB3 — Modelado predictivo (M1–M4)

4 modelos sobre el Silver con features auditadas en [`docs/legacy-leakage-audit.md`](../docs/legacy-leakage-audit.md). Entrena en `log1p(purchase_price)` por estabilidad numérica pero **reporta métricas SIEMPRE en escala nominal** (DKK).

- M1 Linear, M2 Ridge, M3 RandomForest, M4 XGBoost+Optuna
- Split temporal: train 1992–2017, test 2018–2024
"""),
    code("""# Construir feature matrix (con guarda anti-leak)
df_feat, feature_names, audit = build_feature_matrix(
    df_clean, target_col="purchase_price",
    window_years=12, min_obs_per_window=30,
)
print(f"Features: {len(feature_names)} | Anti-leak: {'PASS' if audit['leakage_check_passed'] else 'FAIL'}")
print(f"Excluidas ({len(audit['excluded_cols'])}): {audit['excluded_cols']}")
"""),
    code("""# Ejecutar pipeline de modelado completo (4 modelos + Optuna)
# --no-optuna para correr rápido; quitar para producción
subprocess.run(
    ["uv", "run", "python", "scripts/run_modeling.py", "--config", "configs/analysis.yaml", "--no-optuna"],
    check=True,
)
"""),
    code("""# Reporte de métricas
comparison = pd.read_csv(gold_dir / "mart_model_comparison.csv")
comparison[["model", "test_r2", "test_mae", "test_mape_pct", "test_rmse"]]
"""),
    code("""# Feature importance top-10 del campeón
importance = pd.read_csv(gold_dir / "mart_feature_importance.csv")
champion = comparison.sort_values("test_r2", ascending=False).iloc[0]["model"]
print(f"Campeón: {champion}")
importance[importance["model"] == champion].head(10)
"""),

    md("""## 5. Upload a GCP (opcional)

Si tienes `gcloud auth application-default login` configurado, sube las 3 capas a sus buckets:

```bash
uv run python scripts/upload_to_gcs.py --layer all --config configs/analysis.yaml
```

Buckets esperados (configurables en `configs/analysis.yaml -> gcp.buckets`):
- `gs://danish-housing-bronze/raw/`
- `gs://danish-housing-silver/processed/`
- `gs://danish-housing-gold/marts/`

Para automatización vía Cloud Run Job, ver [`runbooks/gcp-cloud-run-deployment.md`](../runbooks/gcp-cloud-run-deployment.md)."""),

    md("""## 6. TF — Dashboard Tableau (pendiente)

Los 5 marts Gold + los 3 marts de modelado alimentan 5+1 vistas del dashboard:

| Mart | Vista Tableau |
|---|---|
| `mart_quarterly_regional_index` | Línea de tiempo regional + overlay tasas |
| `mart_drawdowns` | Heatmap drawdowns por crisis |
| `mart_volatility` | Volatilidad por tipología |
| `mart_macro_correlation` | Correlación volumen-bonos con lag |
| `mart_transactions_map` | Mapa choropleth por zip_code |
| `mart_feature_importance` | Top features del modelo (M4) |

Plan en [`docs/tableau-dashboard-design.md`](../docs/tableau-dashboard-design.md)."""),

    md("""## Resumen del run

| Fase | Output | Path |
|---|---|---|
| TB1 | Ficha | `plans/project_plan.md` |
| TB2 | Silver parquet | `data/processed/silver/danish_housing_clean.parquet` |
| TB2 | Bitácora | `data/processed/bitacora_limpieza.csv` |
| TB3 | 5 marts analíticos | `data/processed/gold/mart_*.csv` |
| TB3 | 3 marts modelado | `data/processed/gold/mart_model_*.csv` |
| TB3 | Audit modelado | `data/processed/gold/modeling_audit.json` |
| TF | Dashboard | (pendiente — semana 13) |

**Issues abiertos** (ver `bd ready`):
- `4kz` — subir Bronze 1.2M a GCS
- `5fi` — Fase 4 con dataset real (no synthetic)
- `chl` — Cloud Run Job deployment
- `15y`, `d7b`, `h64`, `ay6` — TF (dashboard)"""),
]

out = Path("notebook/00_pipeline_medallion.ipynb")
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print(f"Notebook generado: {out}")
