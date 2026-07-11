# Cheat-sheet de defensa — Sustentación

Respuestas enlatadas a los flancos metodológicos (revisión de riesgos previa a la entrega).
Fuente de números: `docs/reporte-metricas-tb3.md` + análisis sobre `data/marts/mart_predictions_sample.csv`.

---

## R² = 0.44 del modelo campeón (M4 XGBoost)

### El número y qué mide

| Métrica (holdout, escala nominal DKK) | Valor |
|---|---|
| test R² | **0.44** |
| test MAE | 866,618 DKK |
| test MAPE | 37.0% |
| test RMSE | 1,498,211 DKK |
| CV temporal R² | 0.32 ± 0.15 |

Es una **regresión cross-sectional a nivel de transacción individual** (una fila = una venta), validada **out-of-time** (train 1992–2017 → test 2018–2024). NO es el forecast de un índice agregado suave — bajo ese encuadre 0.44 sería pobre; bajo *este*, es modesto pero razonable y honesto.

### Dónde están realmente los errores (análisis por decil de precio)

El error NO es uniforme: se concentra en los extremos. El **mercado medio (deciles 3–6, ~1.1M–2.1M DKK), que es el grueso de las transacciones, tiene MAPE ~26%** y bias bajo. La degradación está en las colas:

| Decil precio | Precio medio | MAE | MAPE | Bias (y_true − y_pred) |
|---:|---:|---:|---:|---:|
| 1 (barato) | 479k | 378k | **90%** | −365k → **sobreestima** |
| 3–6 (medio) | 1.1M–2.1M | 273k–538k | **~26%** | bajo → **zona confiable** |
| 10 (caro) | 6.97M | 3.23M | 45% | **+3.18M → subestima** |

- **RMSE/MAE = 1.74** confirma la cola pesada.
- El **10% de filas con más error concentra el 42%** de la masa total de error.
- **Patrón sistemático**: sobreestima las baratas y subestima las caras (regresión a la media, típico de un modelo sin features hiperlocales). Los "montos considerables" están en el **segmento lujo** (villas en Zealand/Copenhague), no en el mercado medio.

> **Respuesta si preguntan "¿por qué errores de millones?"**: "Están concentrados en el decil de lujo (>4M DKK), donde faltan variables hiperlocales — vecindad exacta, calidad, renovaciones. En el mercado medio, que es el 60% de las transacciones, el error es ~26% MAPE. Por eso el modelo se usa para *ranking* riesgo-retorno por segmento, no para tasar una vivienda individual."

### Por qué no es más alto (y por qué eso está bien)

1. **Distribution shift 2018–2024**: el test cae en el boom post-COVID (+30–50% en 4 años); el train 1992–2017 nunca vio ese régimen. Es el escenario realista de producción, deliberado.
2. **Techo del feature set ≈ 0.5**: los folds CV tempranos (periodos "estables") también dan R²~0.13–0.49 → el límite es la falta de variables hiperlocales, no el algoritmo. Con datos catastrales/embeddings de dirección, R²=0.7–0.8 sería alcanzable.
3. **Objetivo real**: la pregunta de investigación es sobre **volatilidad, drawdowns y diferencias capital-provincias por régimen macro** — el modelo predictivo es secundario y descriptivo; el ranking relativo importa más que el R² absoluto.

### Por qué el 0.44 es HONESTO (integridad — nuestro punto fuerte)

- **Anti-leakage con guard activo**: se detectó y bloqueó `sqm_price_real` (daba un R²=0.97 *falso* por ser función directa del target); el pipeline **aborta** si una columna prohibida entra (`features.py:348`).
- **Split temporal estricto** (no aleatorio → sin fuga del futuro), imputación con mediana del *train*.
- **Métricas en escala nominal DKK** (no log-scale, que infla artificialmente el R²).
- Contraste honesto: el repo legacy reportaba R²=0.9999 sobre log-price con leakage; nuestro 0.44 nominal y auditado es la cifra real y reproducible. **Preferimos un número modesto y verdadero a uno alto y falso.**

### Reproducibilidad del análisis de errores

```python
import pandas as pd, numpy as np
d = pd.read_csv('data/marts/mart_predictions_sample.csv').query("model=='M4_XGBoost'")
d['decil'] = pd.qcut(d.y_true, 10, labels=False) + 1
d.groupby('decil').apply(lambda x: pd.Series({
    'precio_medio': x.y_true.mean(),
    'MAE': x.residual.abs().mean(),
    'MAPE_%': (x.residual.abs()/x.y_true).mean()*100,
    'bias': x.residual.mean(),
}), include_groups=False).round(0)
```
