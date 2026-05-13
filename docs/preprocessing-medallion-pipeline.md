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

**Script**: carga manual desde Kaggle  
**Destino**: `gs://danish-housing-bronze/raw/danish_housing_prices.csv`

### Características del dato crudo

| Atributo | Valor |
|----------|-------|
| Filas | ~1,500,000 |
| Columnas | ~20 |
| Formato | CSV |
| Encoding | UTF-8 |
| Tamaño | ~200 MB |

### Qué NO se modifica en Bronze
- No se eliminan filas
- No se cambian tipos de dato
- No se renombran columnas
- Se preserva el CSV exactamente como viene de Kaggle

---

## Capa Silver — Limpieza

**Script**: `scripts/run_cleaning.py`  
**Módulo**: `src/danish_housing/cleaning.py`  
**Input**: Bronze CSV  
**Output**: `danish_housing_clean.parquet` + `bitacora_limpieza.csv`

### Reglas aplicadas (en orden)

| ID | Problema | Columnas | Acción | Tipo |
|----|----------|----------|--------|------|
| P1 | Nulos en `city` (~11 registros) | `city` | Imputar `'Unknown'` | Transformación |
| P2 | Nulos en vars macro 2023–2024 | `infl`, `yield` | Crear flag `macro_nulo` | Flag |
| P3 | `sales_type = '-'` (~0.5%) | `sales_type` | Crear flag `sales_type_valido` | Flag |
| P4 | `year_build < 1800` | `year_build` | Crear flag `year_build_flag` | Flag |
| P5 | Outliers precio (IQR×3) | `purchase_price`, `sqm_price` | Crear flags `*_outlier` | Flag |
| P6 | Período 1992–1994 menor completitud | General | Crear flag `periodo_preliminar` | Flag |
| P7 | `zip_code` como int (pierde ceros) | `zip_code` | Convertir a str con `zfill(4)` | Transformación |
| P8 | Columnas con `%25` en nombre | Macro vars | Renombrar a `*_pct` | Transformación |

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

Para regenerar todo el pipeline desde cero:

```bash
# 1. Limpiar (Bronze → Silver)
python scripts/run_cleaning.py --config configs/analysis.yaml

# 2. Generar marts (Silver → Gold)
python scripts/export_marts.py --config configs/analysis.yaml

# 3. Subir a GCP
python scripts/upload_to_gcs.py --layer all --config configs/analysis.yaml
```

Todos los parámetros (umbrales IQR, año base, ventana de volatilidad) están en `configs/analysis.yaml` y son la única fuente de verdad.

---

## Tests de calidad del pipeline

```bash
pytest tests/test_cleaning.py -v        # Valida reglas P1–P8
pytest tests/test_marts.py -v           # Valida shape y tipos de marts
```
