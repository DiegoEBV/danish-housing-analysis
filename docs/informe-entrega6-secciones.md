# Secciones para el informe — Entrega 6 (TF)

> **Cómo usar este archivo:** las secciones de abajo están redactadas en el estilo y numeración
> de tu informe (que terminaba en la sección 29 – Referencias). Pega las secciones 30 y 31 **antes**
> de "29. Referencias bibliográficas" (o renumera según convenga). La figura referenciada es
> `docs/refs/segmentation_pca_tsne.png`. El resumen ejecutivo completo está en
> `docs/resumen-ejecutivo.md` (documento aparte, entregable independiente).

---

## 30. Segmentación no supervisada — PCA, KMeans y t-SNE

La segmentación de la sección 19 era **por reglas** (flags `es_capital`, `es_summerhouse`,
`periodo_macro`, terciles de tamaño). Para la Entrega 6 se añade una técnica **no supervisada** que
descubre estructura en los datos sin imponer etiquetas a priori, respondiendo a la pregunta:
*¿se agrupan los códigos postales daneses en perfiles de riesgo-retorno homogéneos, y esos grupos
coinciden con la división Capital vs. Provincias de H2?* El método **no recibe la región como
input**; si reconstruye una división geográfica, es una confirmación emergente (no circular) de H2.

**Espacio de features (por `zip_code`).** Se parte del mart Gold real `mart_transactions_map`
(24 124 filas `year × zip_code`) y se colapsa cada código postal a 6 variables interpretables:

| Feature | Definición | Interpretación |
|---|---|---|
| `price_level` | mediana de precio real/m² en la ventana reciente (5 años) | nivel de precio |
| `cagr_real` | crecimiento anual compuesto del precio real | retorno histórico |
| `volatility` | desvío estándar del cambio interanual | riesgo de fluctuación |
| `max_drawdown` | peor caída pico-valle (%) | riesgo de cola |
| `liquidity_log` | log(1 + volumen medio de transacciones/año) | liquidez |
| `growth_recent` | crecimiento del precio en los últimos 5 años | momentum |

Se filtran zips con <10 años de historia o <15 transacciones/año y se winsorizan las features a
`[p1, p99]` para robustez ante outliers. Sobreviven **483 de 932 zips**. Las features se
estandarizan (`StandardScaler`).

**Reducción de dimensionalidad (PCA).** Dos componentes retienen el **63.6 %** de la varianza
(PC1 = 43.4 %, PC2 = 20.2 %). PC1 es el eje dominante riesgo-retorno.

**Selección de k y clustering (KMeans).** Se evalúa `k ∈ {2..8}` por coeficiente de silueta; el
máximo está en **k = 2** (silueta 0.265). El clustering se hace sobre las 6 features estandarizadas.

**Validación no lineal (t-SNE).** Un embedding t-SNE 2D (perplejidad 30) separa los mismos dos
grupos, confirmando que la estructura no es un artefacto de la métrica euclídea (ver figura).

![Segmentación PCA + KMeans + t-SNE](refs/segmentation_pca_tsne.png)

**Resultado — dos perfiles de mercado:**

| Cluster | Etiqueta | n zips | Región dominante | Precio real/m² | CAGR | Volatilidad | Drawdown medio |
|---|---|---:|---|---:|---:|---:|---:|
| 0 | Precio alto / dinámico / estable | 229 | Zealand (51 %) | 24 848 | +2.5 %/año | 0.19 | −41.9 % |
| 1 | Precio bajo / plano / volátil | 254 | Jutland (Provincias) | 12 979 | +1.1 %/año | 0.42 | −62.0 % |

El cluster de precio alto concentra el metro de Copenhague (Nordhavn, København V, Klampenborg,
Hellerup); el de precio bajo duplica la volatilidad y sufre drawdowns 20 pp más profundos.

**Integración al análisis.** (i) *Confirma H2 de forma emergente*: sin usar la región, el clustering
reconstruye la división resiliencia-capital vs. fragilidad-provincia. (ii) *Refina H3*: el riesgo no
es solo por tipología sino **geográfico** — las provincias de bajo ticket combinan menor retorno con
peor drawdown. (iii) *Alimenta el dashboard*: `mart_zip_segments.csv` añade `cluster_label` por zip,
listo para colorear el mapa coroplético por perfil de riesgo, y `mart_segment_profiles.csv` da la
tabla de centroides.

**Reproducibilidad.** `uv run python scripts/run_segmentation.py --config configs/analysis.yaml`
(determinista, `random_state=42`; parámetros en `configs/analysis.yaml → segmentation`). Metodología
completa en `docs/segmentation-pca-clustering-methodology.md`.

**Limitaciones.** Segmentación descriptiva (no predice ni implica causalidad); la silueta (0.27)
indica estructura moderada — el mercado es un continuo riesgo-retorno con dos modos, no dos
poblaciones disjuntas; 449 zips de baja cobertura quedan fuera por diseño.

---

## 31. QA técnico y reproducibilidad

El aseguramiento de calidad se automatiza en `scripts/run_qa.py`, que en una corrida verifica
integridad de datos y **reconcilia las cifras del informe/dashboard con los marts** (última corrida:
**23/23 chequeos OK**). Extracto:

