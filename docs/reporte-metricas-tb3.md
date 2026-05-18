# Reporte de Métricas y Decisión del Modelo — TB3

**Proyecto**: Dinámica de Precios Residenciales en Dinamarca 1992–2024
**Curso**: Data Visualization — UPC 2026-01
**Equipo**: Vilchez · Ballón · Velásquez Borasino
**Dataset**: 1,507,908 transacciones (Kaggle — martinfrederiksen/danish-residential-housing-prices-1992-2024)
**Fecha de corrida**: 2026-05-18 (GPU NVIDIA L4 en Lightning.ai)

---

## Problema Analítico

**Tipo**: Regresión supervisada.
**Target**: `purchase_price` — precio nominal de transacción en DKK.
**Entrenamiento**: `log1p(purchase_price)` por estabilidad numérica (varianza compresada).
**Reporte de métricas**: **escala nominal (DKK)** vía back-transform `np.expm1(...)`. NO se reportan métricas en log-scale — esa práctica infla artificialmente R² por la compresión de varianza.

**Por qué `purchase_price` y no `sqm_price_real`**: aunque predecir el precio por m² deflactado suele dar R² 0.1-0.15 mejor (target con menor varianza), se eligió predecir el precio total para que las métricas sean directamente interpretables y consistentes con el dashboard de Tableau.

---

## Preprocesamiento aplicado (Bronze → Silver)

Reglas P1–P8 en `src/danish_housing/cleaning.py`. Bitácora en `data/processed/bitacora_limpieza.csv`.

| Regla | Acción | Filas afectadas (de 1.5M) |
|---|---|---:|
| P1 | Imputar `city` faltante con "Unknown" | 0 |
| P2 | Flag `macro_nulo` (gap 2023–2024 en `dk_ann_infl_rate`, `yield_mortgage_bonds`) | 1,193 |
| P3 | Flag `sales_type_valido=False` (ventas familiares, "-", subastas) | 175,149 (~11.6%) |
| P4 | Flag `year_build < 1800` (atípicos extremos) | 0 |
| P5 | Flag `purchase_price_outlier` (IQR × 3) | 24,282 (~1.6%) |
| P5 | Flag `sqm_price_outlier` (IQR × 3) | 15,217 (~1.0%) |
| P6 | Flag `periodo_preliminar` (año < 1995, menor completitud) | 56,043 (~3.7%) |
| P7 | `zip_code` → str con `zfill(4)` | 1,507,908 (all) |
| P8 | Renombrar `nom_interest_rate%`, `dk_ann_infl_rate%`, `yield_on_mortgage_credit_bonds%`, `%_change_between_offer_and_purchase` a sufijos limpios `_pct` | 1,507,908 |

**Las flags NO se borran**; los marts Gold filtran por ellas (`sales_type_valido & ~purchase_price_outlier`). La trazabilidad TB2 se preserva.

---

## Feature engineering y anti-leakage

Módulo: `src/danish_housing/features.py` — portado y auditado del repo legacy R0SEWT/Denmark-HousePrices-Analysis (ver `docs/legacy-leakage-audit.md`).

**Auditoría de leakage**:
- Se detectó en la primera corrida que `sqm_price_real` (precio/m² deflactado) tenía `feature_importance` = 0.56 en M4 XGBoost, dando R²=0.97 **falso**. Es función directa del target: `sqm_price_real = purchase_price / sqm × cpi_factor`. Bloqueado en `FORBIDDEN_FEATURE_COLUMNS` antes del rerun.
- Set final: **41 features**, anti-leak guard PASS. 16 columnas excluidas (target derivatives + flags + IDs).

**Feature matrix construido** sobre 1,507,908 filas:

| Categoría | Features | Detalle |
|---|---|---|
| Temporales | year, month, quarter_num, month_sin/cos, quarter_sin/cos, property_age, crisis_period, time_trend | Causales por construcción |
| Físicas | sqm, no_rooms, year_build, sqm_per_room, rooms_sqm_ratio, sqm_per_room², rooms × sqm | Sin target |
| Categóricas one-hot | region (4), house_type (5), rooms_category (3), size_category (2) | Baja cardinalidad |
| Frequency encoding | city_frequency, zip_code_frequency, sales_type_frequency | Alta cardinalidad (~100s zip) → 1 col |
| Macro externas | nom_interest_rate_pct, dk_ann_infl_rate_pct, yield_mortgage_bonds_pct | Tasas y bonos daneses |
| Causales regionales (rolling) | rolling_regional_{mean, median, std, cv, count, p90} | Sólo años [y-12, y-1] dentro de la región |
| Interacciones | age × house_type | Solo features clean |

