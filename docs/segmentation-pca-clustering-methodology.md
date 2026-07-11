# Segmentación no supervisada — PCA + KMeans + t-SNE

**Entrega 6 (TF) · Técnica analítica requerida: reducción de dimensionalidad + clustering**
**Script reproducible:** `scripts/run_segmentation.py` · **Config:** `configs/analysis.yaml → segmentation`
**Datos:** capa Gold real `mart_transactions_map.csv` (24 124 filas `year × zip_code`, 1992–2024)

---

## 1. Objetivo y por qué esta técnica

La segmentación previa del proyecto (TB4, "Segmentación") era **por reglas** —flags definidos
a mano: `es_capital`, `es_summerhouse`, `periodo_macro`, terciles de tamaño—. La Entrega 6 exige
una técnica **no supervisada** (PCA / t-SNE / clustering) que descubra estructura en los datos
sin imponer etiquetas a priori.

Aplicamos esa técnica sobre una pregunta concreta y alineada con la pregunta de investigación:

> **¿Se agrupan los códigos postales daneses en perfiles de riesgo-retorno homogéneos, y esos
> grupos coinciden con la división Capital vs. Provincias que plantea H2?**

La técnica no recibe la región como input directo. Dicho esto, las 6 features se derivan de
precios y volúmenes que ya están fuertemente correlacionados con la región (Copenhague concentra
los precios más altos y la menor volatilidad del dataset), así que redescubrir la división
capital/provincias es un resultado **esperable**, no una prueba independiente de H2. Su valor real
no es "confirmar" la hipótesis desde cero, sino **aportar granularidad a nivel de código postal**
(en vez de 5 regiones) y **cuantificar el gap riesgo-retorno** entre los dos perfiles de mercado.

## 2. Construcción del espacio de features (por `zip_code`)

Partimos del mart Gold `mart_transactions_map` (grano `year × zip_code`) y colapsamos cada
código postal a un vector de **6 features interpretables** de perfil riesgo-retorno:

| Feature | Definición | Interpretación |
|---|---|---|
| `price_level` | mediana de `avg_sqm_price_real` en la ventana reciente (5 años) | nivel de precio real/m² |
| `cagr_real` | crecimiento anual compuesto del precio real (extremos suavizados con 2 años) | retorno histórico |
| `volatility` | desvío estándar del cambio interanual del precio | riesgo de fluctuación |
| `max_drawdown` | peor caída pico-valle (%) sobre la serie anual | riesgo de cola |
| `liquidity_log` | `log(1 + volumen medio de transacciones/año)` | liquidez del mercado |
| `growth_recent` | crecimiento del precio en la ventana reciente (5 años) | momentum actual |

**Filtros de calidad** (evitan que mercados diminutos y erráticos generen ruido):
- `min_years_coverage = 10` años de historia mínima por zip.
- `min_avg_transactions = 15` transacciones/año promedio mínimas.
- **Winsorización** de cada feature a `[p1, p99]` (`winsorize_pct = 0.01`) antes de escalar,
  para que un único zip atípico no capture un cluster de tamaño 1.

De los **932 zips** del mart, **483** superan los filtros y forman la matriz `483 × 6`.

## 3. Estandarización

Las 6 features tienen escalas muy distintas (precio en decenas de miles de DKK vs. volatilidad en
[0,1]). Se aplica `StandardScaler` (media 0, desvío 1) para que ninguna variable domine la
distancia euclídea por su magnitud. Sin este paso, `price_level` dominaría por completo.

## 4. PCA — reducción de dimensionalidad

Se aplica **PCA** sobre la matriz estandarizada:

- **2 componentes** retienen el **63.6 %** de la varianza total (**PC1 = 43.4 %**, **PC2 = 20.2 %**).
- **PC1** es el eje dominante riesgo-retorno: separa zonas de *precio alto / bajo drawdown / baja
  volatilidad* de zonas de *precio bajo / drawdown profundo / alta volatilidad*.