| Cifra publicada | Fuente | Verificación |
|---|---|---|
| Peor drawdown −92.1 % (Bornholm/Apartment/2018Q3) | `mart_drawdowns` | ✅ −92.11 % |
| Índice Zealand 2024Q4 ≈ 210 (>2× base 1992) | `mart_quarterly_regional_index` | ✅ 210.3 |
| Fyn & islands < 100 (bajo su nivel 1992) | `mart_quarterly_regional_index` | ✅ 90.8 |
| Campeón XGBoost R²=0.44, MAE≈867k DKK | `mart_model_comparison` | ✅ |
| Ranking riesgo Apartment→Villa; segmentación 2 clusters | `mart_drawdowns`, `mart_segment_profiles` | ✅ |

Reproducibilidad: parámetros centralizados en `configs/analysis.yaml` (sin números mágicos),
determinismo con `random_state=42`, entorno congelado en `uv.lock`, 13 tests unitarios de limpieza
(`uv run pytest tests/`) y quality gate `run_qa.py`. Detalle en `docs/qa-tecnico.md`.

```bash
uv run python scripts/export_marts.py --config configs/analysis.yaml       # marts KPIs
uv run python scripts/run_segmentation.py --config configs/analysis.yaml   # PCA/KMeans/t-SNE
uv run python scripts/run_qa.py                                            # QA 23/23
uv run pytest tests/ -q                                                    # tests
```

---

## 32. Diseño visual, accesibilidad y gobernanza de color

El ajuste final de diseño del dashboard se guió por tres principios de visualización: (a) máximo
contraste, (b) **una codificación de color = un solo significado**, y (c) foco en el usuario
(inversor), no en metadatos técnicos.

### 32.1. Modo claro y contraste

El dashboard se migró de tema oscuro a **tema claro** (fondo `#f4f6fb`, superficies blancas, texto
`#1c2233`) tras la observación del docente. Se ajustaron en consecuencia las grillas de los gráficos
(líneas claras `#e3e7ef`) y las etiquetas de ejes (texto oscuro), garantizando legibilidad de series,
ejes y tooltips sobre fondo claro.

### 32.2. Eliminación de ruido técnico en la vista

Se retiró el banner de procedencia técnica (`Gold layer GCP · gs://danish-housing-gold/marts/ …`).
El usuario objetivo del dashboard (inversor residencial) no necesita la ruta del bucket ni el
detalle de infraestructura; esa trazabilidad pertenece al informe y a la documentación técnica
(`docs/cloud-architecture.md`, `docs/data-dictionary-gold.md`), no a la cara del producto. Retirarlo
reduce carga cognitiva y evita competir por atención con los KPIs.

### 32.3. Gobernanza de color — tres capas de codificación separadas

Se detectó que un mismo hue estaba codificando significados distintos en distintas partes del
dashboard (p. ej. el ámbar `#f59e0b` servía a la vez de tipología *Townhouse*, región *Jutland* y
nivel de severidad "medio" en el panel de insights; el coral `#f87171` era *Summerhouse*, el período
*GFC* y "severidad alta"). Esa reutilización induce a leer relaciones inexistentes entre elementos.
Se reorganizó la paleta en **tres capas mutuamente excluyentes**:

| Capa de codificación | Tipo | Paleta | Uso |
|---|---|---|---|
| **Categórica** (nominal) | cualitativa | azul `#60a5fa`, verde `#34d399`, ámbar `#f59e0b`, coral `#f87171`, morado `#a78bfa`, índigo `#6366f1` | tipologías, regiones, períodos macro |
| **Magnitud de riesgo** (drawdown) | secuencial | rampa **rosa/crimson** `#fb7185` → `#f43f5e` → `#be123c` (más oscuro = peor) | barras de drawdown por región, columna DRAWDOWN de casos críticos, métricas de riesgo del panel |
| **Editorial / anotación** | neutra | **slate** `#475569` / `#64748b` | Panel de Insights (títulos, numeración, flechas de acción) |

**Regla aplicada:** la rampa rosa y el slate **no aparecen en ninguna paleta categórica**, por lo que
ningún hue tiene dos significados en el dashboard. Así, en la tabla "Casos críticos" la columna
*Tipología* usa el color categórico (Apartment azul, Townhouse ámbar) y la columna *Drawdown* usa la
rampa rosa de magnitud: dos codificaciones que ya no colisionan.

**Justificación perceptual:** para *magnitud* (drawdown) una escala **secuencial de un solo tono**
(rosa, oscureciéndose con la severidad) es más honesta que un semáforo rojo-ámbar-verde, porque no
reintroduce hues categóricos ni sugiere un umbral cualitativo artificial. Para *anotación editorial*
(panel de recomendaciones), un neutro (slate) comunica "esto es guía interpretativa, no una categoría
del dato".

### 32.4. Títulos analíticos y etiquetas

Cada vista lleva un **título analítico** (afirma un hallazgo, no describe el gráfico): p. ej.
"la vivienda urbana absorbe los peores shocks, no la segunda residencia". Los tooltips de mapa
incluyen `n_transactions` para no malinterpretar zonas de baja muestra, y las series temporales
marcan los shocks macro (GFC 2008, COVID 2020, alza 2022) con líneas anotadas.

### 32.5. Nota sobre indicadores de estado

Los badges de estado de hipótesis (H1/H2 ✓ en verde, H3 ~ en ámbar) usan una convención
**tipo semáforo de estado** (validada / refinada), no una codificación de dato; se mantienen por ser
un patrón de lectura universal e independiente de las paletas de series. Queda documentado como
decisión consciente.
