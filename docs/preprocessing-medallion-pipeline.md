# Pipeline de Preprocesamiento Medallion

**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024

---

## Visión General

El pipeline sigue la arquitectura Medallion: cada capa agrega calidad y transforma los datos para el siguiente paso. Todos los parámetros están centralizados en `configs/analysis.yaml` para garantizar reproducibilidad.

```
RAW (Kaggle)
    │
    ▼  [Ingesta]
BRONZE — datos crudos, sin tocar
    │
    ▼  [Limpieza P1–P8]
SILVER — datos válidos con flags de calidad
    │
    ▼  [Agregación + KPIs]
GOLD   — marts listos para Tableau
```

---

## Capa Bronze — Ingesta

**Script**: `scripts/fetch_kaggle_data.py` (Kaggle API) o descarga manual
**Destino local**: `data/raw/DKHousingPrices.parquet`
**Destino GCS**: `gs://danish-housing-bronze/raw/DKHousingPrices.parquet`

### Características del dato crudo (valores REALES, no estimados)

| Atributo | Valor |
|----------|-------|
| Filas | **1,507,908** |
| Columnas | 19 |
| Formato | Parquet (compressed, Snappy) |
| Tamaño Parquet | **43.0 MB** |
| Tamaño CSV equivalente | ~200 MB |
| Rango fechas | 1992-01-05 → 2024-10-26 |
| Macro NaN (2023–2024) | 1,193 filas |
| Schema notable | `nom_interest_rate%`, `dk_ann_infl_rate%`, `yield_on_mortgage_credit_bonds%` (con sufijo `%` literal en el parquet) |

### Qué NO se modifica en Bronze
- No se eliminan filas
- No se cambian tipos de dato
- No se renombran columnas
- Se preserva el parquet exactamente como viene de Kaggle

---

## Capa Silver — Limpieza

**Script**: `scripts/run_cleaning.py`  
**Módulo**: `src/danish_housing/cleaning.py`  
**Input**: Bronze CSV  
**Output**: `danish_housing_clean.parquet` + `bitacora_limpieza.csv`

### Reglas aplicadas (en orden) · CONTEOS REALES sobre 1,507,908 filas

| ID | Problema | Columnas | Acción | Filas afectadas |
|----|----------|----------|--------|----------------:|
| P1 | Nulos en `city` | `city` | Imputar `'Unknown'` | 0 (parquet ya completo) |
| P2 | Nulos en vars macro 2023–2024 | `dk_ann_infl_rate`, `yield_mortgage_bonds` | Crear flag `macro_nulo` | 1,193 (0.08%) |
| P3 | `sales_type ∈ {family_sale, other_sale, auction, '-'}` | `sales_type` | Crear flag `sales_type_valido` | **175,149 (11.6%)** |
| P4 | `year_build < 1800` | `year_build` | Crear flag `year_build_flag` | 0 |
| P5 | Outliers `purchase_price` (IQR×3) | `purchase_price` | Crear flag `purchase_price_outlier` | 24,282 (1.6%) |
| P5 | Outliers `sqm_price` (IQR×3) | `sqm_price` | Crear flag `sqm_price_outlier` | 15,217 (1.0%) |
| P6 | Período 1992–1994 menor completitud | General | Crear flag `periodo_preliminar` | 56,043 (3.7%) |
| P7 | `zip_code` como int (pierde ceros) | `zip_code` | Convertir a str con `zfill(4)` | 1,507,908 (todas) |
| P8 | Sufijo `%` o `%25` en nombres macro | Macro vars | Renombrar a `*_pct` | 1,507,908 (todas) |

**Dataset limpio para análisis** (post-filtros `sales_type_valido & ~purchase_price_outlier`): **1,311,568 filas (87.0%)**.

### Filosofía de limpieza

> **Preferimos flags sobre eliminación**. Los registros problemáticos se marcan pero no se borran. Esto permite:
> - Reproducibilidad: el Silver siempre puede regenerarse desde Bronze
> - Flexibilidad: análisis posteriores pueden incluir o excluir según necesidad
> - Auditabilidad: la bitácora registra cada transformación

### Output Silver

