# Runbook — Ejecución Completa del Pipeline

## Prerequisitos

1. Python 3.11+ instalado
2. Dataset descargado desde Kaggle en `data/raw/danish_housing_prices.csv`

## Paso 1 — Setup del entorno

```bash
git clone https://github.com/<tu-usuario>/danish-housing-analysis.git
cd danish-housing-analysis

python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

pip install -r requirements.txt
```

## Paso 2 — Descargar el dataset

Opción A (manual):
- Ir a https://www.kaggle.com/datasets/martinfrederiksen/danish-residential-housing-prices-1992-2024
- Descargar y colocar el CSV en `data/raw/danish_housing_prices.csv`

Opción B (API de Kaggle):
```bash
pip install kaggle
kaggle datasets download martinfrederiksen/danish-residential-housing-prices-1992-2024
unzip danish-residential-housing-prices-1992-2024.zip -d data/raw/
```

## Paso 3 — Limpieza de datos (TB2)

```bash
python scripts/run_cleaning.py --config configs/analysis.yaml
```

Output en `data/processed/`:
- `danish_housing_clean.parquet` — datos limpios con flags
- `bitacora_limpieza.csv` — registro de transformaciones

Para prueba rápida con muestra:
```bash
python scripts/run_cleaning.py --config configs/analysis.yaml --sample 50000
```

## Paso 4 — Análisis Exploratorio (TB3)

```bash
jupyter notebook notebook/TB3_analisis_exploratorio.ipynb
```

## Paso 4b — Marts Gold + Segmentación no supervisada (TF)

```bash
# Genera los marts de KPIs desde Silver
uv run python scripts/export_marts.py --config configs/analysis.yaml

# Segmentación no supervisada PCA + KMeans + t-SNE (Entrega 6)
#   -> data/marts/mart_zip_segments.csv, mart_segment_profiles.csv
#   -> docs/refs/segmentation_pca_tsne.png
uv run python scripts/run_segmentation.py --config configs/analysis.yaml
```

> El pipeline completo `scripts/run_pipeline.py` ejecuta la segmentación como FASE C
> automáticamente al final (raw → Silver → Gold → segmentación).

## Paso 5 — Tests y QA

```bash
pytest tests/ -v
pytest tests/ --cov=src/danish_housing --cov-report=term-missing

# QA técnico: integridad + reconciliación informe/dashboard vs marts (23/23 esperado)
uv run python scripts/run_qa.py
```

## Paso 6 — Linting

```bash
ruff check src tests
black --check src tests
```