- PCA cumple doble rol: (a) espacio 2D para visualizar y (b) diagnóstico de que la estructura del
  mercado es esencialmente unidimensional (un solo eje explica ~44 %).

## 5. Selección de `k` — consenso amplio + dos k reportados

El número de clusters **no** se elige por una sola métrica (la silueta pura siempre premia `k=2`).
Se evalúa `k ∈ {2..8}` con un **consenso de 7 criterios** más un experimento de informatividad de
negocio (η²), persistidos en `data/marts/mart_segmentation_validation.csv`:

| k | silueta↑ | Calinski↑ | Davies↓ | estab. ARI↑ | gap↑ | GMM-BIC↓ | η² riesgo↑ | η² retorno↑ |
|---|---|---|---|---|---|---|---|---|
| **2** | **0.265** | **197** | 1.415 | **0.964** | 0.898 | 7056 | 0.291 | 0.174 |
| 3 | 0.231 | 154 | 1.560 | 0.814 | 0.928 | 6710 | 0.300 | 0.291 |
| **4** | 0.234 | 149 | 1.362 | 0.827 | 0.996 | 6741 | **0.466** | **0.290** |
| 5 | 0.217 | 140 | 1.267 | 0.624 | 1.037 | 6631 | 0.514 | 0.313 |

Se reportan **dos** `k`, de forma transparente:

- **`k` científico = 2** — elegido por **consenso de los criterios de calidad de cluster**
  (silueta + Calinski-Harabasz + **estabilidad bootstrap ARI = 0.96**). Es la partición
  estadísticamente robusta: dos regímenes de riesgo-retorno. Los criterios que premian `k` más alto
  (Davies-Bouldin, BIC, gap) solo reflejan que un continuo se puede rebanar más fino, **sin
  robustez** (la estabilidad ARI cae a ~0.6–0.8 para `k>2`), por eso no entran al voto científico.

- **`k` operativo = 4** — elegido por **utilidad de negocio**, no por métrica geométrica. Aunque su
  silueta es ligeramente menor (0.234 vs 0.265, mismo orden), **explica mucha más varianza de las
  variables que le importan al inversor**: pasar de `k=2` a `k=4` sube la varianza de **riesgo**
  explicada de **0.29 → 0.47 (+60 %)** y la de **retorno** de **0.17 → 0.29 (+66 %)**. El `k=2`
  mete en una sola bolsa "provincia barata" tres mercados que un inversor trataría distinto; `k=4`
  los separa (ver §7). Configurable en `kmeans_k_operativo`.

El clustering final se hace sobre las 6 features estandarizadas (no sobre los 2 PCs), para no
descartar el 36 % de varianza residual.

## 6. t-SNE — exploración visual (NO validación)

Se calcula un embedding **t-SNE** 2D con **hiperparámetros fijos y documentados** en config
(`tsne_perplexity = 30`, `tsne_learning_rate = auto`, `tsne_max_iter = 1000`, init con PCA,
`random_state = 42`) como **exploración visual complementaria**, explícitamente **no como prueba de
robustez**: t-SNE puede exagerar o inventar separaciones y depende de la perplejidad. La validación
de la estructura recae en los criterios cuantitativos de §5 (silueta, CH, Davies-Bouldin, estabilidad
ARI, gap, BIC), **no** en t-SNE. La figura (`docs/refs/segmentation_pca_tsne.png`) es ilustrativa.

## 7. Resultado — 4 perfiles de inversión (k operativo)

Los 4 arquetipos se etiquetan de forma **determinista por la posición del centroide** (los índices
de KMeans son arbitrarios). El científico `k=2` parte en capital-premium vs provincia; el `k=4`
**abre esa "provincia" en 3 mercados que el `k=2` esconde**:

