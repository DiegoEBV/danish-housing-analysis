# Resumen del Proyecto — Dinámica de Precios Residenciales en Dinamarca (1992–2024)

**Curso:** Data Visualization · UPC 2026-01
**Equipo:** Rody Vilchez Marin · Diego Ballón Villar · Christian Velásquez Borasino
**Dashboard en vivo:** https://gruvizzgobpe.netlify.app/
**Repositorio:** https://github.com/DiegoEBV/danish-housing-analysis

---

## 1. Pregunta de negocio y alcance

**Pregunta principal:** ¿qué tipologías de vivienda y qué regiones concentran la mayor volatilidad y los peores drawdowns durante las crisis financieras, y cómo difieren los precios entre Copenhague (región capital) y las provincias danesas bajo distintos regímenes de tasas de interés e inflación?

El análisis es **descriptivo-predictivo, no causal**, sobre ~1.5 M de transacciones reales del mercado residencial danés entre 1992 y 2024 (dataset Kaggle, registros oficiales daneses: *Danish Residential Housing Prices 1992–2024*, 1,507,908 filas). No se extrapola fuera de esa ventana temporal.

El cliente objetivo es un **inversor/decisor residencial danés** que necesita decidir *dónde* (región/código postal), *qué* (tipología de vivienda) y *cuándo* (fase del ciclo de tasas) comprar. Ese es el criterio que gobernó cada decisión de diseño del dashboard: toda vista o elemento debe habilitar una acción concreta de ese cliente, no ser solo ilustrativo.

**Dataset:**
- **Regiones (5, agrupación del dataset sobre las regiones administrativas danesas):** København (capital), Sjælland, Syddanmark, Midtjylland, Nordjylland — presentadas en el dashboard como Zealand (capital), Jutland, Fyn & islands y Bornholm.
- **Tipologías (5):** Villa, Ejerlejlighed/Apartment, Rækkehus/Townhouse, Fritidshus/Summerhouse, Farm.
- **Variables macro:** tasa de interés nominal, inflación anual danesa (`dk_ann_infl_rate_pct`), rendimiento de bonos hipotecarios (`yield_mortgage_bonds_pct`).
- **Períodos de crisis definidos en config:** burbuja inmobiliaria 2006–2009 y crisis financiera global (GFC) 2007–2012; el dashboard además anota la reforma hipotecaria de 1995, COVID 2020 y el alza de tasas de 2022+.

---

## 2. Hipótesis y veredicto

| Hipótesis | Enunciado | Veredicto |
|---|---|---|
| **H1** | Las alzas del bono hipotecario anticipan caídas del volumen de transacciones, con rezago | ✅ Confirmada — correlación rolling negativa en ~81 % de los trimestres; se agudiza en crisis (hasta −0.96 en la GFC) y se relaja en expansión |
| **H2** | Existe una prima estructural de la capital: Zealand diverge de las provincias y esa brecha no se cierra con el tiempo | ✅ Confirmada — índice real 2024Q4: Zealand 210 vs. Fyn & islands 91 |
| **H3** | Las tipologías recreativas (Summerhouse) concentran el mayor riesgo en las crisis | ⚠️ **Refutada y refinada** — el mayor riesgo resultó ser la vivienda **urbana de menor ticket** (Apartment, Townhouse), no la segunda residencia; además el riesgo tiene un componente **geográfico** que la segmentación no supervisada hizo explícito |

El giro en H3 es relevante metodológicamente: el equipo dejó que los datos corrigieran la intuición inicial en vez de forzar la hipótesis original.

---

## 3. Arquitectura: pipeline medallion (Bronze → Silver → Gold)

```
Kaggle CSV/Parquet (~1.5M filas)                    Bronze · gs://danish-housing-bronze
    ↓  limpieza P1–P8 (src/danish_housing/cleaning.py) + bitácora auditable
Silver: parquet limpio con flags                    gs://danish-housing-silver
    ↓  KPIs 1–5 (src/danish_housing/kpis.py) + star schema
Gold: marts agregados (data/marts/*.csv)            gs://danish-housing-gold
    ↓
Dashboard web (Netlify) — 6 vistas
```