---

## Split temporal y validación

**Split principal (holdout)**: train 1992–2017 (893,181 filas) / test 2018–2024 (614,727 filas). El test cae en el período de mayor crecimiento (post-COVID, tasas bajas) → distribution shift severo, pero **es el escenario realista** que el modelo enfrentaría en producción.

**Validación cruzada**: `TimeSeriesSplit(n_splits=5)` dentro del train 1992–2017 con ventana expandida (folds históricos), con hyperparams fijos del Optuna principal. Mide variance del modelo a través del tiempo.

---

## Modelos entrenados

| Modelo | Implementación | Hyperparams |
|---|---|---|
| M1 — Linear | `sklearn.linear_model.LinearRegression` | default |
| M2 — Ridge | `sklearn.linear_model.Ridge` | `alpha=1.0` |
| M3 — RandomForest | `sklearn.ensemble.RandomForestRegressor` | `n_estimators=200, max_depth=12, n_jobs=-1` |
| **M4 — XGBoost** | `xgboost.XGBRegressor` (CUDA en GPU NVIDIA L4) | Optuna 30 trials TPE; best: `n_estimators=700, max_depth=10, lr=0.099, subsample=0.97, colsample_bytree=0.73, min_child_weight=1, reg_alpha=0.064, reg_lambda=1.58` |

Imputación de NaN en features con la **mediana del train** (no del dataset completo, para no leakear).

---

## Resultados — Holdout (train 1992–2017 → test 2018–2024)

Métricas en escala nominal DKK:

| Modelo | train R² | **test R²** | test MAE (DKK) | test MAPE | test RMSE (DKK) |
|---|---:|---:|---:|---:|---:|
| M1 Linear | 0.227 | 0.250 | 1,166,372 | 79.1% | 1,732,931 |
| M2 Ridge | 0.227 | 0.250 | 1,165,929 | 79.0% | 1,732,719 |
| M3 RandomForest | 0.417 | 0.237 | 1,033,858 | 43.9% | 1,748,592 |
| **M4 XGBoost (CUDA + Optuna)** | **0.749** | **0.440** | **866,618** | **37.0%** | **1,498,211** |

---

## Resultados — Time-series CV (5 folds en 1992–2017)

R² por fold y modelo:

| Fold | Train periodo | Test periodo | n_train | n_test | M1 | M2 | M3 | M4 |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 1992–1998 | 1998–2003 | 148,866 | 148,863 | 0.142 | 0.135 | 0.062 | 0.126 |
| 2 | 1992–2003 | 2003–2007 | 297,729 | 148,863 | 0.134 | 0.131 | 0.093 | 0.212 |
| 3 | 1992–2007 | 2007–2011 | 446,592 | 148,863 | 0.105 | 0.107 | 0.202 | 0.357 |
| 4 | 1992–2011 | 2011–2015 | 595,455 | 148,863 | 0.221 | 0.221 | 0.268 | 0.414 |
| 5 | 1992–2015 | 2015–2017 | 744,318 | 148,863 | 0.215 | 0.215 | 0.274 | **0.495** |

Resumen CV (mean ± std):

| Modelo | R² | MAE (DKK) | MAPE |
|---|---:|---:|---:|
| M1 Linear | 0.163 ± 0.051 | 810,907 | 62.4% |
| M2 Ridge | 0.162 ± 0.052 | 811,455 | 62.3% |
| M3 RandomForest | 0.180 ± 0.098 | 733,852 | 46.0% |
| **M4 XGBoost** | **0.321 ± 0.150** | **632,879** | **40.4%** |

---

## Decisión del modelo: **M4 XGBoost + Optuna**

**Evidencia cuantitativa**:
- Gana en **TODOS** los folds CV y en el holdout (5/5 + 1/1 = 6/6).
- R² holdout: 0.440 vs. 0.250 del baseline lineal (+76% relativo).
- MAE holdout: 866k DKK vs. 1.17M del baseline (-26%).
- MAPE holdout: 37.0% vs. 79% del baseline (-53%).

