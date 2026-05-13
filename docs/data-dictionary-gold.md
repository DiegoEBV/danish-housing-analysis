# Diccionario de Datos — Capa Gold

**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024  
**Capa**: Gold (`gs://danish-housing-gold/marts/`)  
**Actualización**: Generado por `scripts/export_marts.py` a partir del Silver layer

> Este diccionario documenta los marts listos para Tableau. Para el diccionario del dataset original (Bronze/Silver), ver el notebook TB2.

---

## Dataset Original — Variables Críticas (Silver)

### Variables Geográficas

| Variable | Tipo | Descripción | Ejemplo | Notas |
|----------|------|-------------|---------|-------|
| `zip_code` | str | Código postal danés (4 dígitos) | `"1050"` | P7: convertido de int con zfill(4) |
| `city` | str | Ciudad | `"Copenhagen"` | P1: nulos imputados con "Unknown" |
| `area` | str | Área geográfica agrupada | `"Copenhagen"`, `"East Jutland"` | — |
| `region` | str | Región administrativa danesa | `"København"`, `"Midtjylland"` | 5 regiones |

### Variables Técnicas de Vivienda

| Variable | Tipo | Descripción | Ejemplo | Notas |
|----------|------|-------------|---------|-------|
| `house_id` | str | Identificador único de vivienda | `"dk-12345"` | Clave natural |
| `house_type` | str | Tipología de vivienda | `"Villa"`, `"Ejerlejlighed"`, `"Fritidshus"`, `"Rækkehus"` | 4 categorías principales |
| `year_build` | int | Año de construcción | `1965` | P4: flag para < 1800 |
| `sqm` | float | Superficie en m² | `120.0` | 20–500 m² rango normal |
| `no_rooms` | int | Número de habitaciones | `4` | 1–10 |

### Variables Económicas de la Transacción

| Variable | Tipo | Descripción | Ejemplo | Notas |
|----------|------|-------------|---------|-------|
| `date` | date | Fecha de la transacción | `2008-03-15` | Cobertura 1992–2024 |
| `purchase_price` | float | Precio de compra en DKK | `2,500,000` | P5: flag outliers IQR×3 |
| `sqm_price` | float | Precio nominal por m² (DKK) | `20,833` | Derivado: price/sqm |
| `sqm_price_real` | float | Precio real por m² (DKK, base 2024) | `18,200` | Deflactado con IPC danés |
| `sales_type` | str | Tipo de venta | `"Normal salg"`, `"-"`, `"Familiehandel"` | P3: flag ventas no mercado |

### Variables Macroeconómicas (Dinamarca)

| Variable | Tipo | Descripción | Fuente | Notas |
|----------|------|-------------|--------|-------|
| `nom_interest_rate_pct` | float | Tasa de interés nominal (%) | Finans Danmark | P8: renombrado de `%25` |
| `dk_ann_infl_rate_pct` | float | Inflación anual danesa (%) | Statistics Denmark | P2: nulos en 2023-2024 |
| `yield_mortgage_bonds_pct` | float | Rendimiento bonos hipotecarios 30Y (%) | Boliga | P2: nulos en 2023-2024 |

### Flags de Calidad (creados en Silver)

| Variable | Tipo | Descripción | % afectado |
|----------|------|-------------|------------|
| `macro_nulo` | bool | Nulos en vars macro (período 2023–2024) | ~0.005% |
| `sales_type_valido` | bool | False = venta no de mercado | ~0.5% |
| `year_build_flag` | bool | True = year_build < 1800 (sospechoso) | < 0.1% |
| `purchase_price_outlier` | bool | True = outlier IQR×3 en precio | ~3% |
| `sqm_price_outlier` | bool | True = outlier IQR×3 en precio/m² | ~3% |
| `periodo_preliminar` | bool | True = año < 1995 (menor completitud) | ~2% |

---

## Marts Gold — Diccionario Completo

### mart_quarterly_regional_index.csv

Fuente de verdad para la Vista 1 del dashboard (evolución temporal regional).

