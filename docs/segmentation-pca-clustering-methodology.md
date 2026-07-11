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

## 5. Selección de `k` y KMeans

El número de clusters se elige **por datos**, no a dedo: se corre KMeans para `k ∈ {2..8}` y se
mide el **coeficiente de silueta** de cada solución.

| k | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| silueta | **0.265** | 0.231 | 0.234 | 0.217 | 0.208 | 0.206 | 0.199 |

La silueta es máxima en **k = 2** → se adopta esa solución. El clustering se hace sobre las 6
features estandarizadas (no sobre los 2 PCs), para no descartar el 36 % de varianza residual.
El parámetro `kmeans_k_override` permite fijar `k` manualmente si se quisiera una segmentación
operativa más fina (documentado, pero no usado: la elección automática es la defendible).

## 6. t-SNE — exploración visual complementaria

Se calcula un embedding **t-SNE** 2D (`perplexity = 30`, init con PCA) como **exploración visual
complementaria**, no como prueba de robustez: t-SNE es conocido por poder exagerar o inventar
separaciones entre grupos, y el resultado depende de la perplejidad elegida (no se corrió barrido de
sensibilidad sobre este hiperparámetro). En la figura, los dos grupos aparecen **coherentes con** la
estructura encontrada por KMeans sobre las features estandarizadas (ver
`docs/refs/segmentation_pca_tsne.png`); esa coherencia es consistente con la segmentación, pero no la
demuestra de forma independiente.

## 7. Resultado — dos perfiles de mercado

| Cluster | Etiqueta | n zips | Región dominante | Precio real/m² | CAGR | Volatilidad | Drawdown medio |
|---|---|---:|---|---:|---:|---:|---:|
| 0 | **Precio alto / dinámico / estable** | 229 | Zealand (51 %) | 24 848 | +2.5 %/año | 0.19 | −41.9 % |
| 1 | **Precio bajo / plano / volátil** | 254 | Jutland (Provincias) | 12 979 | +1.1 %/año | 0.42 | −62.0 % |

- El cluster de **precio alto** concentra el metro de Copenhague: sus zips de mayor precio son
  Nordhavn, København V, Klampenborg, Hellerup, København N.
- El cluster de **precio bajo** duplica la volatilidad (0.42 vs. 0.19) y sufre drawdowns **20 pp
  más profundos** (−62 % vs. −42 %).

## 8. Integración al análisis (conexión con hipótesis y dashboard)

- **Consistente con H2 (no confirmación independiente):** el clustering, sin recibir la región como
  input directo, reconstruye la división resiliencia-capital vs. fragilidad-provincia — un resultado
  esperable dado que las features de riesgo-retorno ya están correlacionadas con la región. El
  cluster caro/estable está sobre-representado en Zealand (51 % de sus zips vs. 23 % en el cluster
  barato/volátil); el aporte real es la **granularidad a nivel zip** y la **cuantificación** del gap
  riesgo-retorno entre los dos perfiles, más que una validación adicional de H2.
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
  `docs/refs/segmentation_pca_tsne.png`.

## 10. Limitaciones

- La segmentación es **descriptiva**: agrupa zonas por su comportamiento histórico, no predice
  su evolución futura ni implica causalidad.
- Se restringe a zips con ≥10 años de historia y ≥15 transacciones/año; **449 zips** de baja
  cobertura quedan fuera (mercados rurales muy pequeños) para no introducir ruido.
- La silueta (0.27) indica estructura **moderada**, no clusters netamente disjuntos: el mercado es
  un continuo riesgo-retorno con dos modos, no dos poblaciones separadas. Se reporta como tal.