**Principio de diseño del pipeline:** las reglas de limpieza **flaguean, nunca borran**. Los marts Gold filtran usando esos flags (ej. `sales_type_valido & ~purchase_price_outlier`), lo que preserva la trazabilidad completa exigida en TB2 — cualquier fila puede rastrearse hasta su estado crudo.

Todo parámetro de negocio (nombres de región, tipologías de interés, ventanas de crisis, año base del IPC, año base del índice regional) vive centralizado en `configs/analysis.yaml`; no hay valores hardcodeados en el código.

**Dos pipelines deliberadamente distintos** (no es duplicación accidental):
- `scripts/run_cleaning.py` — entrega TB2, reusa `src/danish_housing/cleaning.py`, escribe Silver + bitácora.
- `scripts/run_pipeline.py` — entrega TB3/TF, inlinea las reglas P1–P8 optimizado para 1.2M filas en RAM limitada (libera el raw antes de generar marts) y genera los marts Gold en una sola corrida.
- `scripts/export_marts.py` — generación standalone de marts leyendo Silver.

---

## 4. Limpieza de datos (TB2): reglas P1–P8

| Regla | Acción | Filas afectadas (de 1.5M) |
|---|---|---:|
| P1 | Imputar `city` faltante con `"Unknown"` | 0 |
| P2 | Flag `macro_nulo` (gap de datos macro 2023–2024) | 1,193 |
| P3 | Flag `sales_type_valido=False` (ventas no-mercado: transferencias familiares, tipo `"-"`, subastas) | 175,149 (~11.6 %) |
| P4 | Flag `year_build < 1800` | 0 |
| P5 | Flag `purchase_price_outlier` / `sqm_price_outlier` (IQR × 3.0) | 24,282 + 15,217 (~1.6 % / ~1.0 %) |
| P6 | Flag `periodo_preliminar` (1992–1994, menor completitud) | 56,043 (~3.7 %) |
| P7 | Padding de `zip_code` a 4 dígitos string | todas |
| P8 | Renombrar columnas `%25` URL-encoded → sufijo `_pct` | todas |

Cada regla loguea vía `_log()` en `bitacora_limpieza.csv`, un artefacto entregable de TB2. Las reglas están cubiertas por tests unitarios en `tests/`.

---

## 5. KPIs analíticos (TB3/TB4)

1. **Precio real/m²** (`compute_real_price_per_sqm`) — deflactado con IPC danés base 2024. El IPC no viene en el dataset: se deriva de `dk_ann_infl_rate_pct` haciendo cumulada desde el año más reciente hacia atrás, con fallback de 2 %/año para años pre-1992.
2. **Índice regional** (`compute_regional_index`) — base 1992 = 100 por región; si una región no tiene observaciones en 1992, el fallback es el primer trimestre disponible.
3. **Drawdown** (`compute_drawdown`) — máximo acumulado (`cummax`) por región × tipología; `drawdown_pct = (precio − cummax) / cummax × 100`.
4. **Volatilidad** (`compute_volatility`) — desvío estándar del cambio trimestral en ventana móvil de 4 trimestres, por tipología.
5. **Elasticidad volumen–bonos** (`compute_volume_bond_correlation`) — correlación rodante (8 trimestres) entre número de transacciones y rendimiento de bonos hipotecarios, con rezago de 2 trimestres. El lag se eligió a priori por el ciclo típico de aprobación hipotecaria; una cross-correlation empírica posterior (lags 0–4Q) confirmó que 2Q cae en la zona de respuesta más fuerte (lag 1 es comparable), documentado en `docs/data-dictionary-gold.md`.

---

## 6. Modelado predictivo (TB3)

