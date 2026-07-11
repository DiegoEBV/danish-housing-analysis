# Entrega 6 (TF) — Contenido para el informe

> Texto, tablas y gráficos listos para pegar. Cada bloque corresponde a un ítem de contenido de la
> Entrega 6. Donde dice `[FIGURA]`, insertar la imagen indicada.

---

## 1. Aplicación de PCA, t-SNE o alternativa aprobada

Como técnica no supervisada de la Entrega 6 se aplicó **reducción de dimensionalidad (PCA + t-SNE)
combinada con clustering (KMeans)** sobre el mercado residencial danés, a nivel de **código postal**.
A diferencia de la segmentación por reglas de TB4 (flags `es_capital`, `es_summerhouse`, etc.), esta
técnica **descubre estructura en los datos sin imponer etiquetas a priori**, respondiendo a:
*¿se agrupan los códigos postales en perfiles de riesgo-retorno homogéneos, y esos grupos coinciden
con la división Capital vs. Provincias de H2?* El método **no recibe la región como variable de
entrada**; si reconstruye una división geográfica, es una confirmación emergente (no circular) de H2.

A partir del mart Gold real `mart_transactions_map` (24 124 filas `year × zip_code`) se construyó una
matriz de **483 códigos postales × 6 features** de perfil riesgo-retorno:

| Feature | Definición | Interpretación |
|---|---|---|
| `price_level` | mediana de precio real/m² (ventana reciente, 5 años) | nivel de precio |
| `cagr_real` | crecimiento anual compuesto del precio real | retorno histórico |
| `volatility` | desvío estándar del cambio interanual | riesgo de fluctuación |
| `max_drawdown` | peor caída pico-valle (%) | riesgo de cola |
| `liquidity_log` | log(1 + volumen medio de transacciones/año) | liquidez |
| `growth_recent` | crecimiento del precio en los últimos 5 años | momentum |

Resultados de la técnica:
- **PCA:** 2 componentes retienen el **63.6 %** de la varianza (PC1 = 43.4 %, PC2 = 20.2 %). PC1 es
  el eje dominante riesgo-retorno.
- **KMeans:** el número de clusters se eligió por **coeficiente de silueta** sobre `k ∈ {2..8}`;
  el máximo está en **k = 2** (silueta 0.265).
- **t-SNE:** el embedding no lineal (perplejidad 30) separa los mismos dos grupos, confirmando que la
  estructura es robusta y no un artefacto de la métrica euclídea.

`[FIGURA: docs/refs/segmentation_pca_tsne.png — varianza PCA, proyección PCA 2D por cluster y embedding t-SNE]`

---

## 2. Integración del resultado al análisis

La segmentación produce **dos perfiles de mercado** que se conectan directamente con las hipótesis y
con el dashboard:

| Cluster | Etiqueta | n zips | Región dominante | Precio real/m² | CAGR | Volatilidad | Drawdown medio |
|---|---|---:|---|---:|---:|---:|---:|
| 0 | Precio alto / dinámico / estable | 229 | Zealand (51 %) | 24 848 | +2.5 %/año | 0.19 | −41.9 % |
| 1 | Precio bajo / plano / volátil | 254 | Jutland (Provincias) | 12 979 | +1.1 %/año | 0.42 | −62.0 % |

- **Confirma H2 de forma emergente:** sin usar la región como input, el clustering reconstruye la
  división resiliencia-capital vs. fragilidad-provincia. El cluster caro/estable concentra el metro de
  Copenhague (sus zips de mayor precio son Nordhavn, København V, Klampenborg, Hellerup) y está
  sobre-representado en Zealand (51 % vs. 23 % en el cluster barato).
- **Refina H3:** el riesgo no es solo por tipología, también es **geográfico** — las provincias de
  bajo ticket combinan menor retorno con drawdowns 20 pp más profundos (−62 % vs. −42 %), el peor
  binomio riesgo-retorno para el inversor.
- **Alimenta el dashboard:** el mart `mart_zip_segments.csv` añade la columna `cluster_label` por
  código postal, lista para colorear el mapa coroplético (pestaña Geografía) por perfil de riesgo, y
  `mart_segment_profiles.csv` alimenta la tabla de centroides.

---

