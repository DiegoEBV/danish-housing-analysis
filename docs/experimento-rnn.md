# Experimento: ¿ayudan los modelos recurrentes (GRU/LSTM/RNN) al forecast de la serie regional?

> **Estado**: experimento cerrado. Veredicto: **NO conviene un modelo recurrente**
> para esta serie; el mejor forecaster es una regresión lineal (Ridge) sobre lags.

## 1. Encuadre honesto del problema

El **modelo campeón del proyecto** es un **XGBoost cross-sectional por transacción**
(predice `purchase_price` fila a fila, R² ≈ 0.44 out-of-time). Ese modelo **no es
secuencial**: no hay una dimensión temporal ordenada en su input, por lo que un RNN
**no aplica a esa tarea tal cual**.

Para poder evaluar si los recurrentes aportan algo, este experimento **reformula el
problema como un forecast de serie temporal**: predecir el **precio real trimestral
por m² por región** (`avg_sqm_price_real` del mart `mart_quarterly_regional_index`).
Por lo tanto:

- **Esto NO es una comparación directa "RNN vs el XGBoost entregado".** Son tareas
  distintas (cross-sectional por transacción vs. forecast de la serie agregada).
- La pregunta que sí responde el experimento es: **"¿los RNN mejoran el forecast de
  la serie trimestral agregada frente a baselines simples y árboles?"**

## 2. Datos

- Fuente: `data/marts/mart_quarterly_regional_index.csv`.
- 4 regiones: `Zealand`, `Jutland`, `Fyn & islands`, `Bornholm`.
- ~130 trimestres por región (1992Q1–2024Q4; `Bornholm` arranca en 1996). Un único
  hueco de 2 trimestres tras 2016Q4, **interpolado linealmente en log-precio**.
- **Serie corta: ~130 puntos por región (~500 en total).** Este es el hecho decisivo:
  es muy poco para deep learning.

## 3. Metodología

- **Tarea**: forecast **one-step-ahead (t+1)** del precio real por m² por región.
- **Espacio de trabajo**: **log-returns** trimestrales `r_t = log(p_t) − log(p_{t-1})`
  (más estacionario/estable que el nivel). Se predice `r_{t+1}` y se reconstruye el
  precio como `p̂_{t+1} = p_t · exp(r̂_{t+1})`. Todas las métricas se computan sobre el
  **nivel de precio real (DKK/m²)**, no sobre el return, para interpretabilidad.
- **Features**: 8 lags de returns (`L=8`, 2 años). Para los modelos poolados se añade
  one-hot de región.
- **Validación TEMPORAL, sin shuffle**: holdout = último **25%** de la línea de tiempo
  (test empieza en **2016Q4**; train=344, test=132 muestras). Los modelos aprendidos
  se ajustan una vez sobre el train y predicen t+1 con los lags reales observados
  (evaluación walk-forward de modelo fijo). Los recurrentes usan un split de validación
  interno temporal (último 15% del train) con **early stopping**.
- **Reproducibilidad**: semillas fijas (`numpy`, `torch`, `random` = 42),
  `torch.use_deterministic_algorithms`.

**Modelos comparados**:

| Familia | Modelo | Descripción |
|---|---|---|
| Baseline | `naive` | random walk: `p̂_{t+1} = p_t` |
| Baseline | `seasonal_naive` | `p̂_{t+1} = p_{t-3}` (valor de 4 trimestres antes) |
| Lineal | `ridge_lags` | Ridge (L2) sobre 8 lags de returns + región |
| Árboles ("como estamos") | `xgboost_lags` | XGBoost sobre 8 lags de returns + región |
| Recurrente | `rnn` | RNN vanilla, 1 capa, 24 unidades, dropout 0.15 |
| Recurrente | `gru` | GRU, 1 capa, 24 unidades, dropout 0.15 |
| Recurrente | `lstm` | LSTM, 1 capa, 24 unidades, dropout 0.15 |

`skill_vs_naive = 1 − RMSE_modelo / RMSE_naive` (>0 = mejor que el random walk).