**Problema:** regresión supervisada. Target `purchase_price` (precio nominal en DKK), entrenado sobre `log1p(purchase_price)` por estabilidad numérica, con métricas reportadas en **escala nominal DKK** vía back-transform — reportar en log-scale infla artificialmente el R² por compresión de varianza, y se descartó explícitamente esa práctica.

**Auditoría de leakage:** la primera corrida detectó que `sqm_price_real` (precio/m² deflactado) tenía feature importance = 0.56 en el modelo XGBoost, dando un R² = 0.97 **falso** — es función algebraica directa del target (`sqm_price_real = purchase_price / sqm × cpi_factor`). Se bloqueó vía `FORBIDDEN_FEATURE_COLUMNS` antes de re-correr. Documentado en `docs/legacy-leakage-audit.md`.

**Set final:** 41 features (temporales causales, físicas, categóricas one-hot, frequency encoding para alta cardinalidad, macro externas, rolling regionales causales usando solo años `[y-12, y-1]`, interacciones edad×tipología). Imputación de NaN con la mediana del **train** (no del dataset completo, para no leakear).

**Split temporal:** train 1992–2017 (893,181 filas) / test 2018–2024 (614,727 filas) — el test cae en el período de mayor crecimiento (boom post-COVID, tasas bajas), lo que genera un *distribution shift* severo pero es el escenario realista que enfrentaría el modelo en producción. Validación cruzada complementaria con `TimeSeriesSplit(n_splits=5)` dentro del train.

| Modelo | train R² | test R² | test MAE (DKK) | test MAPE | test RMSE (DKK) |
|---|---:|---:|---:|---:|---:|
| M1 Linear | 0.227 | 0.250 | 1,166,372 | 79.1 % | 1,732,931 |
| M2 Ridge | 0.227 | 0.250 | 1,165,929 | 79.0 % | 1,732,719 |
| M3 RandomForest | 0.417 | 0.237 | 1,033,858 | 43.9 % | 1,748,592 |
| **M4 XGBoost** (Optuna 30 trials TPE, GPU NVIDIA L4) | **0.749** | **0.440** | **866,618** | **37.0 %** | **1,498,211** |

El gap entre train (0.75) y test (0.44) refleja el distribution shift del boom post-COVID, no overfitting: es la brecha esperable de un split temporal honesto.

---

## 7. Segmentación no supervisada (Entrega 6/TF): PCA + KMeans + t-SNE

La segmentación previa del proyecto (TB4) era **por reglas** — flags definidos a mano (`es_capital`, `es_summerhouse`, terciles de tamaño). La Entrega 6 exigía una técnica no supervisada que descubriera estructura sin imponer etiquetas a priori, aplicada a la pregunta: *¿se agrupan los códigos postales daneses en perfiles de riesgo-retorno homogéneos, y esos grupos coinciden con la división Capital vs. Provincias de H2?*

**Construcción del espacio de features**, a partir del mart Gold `mart_transactions_map` (24,124 filas `year × zip_code`), colapsando cada código postal a 6 features interpretables:

| Feature | Definición | Interpretación |
|---|---|---|
| `price_level` | mediana de precio real/m² (ventana reciente, 5 años) | nivel de precio |
| `cagr_real` | crecimiento anual compuesto del precio real | retorno histórico |
| `volatility` | desvío estándar del cambio interanual | riesgo de fluctuación |
| `max_drawdown` | peor caída pico-valle (%) | riesgo de cola |
| `liquidity_log` | log(1 + volumen medio de transacciones/año) | liquidez del mercado |
| `growth_recent` | crecimiento del precio en la ventana reciente | momentum actual |

**Filtros de calidad:** ≥10 años de historia y ≥15 transacciones/año promedio por zip; winsorización de cada feature a `[p1, p99]` para que un zip atípico no capture un cluster de tamaño 1. De los 932 zips del mart, **483** superan los filtros (449 quedan fuera — sesgo de selección hacia mercados líquidos, declarado explícitamente como limitación).

