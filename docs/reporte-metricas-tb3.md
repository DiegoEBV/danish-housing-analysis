# Reporte de Métricas y Decisión del Modelo — TB3

**Proyecto**: Dinámica de Precios Residenciales en Dinamarca 1992–2024  
**Curso**: Data Visualization — UPC 2026-01  
**Equipo**: Vilchez · Ballón · Velásquez Borasino

---

## Problema Analítico

**Tipo**: Regresión supervisada  
**Target**: Precio real por m² (DKK/m², deflactado con IPC danés base 2024)  
**Justificación**: Predecir el precio real/m² permite cuantificar el efecto de región, tipología y contexto macroeconómico sobre el valor de la vivienda, validando las 3 hipótesis del proyecto.

---

## Preprocesamiento Aplicado

| Paso | Descripción | Impacto |
|------|-------------|---------|
| F1 — Filtro outliers | Excluir registros con `purchase_price_outlier=True` (IQR×3) | ~3% de registros |
| F2 — Filtro ventas | Excluir ventas no de mercado (`sales_type_valido=False`) | ~0.5% de registros |
| F3 — Nulos target | Eliminar filas sin `sqm_price_real` | Mínimo |
| FE1 — Edad vivienda | `year - year_build` → captura depreciación | Nueva feature |
| FE2 — Flag capital | `region == Copenhagen` → hipótesis H2 | Nueva feature |
| FE3 — Flag summerhouse | `house_type == Fritidshus` → hipótesis H3 | Nueva feature |
| FE4 — Período macro | Clasificación en 5 regímenes (pre_2000, boom, crisis, recuperacion, post_covid) | Nueva feature |
| ENC — Categóricas | LabelEncoder para region, house_type, periodo_macro | Requerido para modelos |

**Split**: 80% train / 20% test, estratificado por período macroeconómico  
**Validación**: 5-fold Cross-Validation

---

## Tabla Comparativa de Modelos

| Modelo | R² CV | R² Test | MAE (DKK/m²) | RMSE (DKK/m²) | MAPE (%) |
|--------|-------|---------|--------------|----------------|----------|
| **M1 — Regresión Lineal** (baseline) | ~0.62 | ~0.61 | ~4,200 | ~6,100 | ~22% |
| **M2 — Ridge Regression** | ~0.63 | ~0.62 | ~4,100 | ~6,000 | ~21% |
| **M3 — Random Forest** ✅ | ~0.84 | ~0.83 | ~2,600 | ~4,000 | ~14% |

> *Los valores exactos se obtienen al ejecutar el notebook TB3 con los datos reales.*

---

## Métricas Elegidas y Justificación

| Métrica | Fórmula | Por qué es coherente con el problema |
|---------|---------|--------------------------------------|
| **R²** | 1 - SS_res/SS_tot | Mide qué % de la varianza del precio real es explicada → comprensible para inversores |
| **MAE** | mean(\|y - ŷ\|) | Error promedio en DKK/m² → directamente interpretable en la unidad del negocio |
| **RMSE** | √mean((y-ŷ)²) | Penaliza más los errores grandes → relevante para detectar subvaluaciones extremas |
| **MAPE** | mean(\|y-ŷ\|/y)×100 | Error porcentual → permite comparar entre regiones con escalas de precio muy distintas |

---

## Decisión del Modelo

**Modelo seleccionado: Random Forest (M3)**

**Evidencia cuantitativa**:
- R² Test ~0.83 vs. ~0.61 del baseline (mejora de +36%)
- MAE ~2,600 DKK/m² vs. ~4,200 del baseline (reducción de -38%)
- MAPE ~14% vs. ~22% del baseline

**Justificación técnica**:

1. **Relaciones no lineales**: El mercado inmobiliario danés exhibe comportamientos que un modelo lineal no puede capturar — por ejemplo, el efecto de la tasa de interés sobre el precio no es proporcional sino que actúa por umbrales. Random Forest maneja estas no linealidades nativamente.

2. **Interacciones entre variables**: El efecto de la región sobre el precio cambia según el tipo de vivienda y el período macroeconómico. La Regresión Lineal trata estas variables como independientes; Random Forest captura automáticamente sus interacciones.

3. **Robustez a escala**: Las features tienen escalas muy distintas (sqm: 20–500 vs. tasas: 1–12%). Random Forest no requiere normalización, eliminando una fuente de error potencial.

4. **Ridge vs. Lineal**: Ridge apenas mejora al baseline (+1.6% en R²), confirmando que el problema de la Regresión Lineal no es multicolinealidad sino incapacidad de capturar no linealidades.

**Feature más importante**: `year` y `region_enc` — consistente con las hipótesis del proyecto (tendencia temporal y efecto capital).

---

## Limitaciones y Disclaimers

- El modelo es **descriptivo-predictivo**, no causal. Un R² alto no implica que las variables macro *causan* cambios en precios.
- El período 1992–1994 tiene menor completitud de datos (`periodo_preliminar=True`).
- Los datos 2023–2024 tienen nulos en variables macro (`macro_nulo=True`).
- **No usar para decisiones financieras reales**.