| Campo | Tipo | Descripción | Rango esperado |
|-------|------|-------------|----------------|
| `quarter` | str | Trimestre en formato "AÑOQt" | "1992Q1" – "2024Q4" |
| `year` | int | Año | 1992–2024 |
| `region` | str | Región danesa | 5 valores |
| `avg_sqm_price_real` | float | Precio real promedio por m² en DKK | 5,000–50,000 |
| `regional_index` | float | Índice normalizado, base 1992=100 | 100–600 approx |
| `n_transactions` | int | Volumen de ventas en el trimestre | 1–50,000 |
| `base_year_price` | float | Precio promedio en 1992 (denominador del índice) | por región |

### mart_drawdowns.csv

Fuente para la Vista 3 (análisis de crisis y caídas).

| Campo | Tipo | Descripción | Rango esperado |
|-------|------|-------------|----------------|
| `quarter` | str | Trimestre | "1992Q1" – "2024Q4" |
| `region` | str | Región | 5 valores |
| `house_type` | str | Tipología | 4 valores |
| `avg_sqm_price_real` | float | Precio real promedio | — |
| `cumulative_max` | float | Máximo histórico hasta ese trimestre | — |
| `drawdown_pct` | float | % caída desde pico (negativo o cero) | -60% – 0% |

### mart_volatility.csv

Fuente para la Vista 4 (volatilidad comparada por tipología).

| Campo | Tipo | Descripción | Rango esperado |
|-------|------|-------------|----------------|
| `quarter` | str | Trimestre | "1992Q1" – "2024Q4" |
| `house_type` | str | Tipología | 4 valores |
| `pct_change` | float | Cambio % trimestral del precio real | — |
| `volatility_4q` | float | Desv. estándar rolling 4 trimestres | 0%–20% |

### mart_macro_correlation.csv

Fuente para la Vista 5 (correlación volumen-bonos, hipótesis H1).

| Campo | Tipo | Descripción | Rango esperado |
|-------|------|-------------|----------------|
| `quarter` | str | Trimestre | "1992Q1" – "2024Q4" |
| `n_transactions` | int | Volumen trimestral | — |
| `avg_bond_yield` | float | Yield promedio bonos 30Y (%) | 1%–15% |
| `bond_yield_lag2q` | float | Yield con rezago de 2 trimestres | — |
| `volume_bond_corr` | float | Correlación rolling (8Q) volumen vs. yield rezagado | -1 – 1 |

### mart_transactions_map.csv

Fuente para la Vista 2 (mapa choropleth por código postal).

| Campo | Tipo | Descripción | Notas |
|-------|------|-------------|-------|
| `year` | int | Año | Filtro del slider en Tableau |
| `zip_code` | str | Código postal (4 dígitos) | Join con shapefile PostNord |
| `city` | str | Ciudad asociada | — |
| `region` | str | Región | — |
| `avg_sqm_price_real` | float | Precio real promedio DKK/m² | Escala de color del mapa |
| `n_transactions` | int | Volumen de ventas | Tamaño del tooltip |

### mart_model_comparison.csv (TB3)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `modelo` | str | Nombre del modelo |
| `r2_cv_mean` | float | R² medio en cross-validation |
| `r2_cv_std` | float | Desv. estándar R² en CV |
| `r2_test` | float | R² en test set |
| `mae` | float | MAE en DKK/m² |
| `rmse` | float | RMSE en DKK/m² |
| `mape_pct` | float | MAPE en % |

### mart_feature_importance.csv (TB3)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `feature` | str | Nombre de la variable |
| `importance` | float | Importancia Gini del Random Forest |
| `rank` | int | Ranking de importancia (1 = más importante) |

---

## Notas de Calidad de Datos

1. **Período 1992–1994**: marcado con `periodo_preliminar=True`. Datos menos completos por transición al sistema digital. Incluir en vistas con tooltip de advertencia.
2. **2023–2024**: variables macro con `macro_nulo=True`. Las vistas macroeconómicas excluyen estos registros.
3. **Precios outliers**: excluidos de tendencias (`*_outlier=True`) pero incluidos en vista de volumen.
4. **Ventas no de mercado**: excluidas del análisis de precios (`sales_type_valido=False`) pero incluidas en volumen total.