**Pipeline:** estandarización (`StandardScaler`) → **PCA** (2 componentes retienen 63.6 % de varianza; PC1 = 43.4 %, eje dominante riesgo-retorno; PC2 = 20.2 %) → selección de **k por coeficiente de silueta** sobre `k ∈ {2..8}` (máximo en k=2, silueta 0.265) → **KMeans** sobre las 6 features estandarizadas (no sobre los 2 PCs, para no descartar el 36 % de varianza residual) → **t-SNE** 2D (perplejidad 30, init PCA) como **exploración visual complementaria**, no como validación de robustez: t-SNE puede exagerar separaciones y su resultado depende de la perplejidad elegida; se reporta como coherente con la estructura de KMeans, no como prueba independiente.

![PCA y t-SNE de la segmentación por código postal](docs/refs/segmentation_pca_tsne.png)

**Resultado — dos perfiles de mercado:**

| Cluster | Etiqueta | n zips | Región dominante | Precio real/m² | CAGR | Volatilidad | Drawdown medio |
|---|---|---:|---|---:|---:|---:|---:|
| 0 | Precio alto / dinámico / estable | 229 | Zealand (51 %) | 24,848 | +2.5 %/año | 0.19 | −41.9 % |
| 1 | Precio bajo / plano / volátil | 254 | Jutland/Provincias | 12,979 | +1.1 %/año | 0.42 | −62.0 % |

El cluster de precio alto concentra el metro de Copenhague (Nordhavn, København V, Klampenborg, Hellerup, København N como sus zips de mayor precio). El cluster barato **duplica la volatilidad** (2.3×) y sufre drawdowns **20 pp más profundos** — el peor binomio riesgo-retorno.

**Matiz metodológico (honestidad exigida):** las 6 features derivan de precios y volúmenes ya correlacionados con la región, así que el clustering, sin recibir la región como input, redescubre la división Capital vs. Provincias — un resultado **esperable**, no una confirmación independiente de H2. El resultado es **consistente con H2**, y su aporte real es la **granularidad a nivel de código postal** y la **cuantificación** del gap riesgo-retorno. La silueta de 0.265 indica estructura **moderada**: el mercado es un continuo riesgo-retorno con dos modos, no dos poblaciones netamente disjuntas — se reporta tal cual, sin sobrevender la separación.

**Reproducibilidad:** `scripts/run_segmentation.py`, determinista (`random_state=42` en PCA/KMeans/t-SNE), todos los parámetros en `configs/analysis.yaml -> segmentation`. Metodología completa en `docs/segmentation-pca-clustering-methodology.md`; notebook ejecutado end-to-end en `notebook/TF_segmentacion_pca_kmeans.ipynb` (reusa las funciones del script, sin duplicar lógica).

---

## 8. Hallazgos clave

1. **Divergencia regional estructural.** Índice de precio real (base 1992 = 100) a 2024Q4: **Zealand 210.3 · Bornholm 140.7 · Jutland 110.0 · Fyn & islands 90.8** (por debajo de su nivel de 1992). Zealand más que duplicó su precio real; la brecha no se cerró en la recuperación post-crisis, lo que apunta a restricciones de oferta urbana de carácter estructural.
2. **El riesgo es urbano, no recreativo (H3 refinada).** Contra la intuición inicial, la mayor volatilidad y los peores drawdowns están en vivienda urbana de menor ticket: **Apartment** (σ=9.2, drawdown −92.1 %) y **Townhouse** (σ=10.2, −80.7 %) superan a **Summerhouse** (σ=3.9, −63.1 %). **Villa** es el activo más estable en todas las regiones (σ=2.3, −44.1 %). El peor drawdown del dataset completo es **Bornholm/Apartment 2018Q3 (−92.1 %)**, amplificado por baja liquidez (n=5 transacciones).
3. **La geografía duplica el riesgo.** La segmentación no supervisada, sin usar la región como input, separa los códigos postales en un perfil de precio alto/estable (concentrado en el metro de Copenhague, drawdown −42 %) y uno de precio bajo/volátil (dominado por Jutland/provincias, drawdown −62 %).
4. **Transmisión hipotecaria asimétrica.** La correlación entre volumen de transacciones y rendimiento de bonos hipotecarios (rezago 2 trimestres) es negativa en promedio pero se agudiza en crisis (hasta −0.96 en la GFC) y se aproxima a cero en expansión: el canal de crédito opera sobre todo bajo estrés financiero.
5. **Modelo de precios.** XGBoost explica R²=0.44 en el test out-of-time 2018–2024 (MAE ≈ 867k DKK, MAPE ≈ 37 %), muy por encima del baseline lineal (R²=0.25). El gap train→test refleja distribution shift, no overfitting.

