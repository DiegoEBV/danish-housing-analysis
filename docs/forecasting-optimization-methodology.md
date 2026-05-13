# Metodología de Modelado y Análisis — Danish Housing

**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024  
**Entrega**: TB3 — Preprocesamiento, Modelado y Métricas

---

## Tipo de Problema

**Regresión supervisada**: predecir el precio real por m² (DKK/m²) de una transacción residencial danesa en función de características de la vivienda, ubicación y contexto macroeconómico.

> **Nota importante**: El enfoque es **descriptivo-predictivo**, no causal. Identificamos variables asociadas al precio, pero no establecemos causalidad.

---

## Feature Engineering

### Variables base (del dataset Silver)

| Feature | Tipo | Justificación analítica |
|---------|------|------------------------|
| `sqm` | numérica | Determinante primario del precio total |
| `no_rooms` | numérica | Proxy de distribución interior |
| `year` | numérica | Captura tendencia temporal del mercado |
| `nom_interest_rate_pct` | numérica | Hipótesis H1: efecto de tasas sobre precios |
| `dk_ann_infl_rate_pct` | numérica | Necesaria para deflactar y comparar |
| `yield_mortgage_bonds_pct` | numérica | Hipótesis H1: costo de financiamiento |
| `region_enc` | categórica | Hipótesis H2: efecto capital vs. provincias |
| `type_enc` | categórica | Hipótesis H3: vulnerabilidad por tipología |

### Variables derivadas (feature engineering)

| Feature | Cálculo | Justificación |
|---------|---------|---------------|
| `edad_vivienda` | `year - year_build` | Captura depreciación y preferencia por construcción nueva |
| `es_capital` | `region == 'Copenhagen'` | Hipótesis H2: efecto Copenhague (binario más interpretable) |
| `es_summerhouse` | `house_type == 'Fritidshus'` | Hipótesis H3: vulnerabilidad summerhouse |
| `periodo_macro` | clasificación por rangos de año | Captura regímenes macroeconómicos distintos (boom, crisis, recuperación) |

---

## Modelos Evaluados

### M1 — Regresión Lineal (Baseline)

**Supuesto central**: relación lineal entre features y precio real/m².

```
sqm_price_real = β₀ + β₁·sqm + β₂·no_rooms + β₃·year + β₄·region_enc
               + β₅·type_enc + β₆·nom_interest_rate + ... + ε
```

**Por qué es el baseline**:
- Modelo más simple posible
- Coeficientes directamente interpretables
- Establece el piso mínimo de rendimiento que cualquier modelo más complejo debe superar

**Limitación esperada**: El mercado inmobiliario danés tiene relaciones no lineales (ej: el efecto de la región sobre el precio no es constante a través del tiempo). La Regresión Lineal no puede capturar estas interacciones.

---

### M2 — Ridge Regression (Regularizado)

**Supuesto**: misma estructura lineal que M1, pero con penalización L2 para controlar la multicolinealidad entre variables macroeconómicas.

```
Minimiza: ||y - Xβ||² + α·||β||²
```

**Por qué se evalúa**:
- Las variables `nom_interest_rate`, `dk_ann_infl_rate` y `yield_mortgage_bonds` tienen alta correlación entre sí (multicolinealidad)
- Ridge reduce la varianza de los coeficientes sin eliminar variables
- Si mejora sustancialmente sobre M1 → el problema era multicolinealidad
- Si no mejora → el problema es no-linealidad (→ justifica M3)

---

### M3 — Random Forest (Modelo Seleccionado)

**Supuesto**: ninguno sobre la forma funcional de la relación precio-features.

**Parámetros**:
```python
RandomForestRegressor(
    n_estimators=200,    # 200 árboles — balance entre sesgo y varianza
    max_depth=12,        # evita sobreajuste en árboles individuales
    min_samples_leaf=10, # requiere al menos 10 obs por hoja
    random_state=42
)
```

**Por qué es el modelo seleccionado**:

1. **No linealidad**: Captura relaciones no lineales entre región, año y precio (ej: el precio en Copenhague creció desproporcionadamente después de 2012 — efecto no lineal que la regresión no puede modelar)

2. **Interacciones**: El efecto de la tasa de interés sobre el precio varía según la región y el tipo de vivienda. Random Forest captura estas interacciones automáticamente sin necesidad de especificarlas

3. **Robustez**: No requiere normalización de features (a diferencia de Ridge) y es robusto a outliers residuales

4. **Importancia de variables**: Genera un ranking de importancia (Gini) que valida o refuta las hipótesis del proyecto

---

## Validación

### Estrategia de split

```
Total: ~1,450,000 registros (post-filtros Silver)
├── Train: 80% (~1,160,000)
└── Test:  20% (~290,000)

Estratificación: por periodo_macro (pre_2000, boom, crisis, recuperacion, post_covid)
→ Garantiza que cada período está representado en train y test
```

### Cross-validation

```
5-Fold KFold sobre el train set
→ Detecta overfitting sin tocar el test set
→ Media y desv. estándar del R² como indicadores de estabilidad
```

### Métricas de evaluación

| Métrica | Fórmula | Interpretación en contexto |
|---------|---------|--------------------------|
| R² | 1 - SSres/SStot | % de varianza del precio real explicado por el modelo |
| MAE | mean(\|y-ŷ\|) | Error promedio en DKK/m² — directamente entendible por inversores |
| RMSE | √mean((y-ŷ)²) | Penaliza errores grandes — relevante para detectar subvaluaciones extremas |
| MAPE | mean(\|y-ŷ\|/y)×100 | Error % — compara entre regiones con escalas de precio distintas |

---

## Hipótesis y Cómo el Modelo las Valida

| Hipótesis | Cómo se valida con el modelo |
|-----------|------------------------------|
| H1: Volumen reacciona negativamente a subida de tasas (rezago 1–2Q) | `yield_mortgage_bonds_pct` con lag → importancia en RF + correlación en `mart_macro_correlation` |
| H2: Copenhague más resiliente ante shocks | `es_capital` y `region_enc` → alta importancia en RF + drawdowns menores en Copenhagen |
| H3: Summerhouses con drawdowns más profundos | `es_summerhouse` → importancia en RF + análisis de drawdowns en `mart_drawdowns` |

---

## Limitaciones del Modelo

1. **Período 1992–1994**: menor completitud de datos puede sesgar predicciones para ese período
2. **2023–2024**: nulos en variables macro — el modelo no puede predecir bien con features faltantes
3. **Causalidad**: un R² alto no implica que las variables macro *causan* cambios en precios
4. **Extrapolación**: el modelo no debe usarse para predecir precios fuera del rango histórico
5. **Sin datos geoespaciales finos**: usamos región en vez de coordenadas exactas por simplicidad