## 3. Documentación metodológica de la técnica

**Pipeline reproducible** (`scripts/run_segmentation.py`, parámetros en
`configs/analysis.yaml → segmentation`):

1. **Carga** del mart Gold `mart_transactions_map` (grano `year × zip_code`).
2. **Feature engineering** por zip: las 6 variables de la tabla del punto 1. CAGR robusto (promedia
   los 2 años extremos) y drawdown vía `cummax`.
3. **Filtros de calidad:** se excluyen zips con <10 años de historia o <15 transacciones/año; se
   **winsorizan** las features a `[p1, p99]` para que un zip atípico no capture un cluster de tamaño 1.
   Sobreviven 483 de 932 zips.
4. **Estandarización** (`StandardScaler`, media 0, desvío 1) para que ninguna feature domine por escala.
5. **PCA** (2 componentes) para reducción de dimensionalidad y visualización.
6. **Selección de k** por silueta y **KMeans** sobre las 6 features estandarizadas.
7. **t-SNE** 2D como validación no lineal.
8. **Exportación** de `mart_zip_segments.csv` y `mart_segment_profiles.csv` + figura diagnóstica.

**Reproducibilidad:** determinista (`random_state = 42` en PCA, KMeans y t-SNE); sin números mágicos
(todo en YAML); entorno congelado en `uv.lock`.

**Limitaciones:** segmentación descriptiva (no predice ni implica causalidad); la silueta (0.27)
indica estructura moderada — el mercado es un continuo riesgo-retorno con dos modos, no dos
poblaciones disjuntas; 449 zips de baja cobertura quedan fuera por diseño.

---

## 4. Ajuste final de storytelling, accesibilidad y diseño visual

El ajuste final se guió por tres principios: máximo contraste, **una codificación de color = un solo
significado**, y foco en el usuario (inversor) por sobre la metadata técnica.

- **Modo claro y contraste:** el dashboard pasó de tema oscuro a **tema claro** (fondo `#f4f6fb`,
  superficies blancas, texto `#1c2233`); se ajustaron grillas (líneas claras) y etiquetas de ejes
  (texto oscuro) para legibilidad sobre fondo claro.
- **Eliminación de ruido técnico:** se retiró el banner de procedencia (`gs://danish-housing-gold/…`);
  el inversor no necesita la ruta del bucket, esa trazabilidad va en el informe y en `docs/`.
- **Gobernanza de color por rol** (cada dimensión tiene su paleta, y cada entidad conserva su color
  en todo el dashboard; ningún hue codifica dos significados dentro de una misma vista):

| Rol de color | Paleta | Uso |
|---|---|---|
| **Tipologías** (5) | teal `#0d9488`, naranja `#ea580c`, violeta `#7c3aed`, magenta `#db2777`, gold `#ca8a04` | barras/series por tipo de vivienda (Resumen, Crisis) |
| **Regiones** (4) | índigo `#6366f1`, verde `#34d399`, ámbar `#f59e0b`, morado `#a78bfa` | índice regional (Precios) y barras de drawdown por región (Resumen) |
| **KPIs headline** | verde, índigo, coral, azul | tarjetas de KPI (fila superior) |
| **Riesgo (acento)** | crimson `#be123c` / rosa `#e11d48` | columna DRAWDOWN de casos críticos y métricas de riesgo del panel |
| **Editorial / anotación** | slate `#475569`/`#64748b` | Panel de Insights (títulos, numeración, flechas) |

  Dos correcciones concretas tras revisión de diseño: (a) la **paleta de tipologías se rediseñó** para
  no coincidir con los colores de los KPIs de la fila superior (antes Apartment/Villa/Summerhouse
  reutilizaban el azul/verde/coral de los KPIs); (b) las **barras de "Drawdown por región" pasaron de
  una rampa de un solo tono —donde no se distinguían las regiones— a color por región** (la magnitud se
  lee por el largo de la barra y la etiqueta, no por el color). El slate editorial y el crimson de
  riesgo **no pertenecen a ninguna paleta categórica**.