### Heatmap transversal — peor drawdown (%) por región × tipología

| Región | Apartment | Townhouse | Farm | Summerhouse | Villa |
|---|---:|---:|---:|---:|---:|
| Bornholm | **−92.1** | −80.7 | −79.0 | −63.1 | −44.1 |
| Fyn & islands | −75.3 | −70.6 | −55.1 | −49.3 | −24.9 |
| Zealand | −55.8 | −54.3 | −64.1 | −41.5 | −22.8 |
| Jutland | −56.9 | −59.9 | −39.0 | −35.6 | −26.2 |

---

## 9. Recomendaciones para el cliente (inversor residencial danés)

1. **Timing de entrada (H1):** en fases de alza del bono hipotecario, esperar 1–2 trimestres antes de comprar — el volumen cae con rezago (correlación negativa en ~81 % de los trimestres).
2. **Selección tipología-región (H2/H3):** priorizar **Villa en Zealand** (drawdown −22.8 %, el mejor binomio riesgo-retorno) sobre **Apartment en provincias periféricas** (Jutland −56.9 %, Bornholm −92.1 %) — la escasez de oferta en la capital protege el precio en las caídas.
3. **Exclusión de zonas (segmentación):** evitar concentración en códigos postales del segmento "precio bajo / plano / volátil" — combinan menor retorno (CAGR 1.1 % vs. 2.5 %) con drawdowns 20 pp más profundos y liquidez frágil.
4. **Monitoreo:** usar el rendimiento del bono hipotecario danés como *leading indicator* con rezago de ~2 trimestres.

---

## 10. El dashboard: estructura y diseño visual

**URL:** https://gruvizzgobpe.netlify.app/ — HTML + Chart.js + Leaflet + TopoJSON, alimentado por la capa Gold real (`gs://danish-housing-gold/marts/`), desplegado en Netlify.

**6 pestañas en secuencia narrativa** (numeradas 1–6 en la UI, con puentes de transición de una línea entre cada una):

| # | Vista | Rol | Acción que habilita en el cliente |
|---|---|---|---|
| 1 | Resumen | Contexto: pregunta, KPIs headline, panel FOCO → DRIVER → ACCIÓN, semáforo de hipótesis H1✓/H2✓/H3~ | Entiende el mensaje central en segundos |
| 2 | Precios | **Vista longitudinal**: índice regional 1992–2024, precio real/m², shocks marcados (reforma 1995, GFC, COVID, alza 2022) | Ve la divergencia capital-provincias en el tiempo |
| 3 | Crisis y Riesgo | Drawdowns y volatilidad por tipología durante los ciclos de crisis | Identifica qué tipologías evitar bajo estrés |
| 4 | Geografía | **Vista transversal**: mapa coroplético por código postal con toggle precio ↔ segmento riesgo-retorno, heatmap región × tipología | Decide en qué zonas concentrar o evitar exposición |
| 5 | Modelado | Comparativa de los 4 modelos, feature importance, tabla de decisiones de visualización (incluye gráficos descartados y por qué) | Confía en la base técnica del análisis |
| 6 | Conclusiones | Hipótesis + sección "¿Qué hacer con esto?" con las recomendaciones concretas | Se lleva acciones aplicables |