## 4. Resultados

### Global (promedio across regiones, holdout temporal)

| model | RMSE | MAE | MAPE (%) | skill vs naive |
|---|---:|---:|---:|---:|
| naive | 1331.3 | 904.5 | 5.45 | 0.000 |
| seasonal_naive | 1749.1 | 1289.2 | 7.29 | −0.314 |
| **ridge_lags** | **1217.0** | **842.2** | **4.92** | **+0.086** |
| xgboost_lags | 1362.6 | 972.7 | 5.67 | −0.024 |
| rnn | 1468.6 | 1140.9 | 6.31 | −0.103 |
| gru | 1332.7 | 945.1 | 5.50 | −0.001 |
| lstm | 1320.1 | 943.7 | 5.57 | +0.008 |

### Skill vs naive por región (>0 mejor que naive)

| model | Bornholm | Fyn & islands | Jutland | Zealand |
|---|---:|---:|---:|---:|
| ridge_lags | +0.192 | −0.142 | −0.054 | −0.270 |
| xgboost_lags | +0.052 | −0.199 | −0.071 | −0.333 |
| rnn | +0.190 | −0.197 | −0.719 | −0.949 |
| gru | +0.177 | −0.555 | −0.146 | −0.444 |
| lstm | +0.164 | −0.535 | −0.233 | −0.269 |

Tabla completa (RMSE/MAE/MAPE/skill por modelo, global y por región):
`data/marts/mart_rnn_experiment.csv`. Figura: `docs/refs/rnn_vs_baseline.png`.

## 5. Conclusión (honesta)

**Los modelos recurrentes NO mejoran el forecast de esta serie.** Con el holdout
temporal:

- El **mejor modelo es el más simple y barato: `ridge_lags`** (AR lineal sobre lags),
  único que supera claramente al naive a nivel global (**skill +0.086**, RMSE 1217 vs
  1331).
- Los **recurrentes empatan o pierden contra el random walk**: `lstm` +0.008, `gru`
  −0.001 (empate estadístico con naive), `rnn` −0.103 (peor). No pagan su complejidad.
- `xgboost_lags` sobre esta serie agregada también queda por debajo del naive (−0.024):
  los árboles brillan en la tarea cross-sectional por transacción, no en este forecast.
- El `seasonal_naive` es netamente malo (−0.314): la estacionalidad trimestral no es el
  driver dominante; sí lo son la tendencia y los shocks macro.
- Por región, los recurrentes solo "ayudan" en **Bornholm** (la serie más pequeña y
  ruidosa, y ahí Ridge igual gana), y **empeoran** en Fyn, Jutland y Zealand.

**Causa raíz — serie corta.** ~130 puntos por región (~500 pooled) es un régimen de
datos donde un GRU/LSTM (cientos de parámetros) sobreajusta o, con regularización,
converge a algo cercano al random walk. Los precios de vivienda trimestrales son casi
un random walk con deriva: la mayor parte de la señal one-step-ahead ya está en "el
último valor", y un lag lineal captura el pequeño residuo mejor que una red recurrente.

**Recomendación para el proyecto**: para la tarea de forecast de la serie regional,
**quedarse con modelos simples** (naive/random-walk como referencia y **Ridge sobre
lags** como forecaster). Reservar el deep learning secuencial para cuando exista mucha
más historia o granularidad (p. ej. series mensuales o por zip con miles de puntos).
El campeón del proyecto (**XGBoost cross-sectional por transacción**) sigue siendo el
modelo entregable; este experimento no lo desplaza, solo confirma que agregar un RNN a
la parte de series temporales no aporta valor con los datos disponibles.

## 6. Reproducir

```bash
uv run --with torch --with scikit-learn --with xgboost \
  python docs/refs/rnn_experiment.py   # semillas fijas = 42
```

El script (`docs/refs/rnn_experiment.py`) carga el mart, reconstruye la serie continua,
entrena los 7 modelos y regenera CSV + figura de forma determinista. Usa un entorno
efímero con torch CPU (`--with`), sin tocar las dependencias del proyecto.