```python
# Columnas nuevas añadidas en Silver (además de las originales):
flags_nuevas = [
    'macro_nulo',           # P2
    'sales_type_valido',    # P3
    'year_build_flag',      # P4
    'purchase_price_outlier', # P5
    'sqm_price_outlier',    # P5
    'periodo_preliminar',   # P6
]
# Columnas transformadas: city, zip_code, nom_interest_rate_pct, etc.
```

---

## Capa Gold — Marts para Tableau

**Script**: `scripts/export_marts.py`  
**Módulo**: `src/danish_housing/kpis.py`, `src/danish_housing/marts.py`  
**Input**: Silver parquet  
**Output**: CSVs en `data/processed/gold/`

### Marts generados

#### `mart_quarterly_regional_index.csv`
Índice de precios normalizado por región (base 1992 = 100), agregado por trimestre.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `quarter` | str | Período (e.g., "1992Q1") |
| `region` | str | Región danesa |
| `avg_sqm_price_real` | float | Precio promedio real DKK/m² |
| `regional_index` | float | Índice normalizado (1992=100) |
| `n_transactions` | int | N° transacciones en el trimestre |

#### `mart_drawdowns.csv`
Drawdown pico-valle por región y tipología.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `quarter` | str | Período |
| `region` | str | Región |
| `house_type` | str | Tipo de vivienda |
| `drawdown_pct` | float | % caída desde pico previo |
| `peak_price` | float | Precio en el pico |

#### `mart_volatility.csv`
Volatilidad rolling de 4 trimestres por tipología.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `quarter` | str | Período |
| `house_type` | str | Tipo de vivienda |
| `volatility_4q` | float | Desv. estándar cambio % (ventana 4Q) |

#### `mart_macro_correlation.csv`
Volumen de ventas vs. rendimiento bonos hipotecarios con rezago.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `quarter` | str | Período |
| `n_transactions` | int | Volumen trimestral |
| `avg_bond_yield` | float | Yield promedio bonos 30Y |
| `bond_yield_lag2q` | float | Yield con rezago 2 trimestres |

#### `mart_transactions_map.csv`
Precios agregados por zip_code para mapa choropleth en Tableau.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `year` | int | Año |
| `zip_code` | str | Código postal (4 dígitos, zfill) |
| `avg_sqm_price_real` | float | Precio real promedio |
| `n_transactions` | int | Volumen de ventas |

#### `mart_model_comparison.csv` (TB3)
Comparativa de métricas de los modelos entrenados.

#### `mart_predictions.csv` (TB3)
Predicciones del Random Forest sobre el test set.

#### `mart_feature_importance.csv` (TB3)
Importancia de variables del modelo seleccionado.

---

## Reproducibilidad

Para regenerar todo el pipeline desde cero (con `uv`):

```bash
# 0. Setup
uv sync --extra dev

# 1. Descargar raw de Kaggle (requiere ~/.kaggle/kaggle.json)
uv run python scripts/fetch_kaggle_data.py

# 2. Pipeline completo (cleaning + marts en una sola pasada, memory-efficient)
uv run python scripts/run_pipeline.py --config configs/analysis.yaml

#    O por etapas:
uv run python scripts/run_cleaning.py --config configs/analysis.yaml
uv run python scripts/export_marts.py --config configs/analysis.yaml

# 3. Modelado predictivo (TB3 Fase 4) — opcional, requiere GPU para Optuna 50 trials
uv run python scripts/run_modeling.py --config configs/analysis.yaml \
  --device cuda --optuna-trials 30 --cv-folds 5

# 4. Subir a GCP (requiere gcloud auth application-default login)
uv run python scripts/upload_to_gcs.py --layer all --config configs/analysis.yaml
```

Todos los parámetros (umbrales IQR, año base, ventana de volatilidad, project GCP) están en `configs/analysis.yaml` y son la única fuente de verdad.

### Tiempos referenciales (1.5M filas, Lightning.ai L4 GPU)

| Etapa | CPU | GPU (L4) |
|---|---:|---:|
| `run_pipeline.py` (cleaning + 5 marts) | ~30 s | n/a |
| `run_modeling.py` con Optuna 30 trials + CV 5 folds | ~50 min | **~22 min** |
| `upload_to_gcs.py --layer all` | ~30 s (subida 51 MB Silver) | n/a |

---

## Tests de calidad del pipeline

```bash
uv run pytest tests/ -v       # 13/13 tests (8 P1-P8 + 4 features anti-leak + 1 pipeline)
```