**KPIs headline en Resumen:** precio real/m² (DKK base 2024), prima capital (Zealand 1.8× vs. provincias), peor drawdown (−92.1 %), total de transacciones (1.51 M).

**Gobernanza de color por rol** — cada dimensión tiene su propia paleta y cada entidad conserva su color en todo el dashboard; ningún hue codifica dos significados dentro de una misma vista:

| Rol de color | Paleta | Uso |
|---|---|---|
| Tipologías (5) | teal `#0d9488`, naranja `#ea580c`, violeta `#7c3aed`, magenta `#db2777`, gold `#ca8a04` | barras/series por tipo de vivienda (Resumen, Crisis) |
| Regiones (4) | índigo `#6366f1`, verde `#34d399`, ámbar `#f59e0b`, morado `#a78bfa` | índice regional (Precios), drawdown por región (Resumen) |
| KPIs headline | verde, índigo, coral, azul | tarjetas de KPI |
| Riesgo (acento) | crimson `#be123c` / rosa `#e11d48` | columna de drawdown en casos críticos |
| Editorial / anotación | slate `#475569`/`#64748b` | panel de Insights (títulos, numeración) |
| Segmentación (2, seguro para daltonismo) | azul `#2563eb` / naranja `#f97316`; gris `#9ca3af` para zips sin cobertura | modo "Segmento riesgo-retorno" del mapa |

Dos correcciones de diseño aplicadas durante el proceso: (a) la paleta de tipologías se rediseñó para no coincidir con los colores de los KPIs de la fila superior; (b) las barras de "Drawdown por región" pasaron de una rampa de un solo tono (donde no se distinguían las regiones) a color por región, leyendo la magnitud por el largo de la barra y la etiqueta, no por el color.

**Vista longitudinal vs. transversal (resumen comparativo):**

| | Vista longitudinal | Vista transversal |
|---|---|---|
| Pregunta | ¿Cómo evolucionó el precio real por región en el tiempo? | ¿Cómo se distribuye el riesgo hoy entre regiones y tipologías? |
| Gráfico | Línea multi-serie del índice regional (base 1992=100), con marcadores de shocks | Mapa coroplético por zip (precio real/m² y segmento) + heatmap región × tipología |
| Codificación | posición (Y=índice) + color categórico por región | color (secuencial precio/severidad) + posición geográfica/matriz |
| Hallazgo defendible | Zealand 210 vs. Fyn 91: divergencia estructural que no se cierra en la recuperación | Peor drawdown en Apartment/Bornholm (−92.1 %); Villa es la más resiliente en todas las regiones |

---

## 11. Calidad: QA técnico y accesibilidad

**QA automatizado** (`scripts/run_qa.py`) — **23/23 chequeos OK**, verificados en la última corrida:
- Integridad: presencia y esquema de los marts, rangos válidos (`drawdown_pct ∈ [-100, 0]`, `regional_index > 0`), sin nulos en columnas clave.
- Integridad referencial: zips segmentados ⊆ mapa de transacciones (0 huérfanos).
- Consistencia segmentos ↔ perfiles (`Σ n_zips == 483 == filas de segmentos`).
- **Reconciliación:** cada cifra publicada en el informe y el dashboard se re-deriva desde los marts y debe coincidir (peor drawdown −92.1 %, índice Zealand ≈210, XGBoost R²≈0.44, ranking de riesgo Apartment→Villa, k=2 clusters). El script sale con código ≠ 0 si algo falla.
- Star schema validado: 0 huérfanos, 0 duplicados.