| Cluster | Arquetipo | n zips | Región dom. | Precio real/m² | CAGR | Volatilidad | Drawdown medio |
|---|---|---:|---|---:|---:|---:|---:|
| 0 | **Premium estable/líquido** | 157 | Zealand | 28 276 | +2.8 %/año | 0.17 | −39.2 % |
| 1 | **Volátil / alto riesgo** | 47 | Jutland | 14 292 | +0.9 %/año | **0.88** | **−79.2 %** |
| 2 | **Value estable/líquido** | 114 | Jutland | 14 293 | +0.7 %/año | 0.28 | −54.0 % |
| 3 | **Value con crecimiento** | 165 | Jutland | 13 615 | **+1.9 %/año** | 0.30 | −56.4 % |

- El **argumento clave**: en `k=2` los clusters 1, 2 y 3 colapsan en un único "Jutland barato". Pero
  el 1 es una **trampa de alto riesgo** (volatilidad 0.88, drawdown −79 %), el 2 es **value estable**
  y el 3 es **value con crecimiento** (CAGR 1.9 %). Para el negocio, separarlos es la diferencia
  entre "invertir en provincia" e "invertir en *este tipo* de provincia".

## 8. Integración al análisis (conexión con hipótesis y dashboard)

- **Consistente con H2 (no confirmación independiente):** el clustering, sin recibir la región como
  input directo, reconstruye la división resiliencia-capital vs. fragilidad-provincia — esperable
  porque las features de riesgo-retorno correlacionan con la región. **Pero no es pura geografía
  disfrazada:** PC1 explica solo el **43 %** de la varianza; el 57 % restante es estructura
  multidimensional real (volatilidad, drawdown, dinámica) que el `k=4` aprovecha para separar
  arquetipos *dentro* de una misma región (los 3 perfiles de Jutland). El aporte es la
  **granularidad a nivel zip** y la **cuantificación** del gap riesgo-retorno, no una validación
  extra de H2.
- **Refina el mensaje de riesgo (H3):** el riesgo no es solo por tipología (Apartment/Townhouse) sino
  **geográfico** — las provincias de bajo ticket combinan menor retorno con mayor drawdown, el peor
  binomio riesgo-retorno para el inversor.
- **Feeds del dashboard:** el mart `mart_zip_segments.csv` añade la columna `cluster_label` a nivel
  de código postal, lista para colorear el **mapa coroplético** (Vista 2 / pestaña Geografía) por
  segmento en vez de por precio absoluto, y `mart_segment_profiles.csv` alimenta una tabla-resumen
  de centroides.

## 9. Reproducibilidad

```bash
uv run python scripts/run_segmentation.py --config configs/analysis.yaml
```

- Determinista: `random_state = 42` en PCA, KMeans y t-SNE.
- Todos los parámetros (filtros, features, `k`, perplejidad) viven en `configs/analysis.yaml →
  segmentation`; no hay números mágicos en el código.
- Salidas: `data/marts/mart_zip_segments.csv`, `data/marts/mart_segment_profiles.csv`,
  `data/marts/mart_segmentation_validation.csv` (métricas por k + experimento η²),
  `docs/refs/segmentation_pca_tsne.png`.

## 10. Limitaciones

- La segmentación es **descriptiva**: agrupa zonas por su comportamiento histórico, no predice
  su evolución futura ni implica causalidad.
- Se restringe a zips con ≥10 años de historia y ≥15 transacciones/año; **449 zips** de baja
  cobertura quedan fuera (mercados rurales muy pequeños) para no introducir ruido.
- La silueta (0.27) indica estructura **moderada**, no clusters netamente disjuntos: el mercado es
  un continuo riesgo-retorno con dos modos, no dos poblaciones separadas. **Se reporta con total
  transparencia**: el `k` científico (2) es la partición robusta (estabilidad ARI 0.96); el `k`
  operativo (4) es una **discretización del continuo en perfiles accionables**, elegida por
  informatividad de negocio (η²), no se afirma que sean 4 clusters naturales. Ambos, con todas sus
  métricas, quedan en `mart_segmentation_validation.csv`.