- **Títulos analíticos:** cada vista afirma un hallazgo (p. ej. "la vivienda urbana absorbe los
  peores shocks, no la segunda residencia"), no solo describe el gráfico. Los tooltips de mapa
  incluyen `n_transactions` para no malinterpretar zonas de baja muestra.

---

## 5. Vista longitudinal y vista transversal finales

| | **Vista longitudinal** | **Vista transversal** |
|---|---|---|
| **Pregunta** | ¿Cómo evolucionó el precio real por región en el tiempo? | ¿Cómo se distribuye el riesgo hoy entre regiones y tipologías? |
| **Gráfico** | Línea multi-serie del índice regional (base 1992 = 100), 1992–2024, con marcadores de shocks (GFC 2008, COVID 2020, alza 2022) | Mapa coroplético por código postal (precio real/m² y segmento) + heatmap región × tipología de drawdowns |
| **Codificación** | posición (Y = índice) + color categórico por región | color (secuencial precio/severidad) + posición geográfica / matriz |
| **Hallazgo defendible** | Zealand **210** en 2024Q4 vs. Fyn & islands **91** (bajo su nivel de 1992): divergencia estructural que no se cierra en la recuperación | El peor drawdown se concentra en **Apartment/Bornholm (−92.1 %)**; Villa es la más resiliente en todas las regiones |

Índice regional base 1992 = 100 (2024Q4): **Zealand 210.3 · Bornholm 140.7 · Jutland 110.0 · Fyn & islands 90.8**.

Heatmap transversal — peor drawdown (%) por región × tipología:

| Región | Apartment | Townhouse | Farm | Summerhouse | Villa |
|---|---:|---:|---:|---:|---:|
| Bornholm | **−92.1** | −80.7 | −79.0 | −63.1 | −44.1 |
| Fyn & islands | −75.3 | −70.6 | −55.1 | −49.3 | −24.9 |
| Zealand | −55.8 | −54.3 | −64.1 | −41.5 | −22.8 |
| Jutland | −56.9 | −59.9 | −39.0 | −35.6 | −26.2 |

`[FIGURA: captura de la pestaña "Precios" (longitudinal) y "Crisis y Riesgo"/"Geografía" (transversal)]`

---

## 6. Versión beta final del dashboard

La versión beta consolidó el dashboard alpha (6 pestañas) e incorporó los ajustes de la Entrega 6:

| Cambio alpha → beta | Detalle |
|---|---|
| Tema visual | migración a **modo claro** (contraste) |
| Gobernanza de color | 3 capas de codificación sin hues repetidos |
| Metadata | eliminación del banner técnico de la vista |
| Segmentación | integración de `mart_zip_segments` (PCA/KMeans) para colorear el mapa por perfil |
| Cifras | reconciliadas con los marts reales vía `run_qa.py` (23/23) |

Estructura de 6 pestañas con flujo de lectura progresivo: **Resumen → Precios → Geografía → Crisis y
Riesgo → Modelado → Conclusiones**, con filtros globales sincronizados (tipología, región, período macro).

---

## 7. Dashboard final

- **URL:** https://gruvizzgobpe.netlify.app/
- **Datos:** capa Gold real (`gs://danish-housing-gold/marts/`), 7 marts, ~1.5 M transacciones 1992–2024.
- **KPIs headline:** precio real/m² (DKK base 2024), prima capital (Zealand 1.8× vs. provincias),
  peor drawdown (−92.1 %), total de transacciones (1.51 M).
- **Responde la pregunta sin explicación externa:** la pestaña Resumen presenta la pregunta, el
  gráfico de riesgo por tipología y un panel FOCO/DRIVER/ACCIÓN que entrega la lectura ejecutiva.
- **Cobertura del curso:** limpieza (P1–P8), modelado (M1–M4), segmentación no supervisada
  (PCA/KMeans/t-SNE), geoanalítica (mapa coroplético) y storytelling.

`[FIGURA: captura de la pestaña Resumen del dashboard final]`

---

## 8. Historia visual / secuencia de presentación

Guion de defensa (storyboard) alineado con el flujo del dashboard:

| # | Momento | Vista / apoyo | Mensaje clave |
|---|---|---|---|
| 1 | **Gancho** | KPIs del Resumen | "El peor drawdown del mercado fue −92.1 % (Apartment/Bornholm)" |
| 2 | **Pregunta** | callout del Resumen | tipologías/regiones de mayor riesgo bajo el ciclo de tasas |
| 3 | **Contexto histórico** | Precios (longitudinal) | divergencia Zealand 210 vs. Fyn 91: dos velocidades |
| 4 | **Geografía** | Mapa + segmentación PCA | el riesgo es geográfico: capital resiliente vs. provincia volátil |
| 5 | **Crisis y riesgo** | Heatmap + drawdowns | la vivienda urbana absorbe los peores shocks, no la segunda residencia |
| 6 | **Modelo** | Comparativa M1–M4 | XGBoost R²=0.44 out-of-time; el ciclo de tasas mueve el volumen (lag 2Q) |
| 7 | **Segmentación** | figura PCA/t-SNE | validación no supervisada de H2 (sin usar la región) |
| 8 | **Conclusión** | Conclusiones + hipótesis | H1✓ H2✓ H3 refinada; recomendaciones de asignación |
| 9 | **Cierre técnico** | pipeline + QA | reproducibilidad y control de supuestos |

---

## 9. QA técnico

QA automatizado en `scripts/run_qa.py` — **23/23 chequeos OK** — que verifica integridad y
**reconcilia las cifras del informe/dashboard con los marts**:

| Chequeo | Resultado |
|---|---|
| Esquema y presencia de 8 marts | ✅ |
| `drawdown_pct ∈ [-100, 0]`, `regional_index > 0`, sin nulos en claves | ✅ |
| Integridad referencial (zips segmentados ⊆ mapa) | ✅ 0 huérfanos |
| Consistencia segmentos ↔ perfiles (`Σ n_zips == 483`) | ✅ |
| Peor drawdown −92.1 % (Bornholm/Apartment/2018Q3) | ✅ |
| Índice Zealand 2024Q4 ≈ 210 ; Fyn < 100 | ✅ |
| Campeón XGBoost R²=0.44, MAE ≈ 867k DKK | ✅ |
| Ranking riesgo Apartment→Villa ; segmentación 2 clusters | ✅ |

Complementado con 13 tests unitarios de limpieza (`uv run pytest tests/`) y linters (ruff/black).

---

## 10. Defensa del pipeline completo

Arquitectura **Medallion** reproducible end-to-end (Bronze → Silver → Gold → segmentación → dashboard):

| Capa | Contenido | Script | Salida |
|---|---|---|---|
| Bronze | CSV/Parquet crudo de Kaggle (~1.5 M) | carga manual | `data/raw/` |
| Silver | dataset limpio con flags P1–P8 + bitácora | `run_cleaning.py` / `run_pipeline.py` | `*.parquet` |
| Gold | 7 marts agregados + segmentación | `export_marts.py`, `run_segmentation.py` (FASE C de `run_pipeline.py`) | `data/marts/*.csv` |
| Presentación | dashboard HTML/Chart.js | Netlify / GitHub Pages | dashboard en vivo |

**Control de supuestos, límites y decisiones (para la defensa):**
- Las reglas de limpieza **flaguean en vez de borrar** — preserva trazabilidad (bitácora TB2); los
  marts filtran con esos flags.
- Análisis **descriptivo-predictivo, no causal**: un R² alto no implica causalidad; los títulos
  evitan verbos causales fuertes.
- Parámetros de negocio centralizados en `configs/analysis.yaml` (año base IPC 2024, base índice 1992,
  ventanas de volatilidad/drawdown, `drawdown_min_obs=5` para evitar drawdowns espurios de baja
  muestra) — decisiones documentadas y con análisis de sensibilidad.
- Límites: 2023–2024 con nulos macro flagueados; 1992–1994 de menor completitud; precisión espacial a
  nivel de código postal; no se extrapola fuera de 1992–2024.
- **Reproducibilidad:** `uv.lock` fija el entorno; `random_state=42`; quality gate `run_qa.py` (23/23)
  y tests (`pytest`) garantizan que una nueva corrida reproduce las cifras publicadas.

```bash
uv sync
uv run python scripts/run_pipeline.py --config configs/analysis.yaml   # Bronze->Silver->Gold->segmentación
uv run python scripts/run_qa.py                                        # QA 23/23
uv run pytest tests/ -q                                                # tests
```