**Accesibilidad** (`docs/verificacion-accesibilidad.md`):
- **Contraste WCAG AA:** se auditaron todos los pares texto/fondo reales (incluyendo badges translúcidos); 25 pares fallaban, los 25 fueron corregidos y ahora pasan (≥4.5:1 texto normal).
- **Daltonismo:** simulación de protanopia/deuteranopia sobre todas las paletas; se corrigieron 3 colisiones reales (Zealand vs. Fyn, Villa vs. Townhouse, períodos de crisis); la paleta de segmentos (azul/naranja) fue diseñada para ser distinguible desde el inicio.
- **ARIA:** roles `tablist`/`tab`/`tabpanel` con `aria-selected`, `aria-label` en cada canvas de Chart.js con el hallazgo (no una descripción genérica), `aria-label` en el mapa y en los controles (selects, toggles), jerarquía de headings coherente, foco visible en controles interactivos.
- Títulos analíticos: cada gráfico afirma un hallazgo en vez de describir el eje (ej. "Zealand más que duplica su nivel de 1992" en lugar de "Precios por región"); ejes con unidades explícitas (DKK/m², %, trimestres).

Complementado con tests unitarios de limpieza (`pytest tests/`) y linters (`ruff`, `black`, `mypy`).

---

## 12. Reproducibilidad

```bash
uv sync --extra dev --extra notebook                                        # entorno (uv 0.9+)

uv run python scripts/run_cleaning.py  --config configs/analysis.yaml       # Bronze → Silver (TB2)
uv run python scripts/run_pipeline.py  --config configs/analysis.yaml       # Silver + marts Gold (TB3)
uv run python scripts/export_marts.py  --config configs/analysis.yaml       # marts standalone
uv run python scripts/run_segmentation.py --config configs/analysis.yaml    # PCA/KMeans/t-SNE (TF)
uv run python scripts/run_qa.py                                             # quality gate (23/23)
uv run pytest tests/                                                        # tests de limpieza
```

- Determinismo: `random_state=42` fijo en PCA, KMeans y t-SNE; entorno congelado en `uv.lock`.
- Parámetros de negocio centralizados en `configs/analysis.yaml` (año base IPC 2024, año base índice 1992, ventanas de volatilidad/drawdown, `drawdown_min_obs=5` para evitar drawdowns espurios de baja muestra) — decisiones documentadas.
- Runbooks end-to-end en `runbooks/` (ejecución completa, setup medallion en GCP, corrida GPU en Lightning.ai).
- Notebooks entregables ejecutados con outputs: TB2 (perfilado/limpieza), TB3 (preprocesamiento/modelado), TB4 (segmentación por reglas + cálculos), TF (`TF_segmentacion_pca_kmeans.ipynb`, PCA/KMeans/t-SNE).

**Arquitectura Medallion end-to-end (para defensa del pipeline):**

| Capa | Contenido | Script | Salida |
|---|---|---|---|
| Bronze | CSV/Parquet crudo de Kaggle (~1.5M) | carga manual | `data/raw/` |
| Silver | dataset limpio con flags P1–P8 + bitácora | `run_cleaning.py` / `run_pipeline.py` | `*.parquet` |
| Gold | marts agregados + segmentación | `export_marts.py`, `run_segmentation.py` | `data/marts/*.csv` |
| Presentación | dashboard HTML/Chart.js | Netlify / GitHub Pages | dashboard en vivo |

---

## 13. Límites y supuestos

- Análisis **descriptivo-predictivo, no causal**: un R² alto no implica causalidad; los títulos del dashboard evitan verbos causales fuertes.
- **Deflactor derivado, no observado:** el IPC se reconstruye por cumulada de la inflación anual danesa, con fallback de 2 %/año pre-1992 — todo "precio real" reportado depende de esa aproximación.
- Precisión espacial a nivel de código postal, sin coordenadas exactas de propiedades individuales.
- Gap de datos macro 2023–2024 y período preliminar 1992–1994 (menor completitud) están **flagueados**, no ocultados ni eliminados.
- Segmentación: cubre solo mercados líquidos (483 de 932 zips, ~48 % de exclusión); silueta 0.265 indica estructura moderada, no clusters netamente disjuntos; es descriptiva, no predictiva ni causal.
- El lag de 2 trimestres del KPI 5 se eligió a priori por el ciclo hipotecario típico; la cross-correlation empírica lo ubica en la zona de respuesta fuerte pero el lag 1 es comparable — documentado con honestidad, no se afirma que sea el único óptimo.
- El R²=0.44 del modelo campeón refleja el distribution shift del test out-of-time (boom post-COVID) — es el escenario realista de producción, no una limitación oculta.

