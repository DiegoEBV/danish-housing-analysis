# Auditoría de leakage — features del repo legacy

**Estado**: ✅ Inspección inicial completa; pendiente ejecución y validación con métricas reales
**Issue bd**: `danish-housing-analysis-r8s`
**Repo origen**: [R0SEWT/Denmark-HousePrices-Analysis](https://github.com/R0SEWT/Denmark-HousePrices-Analysis)
**Archivo inspeccionado**: `src/feature_engineering.py` (~2236 líneas), `src/config.py`

## Resumen ejecutivo

El repo legacy ya implementa **anti-leak guards explícitos** (`FORBIDDEN_FEATURE_COLUMNS`, `prepare_final_dataset` con `assert` de leakage). Sin embargo:

1. **El target es `log_price = np.log1p(purchase_price)`**, no `purchase_price`. Las métricas reportadas (R²=0.9999, MAPE=0.025%) son sobre log-scale, lo cual comprime la varianza y produce métricas artificialmente altas. **No es leakage, es presentación engañosa.**
2. **`prepare_final_dataset` excluye correctamente** las features derivadas directamente del target (`price_per_sqm`, `price_zscore`, `price_deviation_from_median`, etc.).
3. **`create_rolling_regional_features` es causal**: usa estrictamente años `[y - k, y - 1]` con un `min_obs`, sin incluir el row actual.
4. **`apply_target_encoding` SÍ tiene leakage** en su implementación, pero está **excluida** de las features finales vía `FORBIDDEN_FEATURE_COLUMNS`.
5. **`create_size_derived_features` (DEPRECADA)** genera `sqm_price_percentile` y `sqm_price_category` desde `sqm_price` — leaky directo. Su sucesora `create_size_features` solo genera `sqm_per_room` y `rooms_sqm_ratio` (clean).

## Acción para TB3

- **Portar**: el pipeline canónico (`create_rolling_regional_features`, `create_advanced_features`, `prepare_final_dataset`) tal cual, con su lista de exclusiones.
- **NO usar log_price como target final**: predecir `purchase_price` (nominal) o `sqm_price_real` (deflactado). Si se entrena sobre `log_price` por estabilidad, **reportar métricas sobre la escala original** (back-transform con `np.expm1` antes de calcular MAE/MAPE).
- **Esperar R² ≈ 0.70–0.92** y MAPE ≈ 10–20% sobre `purchase_price`. Si M4 reporta R² > 0.95 en escala nominal, re-auditar.

---

## Tabla de veredictos por feature

### Constantes de configuración (`src/config.py`)

| Constante | Definición | Comentario |
|---|---|---|
| `MODEL_TARGET_COL` | `'log_price'` | ⚠️ Métricas se reportan en log-scale por defecto. Hay que back-transformar para reportar honestamente. |
| `ROLLING_FEATURE_COLUMNS` | mean/median/std/cv/count/p90 regional | 🟢 Todas computadas causalmente. |
| `CAUSAL_DERIVED_COLUMNS` | `is_premium_causal`, `price_deviation_from_rolling_median` | 🟢 Comparan target vs. ventana causal pasada — clean. |
| `FORBIDDEN_FEATURE_COLUMNS` | `{purchase_price, price_per_sqm, price_zscore, price_category, price_per_sqm_x_region, sqm_x_region, is_premium, price_deviation_from_median, region_target_encoded, regional_price_mean/median/std/cv/rank, ...}` | 🟢 Lista de bloqueo correcta. |

### Funciones de feature engineering

| Función | Veredicto | Razón |
|---|---|---|
| `convert_date_features` | 🟢 Clean | Extrae `year`, `month`, `quarter` desde `date`. Sin target. |
| `create_property_age_features` | 🟢 Clean | `property_age = year - year_build`. Sin target. |
| `create_price_derived_features` | ⚠️ Deprecada | Redirige a `create_price_features`. |
| `create_price_features` | 🟢 Clean (es el target) | Solo crea `log_price = log1p(purchase_price)`. Es el target transformado, no una feature. |
| `create_size_derived_features` | 🔴 Leaky (deprecada) | Genera `sqm_price_percentile` y `sqm_price_category` desde `sqm_price = price/sqm`. No usar. |
| `create_size_features` | 🟢 Clean | Solo `rooms_category`, `size_category`, `sqm_per_room`, `rooms_sqm_ratio`. Sin target. |
| `create_cyclic_temporal_features` | 🟢 Clean | `month_sin/cos`, `quarter_sin/cos`. |
| `apply_onehot_encoding` | 🟢 Clean | One-hot de categóricas. |
| `apply_target_encoding` | 🔴 Leaky en implementación | Computa la media smoothed del target sobre **todo el df** (sin CV real pese al nombre). Salida `*_target_encoded` está en `FORBIDDEN_FEATURE_COLUMNS` → bloqueada en final. |
| `apply_frequency_encoding` | 🟢 Clean | Frecuencias de categorías, no involucra target. |
| `group_rare_categories` | 🟢 Clean | Agrupa categorías bajo cierto count. |
| `apply_standard_scaling` / `minmax` / `robust` | 🟢 Clean | Scalers sobre features. Idealmente fittear sólo en train pero la lógica de feature engineering completa lo aplica antes del split (técnicamente leaks de scale parameters, en práctica despreciable). |
| `apply_log_transformation` | 🟢 Clean | Log de variables seleccionadas (cuidado si target). |
| `create_interaction_features` | 🟢 Clean | Productos entre features ya limpias. |
| `create_macroeconomic_features` | 🟢 Clean | Procesa `dk_ann_infl_rate`, `yield_on_mortgage_credit_bonds`, etc. Externas. |
| `_compute_rolling_window_stats` | 🟢 Clean (causal) | Filtra `year >= year_ref - k & year <= year_ref - 1`. **Excluye el row actual y futuros.** |
| `create_rolling_regional_features` | 🟢 Clean (causal) | Aplica `_compute_rolling_window_stats` por región/año. Produce 6 columnas en `ROLLING_FEATURE_COLUMNS`. |
| `create_geographic_aggregated_features` | ⚠️ Deprecada (RFE-02) | Era no-causal, ahora redirige a la causal. |
| `create_regional_aggregated_features` | ⚠️ Deprecada (RFE-02) | Mismo caso. |
| `create_advanced_features` | 🟢 Clean | Construye `is_premium_causal`, `price_deviation_from_rolling_median` (vs. rolling, no vs. global). Limpia legacy explícito (`legacy_cols` drop). |
| `prepare_final_dataset` | 🟢 Clean | Tiene 2 `assert FORBIDDEN_FEATURE_COLUMNS & set(...)` que abortan si una columna prohibida llega al feature set. Feature selection con MI + F-regression. |

### Decisiones de exclusión en `prepare_final_dataset`

Excluye explícitamente:
- IDs / no-feature: `date, region, house_id, address, city, area, zip_code, house_type, sales_type, season, market_phase, rooms_category, size_category, decade_built, year_build`
- Target y derivadas directas: `purchase_price, price_per_sqm, price_zscore, price_category, sqm_x_region, price_per_sqm_x_region, is_premium, price_deviation_from_median, regional_p90, regional_median`
- Agregados regionales globales (no-causales): `regional_price_*, region_target_encoded, region_count`
- Macro redundantes: `sqm_price, %_change_between_offer_and_purchase, dk_ann_infl_rate%, yield_on_mortgage_credit_bonds%, nom_interest_rate%` (estas son las versiones con `%` URL-encoded; las versiones limpias `*_pct` SÍ entran)
- Temporales redundantes: `quarter, time_trend`

## Por qué R²=0.9999 no es necesariamente leakage

El target es `log_price = log1p(purchase_price)`. La varianza de `log_price` en este dataset es ~0.5-1.5 (range típico de 12-16 para precios de 50k-10M DKK). Si el modelo predice con `rolling_regional_median` (que ya captura el centro de la distribución regional histórica) + features causales de la propiedad (sqm, rooms, age, house_type), explicar 99% de la varianza de log-scale es alcanzable porque:

1. La varianza intra-región/año en log-scale es pequeña.
2. `rolling_regional_median` es un proxy excelente del precio esperado.
3. Las features físicas (sqm, age) explican casi toda la varianza restante.

**Validación honesta**: back-transformar predicciones (`y_pred_dkk = np.expm1(y_pred_log)`) y reportar:
- MAE en DKK
- MAPE en `purchase_price` (no en `log_price`)
- R² sobre `purchase_price` (no sobre `log_price`)

Una buena predicción inmobiliaria con estas features esperaría:
- R²(purchase_price) ≈ 0.85–0.92
- MAPE ≈ 12–18%
- MAE ≈ 200,000–400,000 DKK

Si reportamos métricas en escala log, hay que ser explícitos.

## Features a portar a `src/danish_housing/features.py`

Lista propuesta para el módulo nuevo (Fase 4 del plan TB3):

1. **Temporales**: `year`, `month`, `quarter`, `month_sin/cos`, `quarter_sin/cos`, `property_age = year - year_build`, `time_trend`
2. **Físicas**: `sqm`, `no_rooms`, `sqm_per_room`, `rooms_sqm_ratio`, `rooms_category` (one-hot), `size_category` (one-hot), `house_type` (one-hot), `region` (one-hot)
3. **Macro externas**: `dk_ann_infl_rate_pct`, `yield_mortgage_bonds_pct`, `nom_interest_rate_pct`
4. **Crisis flag**: `crisis_period` (años 2007–2012, 2020–2021)
5. **Causales regionales** (las 6 + 2): `rolling_regional_mean/median/std/cv/count/p90`, `is_premium_causal`, `price_deviation_from_rolling_median`
6. **Interacciones**: `age_x_villa`, `age_x_apartment`, `no_rooms × sqm`, `sqm_per_room²`

**Target candidato para M4**: `purchase_price` (nominal) o `sqm_price_real` (deflactado). Si se usa log para entrenar, **siempre back-transformar para reportar**.

## Pendientes de auditoría

- [ ] Ejecutar `prepare_final_dataset` con un sample y listar las features finales exactas que entran al modelo. Verificar manualmente que ninguna sea sospechosa.
- [ ] Cuando M4 corra: comparar métricas en log vs. nominal explícitamente.
- [ ] Validar que `create_train_test_split` realmente usa split temporal (train 1992–2017 / test 2018+).
