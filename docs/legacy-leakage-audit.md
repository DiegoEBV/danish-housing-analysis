# Auditoría de leakage — features del repo legacy

**Estado**: 🔄 En curso (Fase 3 del plan de refactor TB3)
**Issue bd**: `danish-housing-analysis-r8s`
**Repo origen**: [R0SEWT/Denmark-HousePrices-Analysis](https://github.com/R0SEWT/Denmark-HousePrices-Analysis)

## Motivación

El repo legacy reporta R²=0.9999 / MAPE=0.025% para XGBoost+Optuna sobre el dataset de Kaggle de vivienda danesa. Una métrica tan perfecta en datos de mercado inmobiliario es señal casi segura de **data leakage** — alguna feature en el conjunto de entrenamiento contiene información del target (`purchase_price`).

Antes de portar features a este proyecto, hay que decidir cuáles son legítimas y cuáles deben descartarse.

## Target del proyecto

El target predicho es **`purchase_price`** (precio nominal de transacción en DKK). Cualquier feature derivada del precio de la misma fila, o agregada incluyendo la fila misma, es leaky.

## Sospechosos identificados (por inspección)

| Feature | Veredicto preliminar | Razón |
|---|---|---|
| `price_per_sqm` (= `purchase_price / sqm`) | 🔴 Leaky directo | Es función del target. Cualquier modelo con esta feature puede recuperar el target multiplicando por `sqm`. |
| `price_deviation_from_regional_median` | 🟡 Borderline | Si la mediana se calcula sobre la región **incluyendo la fila misma**, hay fuga. Si se computa con leave-one-out o sobre el split de train antes del test, es defendible. |
| `region_avg_price_yearly` | 🟡 Borderline | Mismo problema: agregación que potencialmente incluye la fila. Requiere computar sobre train-only y mapear al test sin recalcular. |
| `rolling_mean_price_12m` (zip_code) | 🔴 Leaky si incluye el row actual | Ventana rolling que toca el target del row es fuga. Debe ser estrictamente shifted: usar transacciones **anteriores** a la fecha del row. |
| `is_capital`, `region_encoding` | 🟢 Clean | Geográficas estáticas. |
| `year`, `quarter`, `month_sin/cos` | 🟢 Clean | Temporales del row. |
| `sqm`, `rooms`, `year_build`, `house_type` | 🟢 Clean | Características físicas de la propiedad. |
| `dk_ann_infl_rate_pct`, `yield_mortgage_bonds_pct` | 🟢 Clean | Macro externas, no derivadas del target. |
| `nom_interest_rate_pct` | 🟢 Clean | Macro externa. |
| `pct_change_offer_purchase` | 🔴 Leaky | Diferencia % entre precio oferta y precio compra — incluye `purchase_price` en el numerador. |

## Plan de auditoría (pendiente)

1. **Clonar el legacy localmente** (o leer raw desde GitHub) y abrir `src/feature_engineering.py`.
2. **Listar exhaustivamente** todas las features generadas + su fórmula.
3. **Clasificar** cada una: `clean` / `leaky` / `borderline` (con justificación).
4. **Definir set final** de features importables. Para borderline, definir el **método de cómputo seguro** (e.g., aggregaciones sólo sobre train).
5. **Documentar** los descartes con razón explícita aquí.

## Criterio de "no leakage"

Una feature es **clean** si y sólo si:

1. **No es función del target** del mismo row (directa o indirecta).
2. Si es agregación, **se computa sobre el split de train** y se mapea al test sin recalcular incluyendo test rows.
3. Si es temporal/rolling, **usa estrictamente datos anteriores** a la fecha del row (shifted, no centered).
4. Si depende de la fecha futura (e.g., precios futuros mismos), está prohibida.

## Validación posterior al import

Tras importar features y entrenar M4 (XGBoost+Optuna):

- Si R² > 0.95 en test, **re-auditar**. Probable que algo siga leaky.
- Si R² ≈ 0.70-0.85, es una señal saludable para este dataset y problema.
- Si R² < 0.50, revisar feature set y/o split temporal.

## Decisiones tomadas

_(Llenar conforme se ejecute la auditoría)_

- _Fecha:_ _veredicto:_ _justificación:_
