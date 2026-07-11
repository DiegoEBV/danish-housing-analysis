# Metodología de Modelado y Análisis — Danish Housing

**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024
**Entrega**: TB3 — Preprocesamiento, Modelado y Métricas

> **Alcance de este documento**: describe el **diseño y las decisiones metodológicas** del modelado (el *porqué*). Los **resultados numéricos** (métricas por modelo, tablas de holdout y CV, importancia de features) viven en [`reporte-metricas-tb3.md`](reporte-metricas-tb3.md), que es la fuente autoritativa de los números. La implementación de referencia es `scripts/run_modeling.py` + `src/danish_housing/features.py`.

---

## Tipo de Problema

**Regresión supervisada**: predecir el **precio nominal de transacción `purchase_price` (DKK)** de una vivienda residencial danesa en función de características de la vivienda, ubicación y contexto macroeconómico.

- El modelo se **entrena sobre `log1p(purchase_price)`** por estabilidad numérica (la distribución de precios está fuertemente sesgada a la derecha), pero **todas las métricas se reportan en escala nominal DKK** vía back-transform `np.expm1(...)`. No se reportan métricas en log-scale: esa práctica infla artificialmente el R² por la compresión de varianza (fue precisamente el defecto del pipeline legacy — ver `docs/legacy-leakage-audit.md`).
- **Por qué el target es `purchase_price` y no `sqm_price_real`**: predecir el precio/m² deflactado suele dar un R² ~0.1–0.15 mayor (target con menor varianza), pero se optó por el precio total para que las métricas sean directamente interpretables y consistentes con el dashboard de Tableau. Además, `sqm_price_real` es **función directa del target** y se excluye por leakage (ver más abajo).

> **Nota**: El enfoque es **descriptivo-predictivo, no causal**. Identificamos variables asociadas al precio; no establecemos causalidad.

---

## Feature Engineering

El set final es de **41 features**, construido en `src/danish_housing/features.py` (portado y auditado del repo legacy `R0SEWT/Denmark-HousePrices-Analysis`). Todas las features son **causales por construcción** — no incorporan información del futuro ni derivadas del target.

| Categoría | Features (ejemplos) | Justificación |
|---|---|---|
| Temporales | `year`, `month`, `quarter_num`, `month_sin/cos`, `quarter_sin/cos`, `property_age`, `crisis_period`, `time_trend` | Tendencia y estacionalidad; codificación cíclica para meses/trimestres |
| Físicas | `sqm`, `no_rooms`, `year_build`, `sqm_per_room`, `rooms_sqm_ratio` e interacciones | Determinantes primarios del precio |
| Categóricas one-hot | `region` (4), `house_type` (5), `rooms_category` (3), `size_category` (2) | Baja cardinalidad — Hipótesis H2 (región) y H3 (tipología) |
| Frequency encoding | `city_frequency`, `zip_code_frequency`, `sales_type_frequency` | Alta cardinalidad (~cientos de zips) colapsada a 1 columna sin one-hot explosivo |
| Macro externas | `nom_interest_rate_pct`, `dk_ann_infl_rate_pct`, `yield_mortgage_bonds_pct` | Hipótesis H1: tasas y costo de financiamiento danés |
| Causales regionales (rolling) | `rolling_regional_{mean, median, std, cv, count, p90}` | Contexto de precio regional usando **solo años `[y-12, y-1]`**, excluyendo la fila actual → sin leakage |
| Interacciones | `age × house_type` | Solo sobre features limpias |

### Anti-leakage (decisión metodológica clave)

En la primera corrida se detectó que `sqm_price_real` (precio/m² deflactado) alcanzaba `feature_importance ≈ 0.56` y producía un **R²=0.97 falso**: es función directa del target (`purchase_price / sqm × cpi_factor`). Se estableció una lista `FORBIDDEN_FEATURE_COLUMNS` en `features.py:38` que bloquea el target y todas sus derivadas (`sqm_price`, `sqm_price_real`, `price_zscore`, regionales que incluyen precio, `%_change_between_offer_and_purchase`, IDs y flags de Silver).

El guard es **activo, no documental**: `build_feature_matrix` lanza `AssertionError` si cualquier columna prohibida entra al set de features (`features.py:348`). El flag `leakage_check_passed=True` solo se alcanza si la corrida no aborta. El resultado quedó en **41 features limpias, 16 columnas excluidas**.

---

## Modelos Evaluados

Se entrenaron **4 modelos** de complejidad creciente. La comparación establece si el problema es de multicolinealidad, de no-linealidad, o del techo del feature set.

### M1 — Regresión Lineal (baseline)
`LinearRegression` sobre `log1p(purchase_price)`. Piso mínimo de rendimiento; coeficientes interpretables. Se espera que subajuste porque el mercado tiene relaciones no lineales.

### M2 — Ridge (regularizado)
`Ridge(alpha=1.0)`. Misma estructura lineal que M1 con penalización L2 para controlar la multicolinealidad entre las macro (`nom_interest_rate`, `dk_ann_infl_rate`, `yield_mortgage_bonds`). Si mejora sobre M1 → el problema era multicolinealidad; si no → es no-linealidad (justifica M3/M4).

