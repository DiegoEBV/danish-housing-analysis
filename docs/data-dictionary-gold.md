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

**Sobre el rezago de 2 trimestres:** el lag se fijó a priori (`configs/analysis.yaml`, ciclo típico
de decisión/aprobación hipotecaria). Una cross-correlation empírica de `n_transactions` vs.
`avg_bond_yield` para lags 0–4Q sobre este mart da correlaciones estáticas muy planas y monótonamente
crecientes en magnitud (lag0 = −0.79, lag1 = −0.80, **lag2 = −0.81**, lag3 = −0.81, lag4 = −0.82), y
bajo el mismo esquema rolling-8Q del KPI el efecto medio es algo más fuerte en lag1 (|corr| media
0.58) que en lag2 (0.45), pero el mínimo de la ventana (el pico de crisis, −0.96 en la GFC citado en
el informe) es prácticamente idéntico entre lag1 y lag2. Conclusión: **lag=2 es una elección
razonable y defendible**, dentro del rango de respuesta más fuerte, pero no es un único óptimo
empírico marcado — lag=1 responde de forma comparable o levemente mayor en promedio. No se cambia el
pipeline por esto; se deja documentado como nota de sensibilidad.

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

### mart_zip_segments.csv (TF · segmentación no supervisada)

Una fila por código postal segmentado (grano `zip_code`). Generado por
`scripts/run_segmentation.py` (PCA + KMeans + t-SNE sobre `mart_transactions_map`).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `zip_code` | str | Código postal danés (4 dígitos) |
| `city` | str | Ciudad de referencia |
| `region` | str | Región (Zealand, Jutland, Fyn & islands, Bornholm) |
| `n_years` | int | Años de historia usados |
| `price_level` | float | Nivel de precio real/m² (mediana ventana reciente) |
| `cagr_real` | float | Crecimiento anual compuesto del precio real |
| `volatility` | float | Desv. estándar del cambio interanual |
| `max_drawdown` | float | Peor caída pico-valle (%) |
| `liquidity_log` | float | log(1 + volumen medio de transacciones) |
| `growth_recent` | float | Crecimiento en la ventana reciente (5 años) |
| `pca1`, `pca2` | float | Coordenadas en el espacio PCA (2D) |
| `tsne1`, `tsne2` | float | Coordenadas en el embedding t-SNE (2D) |
| `cluster` | int | Id de cluster KMeans |
| `cluster_label` | str | Etiqueta interpretable (p. ej. "Precio alto / dinámico / estable") |

### mart_segment_profiles.csv (TF · perfil por cluster)

Una fila por cluster (centroide interpretable).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cluster` | int | Id de cluster |
| `n_zips` | int | Número de zips en el cluster |
| `price_level`, `cagr_real`, `volatility`, `max_drawdown`, `liquidity_log`, `growth_recent` | float | Media del centroide en cada feature |
| `cluster_label` | str | Etiqueta interpretable |
| `region_dominante` | str | Región más frecuente en el cluster |

---

## Notas de Calidad de Datos

1. **Período 1992–1994**: marcado con `periodo_preliminar=True`. Datos menos completos por transición al sistema digital. Incluir en vistas con tooltip de advertencia.
2. **2023–2024**: variables macro con `macro_nulo=True`. Las vistas macroeconómicas excluyen estos registros.
3. **Precios outliers**: excluidos de tendencias (`*_outlier=True`) pero incluidos en vista de volumen.
4. **Ventas no de mercado**: excluidas del análisis de precios (`sales_type_valido=False`) pero incluidas en volumen total.
