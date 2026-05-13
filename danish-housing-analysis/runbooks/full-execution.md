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

## Paso 5 — Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src/danish_housing --cov-report=term-missing
```

## Paso 6 — Linting

```bash
ruff check src tests
black --check src tests
```