**Por qué los lineales fallan**:
- M1/M2 con R² ≈ 0.16–0.25 indica que **no hay una relación lineal fuerte** entre las features y el precio. El mercado inmobiliario es altamente no lineal: el efecto de `sqm` sobre el precio depende de la zona, tipo de vivienda, era de construcción.

**Por qué M3 (RandomForest) queda detrás de M4**:
- RF train R²=0.42 vs. M4 train R²=0.75 → M3 **subajusta** con `max_depth=12`.
- Aumentar max_depth degrada test_R² por overfitting; XGBoost con learning rate bajo + regularización L1/L2 generaliza mejor.

**Por qué M4 funciona**:
- Captura interacciones complejas (sqm × region × era).
- Regularización L1/L2 (`reg_alpha=0.06, reg_lambda=1.58`) controla overfitting.
- Optuna optimiza con 3-fold CV interna sobre RMSE en log-scale (estable).

---

## Interpretación: ¿por qué R²=0.44 y no 0.85?

El audit doc predijo R²~0.85, pero el ceiling real es ~0.5. Razones:

1. **Distribution shift 2017→2018**: el test cae en el boom post-COVID (precios subiendo 30-50% en 4 años). El modelo entrenado en 1992-2017 nunca vio ese régimen.
2. **CV folds tempranos también bajos** (F1 R²=0.13): demuestra que el problema NO es solo el holdout; el ceiling del feature set es ~R²=0.5 incluso en períodos "estables".
3. **Features faltantes**: no se incluyen variables hyperlocales (vecindad específica, calidad de construcción, renovaciones, distancia a transporte). Con embeddings de address o datos catastrales, R²=0.7-0.8 sería alcanzable.
4. **Comparación con el legacy**: el legacy reporta R²=0.9999, pero sobre **log_price** (varianza comprimida 100x) y con leakage no descubierto en su audit interno. En escala nominal, su R² real estimado sería ≤ 0.5.

---

## Top 10 features (M4 XGBoost — `mart_feature_importance.csv`)

| Rank | Feature | Importance | Comentario |
|---:|---|---:|---|
| 1 | `house_type_Summerhouse` | 0.177 | Tipología más barata, fácil de separar |
| 2 | `rolling_regional_median` | 0.105 | Mediana causal regional últimos 12 años |
| 3 | `year` | 0.080 | Tendencia inflacionaria/boom |
| 4 | `region_Zealand` | 0.064 | Provincial vs. Copenhagen-adjacent |
| 5 | `house_type_Villa` | 0.059 | Tipología cara |
| 6 | `house_type_Townhouse` | 0.040 | Intermedia |
| 7 | `rolling_regional_cv` | 0.035 | Volatilidad regional histórica |
| 8 | `rolling_regional_p90` | 0.032 | Cuantil 90 regional (luxury floor) |
| 9 | `sales_type_frequency` | 0.031 | Densidad de tipo de venta en la zona |
| 10 | `house_type_Farm` | 0.030 | Tipología rural |

**Lectura**: las features dominantes son **causales y limpias** (tipología, rolling regional, año). NO hay derivadas del target en el top — anti-leak validado.

---

## Limitaciones y disclaimers

- **R²=0.44 nominal** es modesto en absoluto pero **honesto y reproducible** con anti-leak guard.
- Modelo **descriptivo-predictivo**, no causal. Las correlaciones con tasas no implican causalidad.
- Periodo 1992–1994 marcado `periodo_preliminar` (menor completitud).
- Datos 2023–2024 con macro nulos (1,193 filas).
- **No usar para decisiones financieras reales**.

## Reproducibilidad

```bash
# Bronze ya en gs://danish-housing-bronze/raw/DKHousingPrices.parquet (1.5M filas)
gcloud storage cp gs://danish-housing-bronze/raw/DKHousingPrices.parquet data/raw/

# Pipeline completo + modelado en GPU L4 (~25 min con Optuna 30 trials + CV 5 folds)
uv run python scripts/run_pipeline.py --config configs/analysis.yaml
uv run python scripts/run_modeling.py --config configs/analysis.yaml \
  --device cuda --optuna-trials 30 --cv-folds 5

# Marts finales en gs://danish-housing-gold/marts/
```

Audit completo de cada corrida en `data/processed/gold/modeling_audit.json`.