### M3 — Random Forest
`RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1)`. Sin supuestos sobre la forma funcional; captura interacciones. Con `max_depth=12` **subajusta** (train R² ≈ 0.42), y subir la profundidad degrada el test por overfitting.

### M4 — XGBoost + Optuna (**modelo seleccionado**)
`XGBRegressor` (`tree_method="hist"`, CUDA en GPU NVIDIA L4). Hiperparámetros optimizados con **Optuna (30 trials, sampler TPE)** usando una CV interna de 3 folds sobre RMSE en log-scale. Best: `n_estimators=700, max_depth=10, lr=0.099, subsample=0.97, colsample_bytree=0.73, reg_alpha=0.064, reg_lambda=1.58`.

**Por qué gana M4**: captura interacciones complejas (`sqm × region × era`) con learning rate bajo + regularización L1/L2, generalizando mejor que RF. La selección de campeón es automática por **mejor `test_r2`** en el holdout (`run_modeling.py:342`), y M4 gana **6/6** (5 folds CV + 1 holdout).

---

## Validación

### Estrategia de split — **temporal, no aleatorio**

El split es **temporal estricto** (`features.py:380` `temporal_train_test_split`), no un `train_test_split` aleatorio:

```
Train: años ≤ 2017   → 893,181 filas
Test:  años ≥ 2018   → 614,727 filas
```

**Por qué temporal y no aleatorio**: un split aleatorio en datos temporales **leakea el futuro al train** (habría transacciones de 2020 en train prediciendo transacciones de 2019). El split temporal reproduce el escenario realista de producción: entrenar con el pasado y predecir el futuro. El costo es un **distribution shift severo** — el test cae en el boom post-COVID (precios +30–50% en 4 años, tasas bajas), un régimen que el train 1992–2017 nunca vio. Ese shift es la razón principal de un R² modesto, y es **deliberado y honesto**, no un defecto.

### Cross-validation — `TimeSeriesSplit`

`TimeSeriesSplit(n_splits=5)` **dentro del train 1992–2017**, con ventana expandida (cada fold entrena con el histórico acumulado y valida en el bloque siguiente) — `run_modeling.py:207`. Mide la **varianza del modelo a través del tiempo**; NO se usa `KFold` aleatorio por la misma razón que el split principal.

### Métricas de evaluación (escala nominal DKK)

| Métrica | Interpretación en contexto |
|---|---|
| R² | % de varianza del precio explicado por el modelo |
| MAE | Error promedio en DKK — directamente entendible por un inversor |
| RMSE | Penaliza errores grandes → detecta subvaluaciones extremas en propiedades caras |
| MAPE | Error % — comparable entre regiones con escalas de precio distintas |

> Los valores concretos de estas métricas por modelo (holdout y CV) están en [`reporte-metricas-tb3.md`](reporte-metricas-tb3.md). Resumen ejecutivo: el campeón M4 logra **test R²=0.44** (vs. 0.25 del baseline lineal), con errores absolutos grandes en el segmento de propiedades caras (RMSE ≫ MAE) — limitación discutida en el reporte.

---

## Hipótesis y cómo el modelo las aborda

| Hipótesis | Evidencia en el modelado |
|---|---|
| **H1**: el volumen reacciona a las tasas/bonos (rezago ~2Q) | `yield_mortgage_bonds_pct` como feature + correlación con lag en `mart_macro_correlation` |
| **H2**: Copenhague más resiliente ante shocks | one-hot `region_*` con alta importancia + drawdowns menores en la capital (`mart_drawdowns`) |
| **H3**: summerhouses con drawdowns más profundos | `house_type_Summerhouse` es la feature #1 en importancia + análisis en `mart_drawdowns` |

> Sobre H2, ver también la nota de **circularidad** en la metodología de segmentación (`segmentation-pca-clustering-methodology.md`): las features derivadas de precio ya correlacionan con la región, por lo que "redescubrir" la división capital/provincias es *consistente* con H2, no una confirmación independiente.

---

## Limitaciones del Modelo

1. **R²=0.44 nominal** es modesto en absoluto, pero honesto y reproducible con el anti-leak guard. El techo real del feature set ronda R²≈0.5 incluso en períodos estables (ver CV en el reporte).
2. **Distribution shift 2018–2024**: el test cae en un régimen (boom post-COVID) que el train nunca vio.
3. **Errores absolutos grandes en propiedades caras** (RMSE ≫ MAE): el modelo sirve para *ranking* riesgo-retorno y análisis agregado, **no para pricing exacto** de una vivienda individual.
4. **Sin datos hiperlocales**: no hay vecindad específica, calidad de construcción, renovaciones ni distancia a transporte; con datos catastrales/embeddings de dirección el R² subiría a 0.7–0.8.
5. **Período 1992–1994** (`periodo_preliminar`) y **2023–2024** (macro nulos) tienen menor completitud.
6. **No causal**: correlaciones con macro no implican causalidad. No usar para decisiones financieras reales.