---

## 14. Cobertura del curso y estado del entregable

| Entregable | Estado | Contenido |
|---|---|---|
| TB1 — Ficha del proyecto | ✅ Completo | Pregunta analítica, dataset, KPIs |
| TB2 — Perfilado y Limpieza | ✅ Completo | Reglas P1–P8 + bitácora |
| TB3 — Modelado y Métricas | ✅ Completo | M1–M4, XGBoost campeón, marts de modelado |
| TB4 — Segmentación y cálculos | ✅ Completo | Star schema + segmentación por reglas + 5 KPIs |
| TF — Trabajo final (Entrega 6) | ✅ Completo | Segmentación no supervisada, dashboard final, QA, accesibilidad |

El dashboard responde la pregunta principal **sin depender de explicación externa extensa**: la pestaña Resumen presenta la pregunta, el semáforo de hipótesis y un panel FOCO → DRIVER → ACCIÓN con la lectura ejecutiva; cada vista cierra con su propio takeaway, y Conclusiones cierra con acciones concretas para el cliente.

**Nota sobre formato:** el entregable pide "dashboard en Tableau (o una web en node.js)"; el producto actual es HTML estático + Chart.js desplegado en Netlify (no Tableau `.twbx` ni Node.js). Es defendible como demo funcional publicable en vivo; la confirmación formal con el docente sobre si esto satisface el requisito de formato queda pendiente, fuera del alcance de este documento.

---

## Anexo — Inventario de documentación y activos de referencia

| Documento / activo | Ruta | Contenido |
|---|---|---|
| Figura PCA + t-SNE | `docs/refs/segmentation_pca_tsne.png` | Varianza PCA, proyección 2D por cluster, embedding t-SNE — única imagen estática del repo |
| Metodología de segmentación | `docs/segmentation-pca-clustering-methodology.md` | Detalle completo de features, filtros, PCA, k, t-SNE, limitaciones |
| Reporte de métricas TB3 | `docs/reporte-metricas-tb3.md` | Preprocesamiento, feature engineering, auditoría de leakage, resultados de los 4 modelos |
| Verificación de accesibilidad | `docs/verificacion-accesibilidad.md` | Auditoría de contraste WCAG AA, simulación de daltonismo, ARIA aplicado |
| QA técnico | `docs/qa-tecnico.md` + `scripts/run_qa.py` | Metodología del quality gate y resultado de la última corrida |
| Resumen ejecutivo | `docs/resumen-ejecutivo.md` | Síntesis de una página de hallazgos y recomendaciones |
| Informe Entrega 6 (texto pasteable) | `docs/informe-entrega6-secciones.md` | Contenido por ítem de la rúbrica, listo para copiar al informe |
| Diccionario de datos Gold | `docs/data-dictionary-gold.md` | Esquema y grano de cada mart |
| Auditoría de leakage legacy | `docs/legacy-leakage-audit.md` | Detalle del hallazgo `sqm_price_real` y su remediación |
| Estado actual del proyecto | `docs/project-current-state.md` | Seguimiento vivo de avance por entregable |
| Notebooks entregables | `notebook/TB2_*.ipynb`, `TB3_*.ipynb`, `TB4_*.ipynb`, `TF_segmentacion_pca_kmeans.ipynb` | Evidencia ejecutada de cada entrega |
