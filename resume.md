# Resumen del Proyecto — Mercado Residencial Danés 1992–2024

> Documento maestro para transformar en slides de defensa (TF · Entrega 6).
> Cada sección `## Slide N` es una diapositiva sugerida; los bullets son el contenido, las *notas* son el guion oral.

**Curso:** Data Visualization · UPC 2026-01
**Equipo:** Rody Vilchez Marin · Diego Ballón Villar · Christian Velásquez Borasino
**Dashboard en vivo:** https://gruvizzgobpe.netlify.app/
**Repositorio:** https://github.com/DiegoEBV/danish-housing-analysis

---

## Slide 1 — Portada

- **Título:** Dinámica de precios residenciales en Dinamarca 1992–2024
- **Subtítulo:** ¿Dónde se concentra el riesgo residencial y cómo influye el ciclo de tasas hipotecarias?
- ~1.5 M de transacciones reales · 33 años · 5 regiones · dashboard interactivo en vivo

---

## Slide 2 — Pregunta de negocio y cliente

- **Pregunta principal:** ¿Qué tipologías y regiones concentran el mayor riesgo residencial (volatilidad y drawdowns en crisis), y cómo difieren los precios entre Copenhague y las provincias bajo distintos regímenes de tasas e inflación?
- **Cliente:** inversor/decisor residencial danés que debe decidir **dónde** (región/zip), **qué** (tipología) y **cuándo** (ciclo de tasas) comprar.
- **Principio de diseño del dashboard:** cada elemento responde *"¿qué queremos que el cliente haga al ver esto?"* — nada decorativo.
- Alcance: análisis **descriptivo-predictivo, no causal** (1992–2024, sin extrapolación).

---

## Slide 3 — Dataset

- **Fuente:** Kaggle — *Danish Residential Housing Prices 1992–2024* (registros oficiales daneses).
- **Volumen:** 1,507,908 transacciones.
- **Regiones (5):** Zealand (capital/København), Jutland, Fyn & islands, Bornholm (agrupación del dataset sobre København, Sjælland, Syddanmark, Midtjylland, Nordjylland).
- **Tipologías (5):** Villa, Apartment (Ejerlejlighed), Townhouse (Rækkehus), Summerhouse (Fritidshus), Farm.
- **Variables macro incluidas:** tasa nominal, inflación anual danesa, rendimiento de bonos hipotecarios (`yield_mortgage_bonds_pct`).
- **Períodos de crisis analizados:** burbuja inmobiliaria 2006–2009 y GFC 2007–2012; shocks marcados en el dashboard (GFC, COVID, alza de tasas 2022+).

---

## Slide 4 — Hipótesis

| # | Hipótesis | Veredicto |
|---|---|---|
| **H1** | Las alzas del bono hipotecario anticipan caídas de volumen de transacciones con rezago de 1–2 trimestres | ✅ Confirmada — correlación rolling negativa en ~81 % de los trimestres; se agudiza en crisis (hasta −0.96 en la GFC) |
| **H2** | Existe una prima estructural de la capital: Zealand diverge de las provincias y la brecha no se cierra | ✅ Confirmada — Zealand 210 vs Fyn 91 (índice real, base 1992=100) |
| **H3** | Las tipologías recreativas (Summerhouse) concentran el mayor riesgo en crisis | ⚠️ **Refinada** — el riesgo resultó **urbano de bajo ticket**: Apartment y Townhouse superan en volatilidad y drawdown a Summerhouse; además el riesgo es **geográfico** (segmentación) |

*Nota oral:* H3 refutada-refinada es un punto fuerte de defensa — muestra que dejamos que los datos corrijan la intuición inicial.

---

## Slide 5 — Arquitectura: medallion Bronze → Silver → Gold

```
Kaggle CSV/Parquet (~1.5M filas)                    [Bronze · gs://danish-housing-bronze]
    ↓  limpieza P1–P8 (src/danish_housing/cleaning.py) + bitácora auditable
Silver: parquet limpio con flags                    [gs://danish-housing-silver]
    ↓  KPIs 1–5 (src/danish_housing/kpis.py) + star schema
Gold: 11 marts agregados (data/marts/*.csv)         [gs://danish-housing-gold]
    ↓
Dashboard web (Netlify) — 6 vistas
```

- **Filosofía:** las reglas de limpieza **flagean, no borran** — los marts Gold filtran por flags (`sales_type_valido & ~purchase_price_outlier`), preservando trazabilidad total.
- Todo parámetro de negocio (regiones, tipologías, crisis, años base) vive en `configs/analysis.yaml` — cero números mágicos.
- GCP: buckets por capa + runbooks de despliegue (`runbooks/`).

---

## Slide 6 — Limpieza (TB2): reglas P1–P8 con bitácora

| Regla | Acción | Filas afectadas |
|---|---|---:|
| P1 | Imputar `city` faltante → "Unknown" | 0 |
| P2 | Flag `macro_nulo` (gap macro 2023–2024) | 1,193 |
| P3 | Flag ventas no-mercado (familiares, "-", subastas) | 175,149 (~11.6 %) |
| P4 | Flag `year_build < 1800` | 0 |
| P5 | Flag outliers IQR×3 en precio y precio/m² | 24,282 + 15,217 |
| P6 | Flag período preliminar (<1995, menor completitud) | 56,043 (~3.7 %) |
| P7 | `zip_code` → string 4 dígitos (`zfill`) | todas |
| P8 | Renombrar columnas `%25` URL-encoded → `_pct` | todas |

- Cada regla loguea en `bitacora_limpieza.csv` (artefacto entregable TB2).
- Tests unitarios por regla en `tests/` (pytest).

---

## Slide 7 — KPIs analíticos (TB3/TB4)

1. **Precio Real/m²** — deflactado con IPC danés base 2024, derivado por cumulada de `dk_ann_infl_rate_pct` (fallback 2 %/año pre-1992).
2. **Índice Regional** — base 1992 = 100 por región (vista longitudinal).
3. **Drawdown** — caída % desde el máximo acumulado por región × tipología (`cummax`).
4. **Volatilidad** — desvío estándar del cambio trimestral, ventana móvil 4Q por tipología.
5. **Elasticidad volumen–bonos** — correlación rodante 8Q entre transacciones y bono hipotecario con **lag 2Q** (justificado empíricamente con cross-correlation lags 0–4Q: lag 2 está en la zona de respuesta más fuerte, comparable a lag 1).

---

## Slide 8 — Modelado predictivo (TB3)

- **Problema:** regresión supervisada; target `purchase_price` (entrenado en `log1p`, métricas back-transformadas a DKK nominal — sin inflar R² con log-scale).
- **Anti-leakage:** auditoría detectó que `sqm_price_real` (derivada del target) daba un R² = 0.97 **falso**; bloqueada vía `FORBIDDEN_FEATURE_COLUMNS`. Set final: **41 features** limpias (temporales, físicas, one-hot, frequency encoding, macro, rolling regionales causales).
- **Split temporal honesto:** train 1992–2017 (893 k) / test 2018–2024 (615 k) + TimeSeriesSplit 5 folds.

| Modelo | test R² | test MAE (DKK) | test MAPE |
|---|---:|---:|---:|
| M1 Linear | 0.250 | 1,166,372 | 79.1 % |
| M2 Ridge | 0.250 | 1,165,929 | 79.0 % |
| M3 RandomForest | 0.237 | 1,033,858 | 43.9 % |
| **M4 XGBoost (Optuna 30 trials, GPU L4)** | **0.440** | **866,618** | **37.0 %** |

*Nota oral:* R²=0.44 es modesto por diseño: el test cae en el boom post-COVID (*distribution shift*), el escenario realista de producción. El gap train→test (0.75→0.44) refleja ese shift, no overfitting.

---

## Slide 9 — Segmentación no supervisada (Entrega 6): PCA + KMeans + t-SNE

![PCA y t-SNE de la segmentación por código postal](docs/refs/segmentation_pca_tsne.png)

- **Pregunta:** ¿se agrupan los códigos postales en perfiles riesgo-retorno homogéneos?
- **Features (6, por zip):** nivel de precio real, CAGR real, volatilidad, max drawdown, liquidez (log), momentum reciente. Filtros de calidad: ≥10 años de historia, ≥15 transacciones/año → **483 de 932 zips** (sesgo de selección hacia mercados líquidos, declarado).
- **Método:** winsorización p1–p99 → StandardScaler → PCA (2 comp = 63.6 % varianza; PC1 = eje riesgo-retorno, 43.4 %) → KMeans sobre las 6 features estandarizadas, **k elegido por silueta** (máx 0.265 en k=2) → **t-SNE como exploración visual complementaria** (no "validación": t-SNE puede exagerar separaciones).
- **Reproducible:** `random_state=42`, parámetros en YAML, script `scripts/run_segmentation.py` + notebook `notebook/TF_segmentacion_pca_kmeans.ipynb`.

---

## Slide 10 — Resultado de la segmentación: dos perfiles de mercado

| Cluster | n zips | Precio real/m² | CAGR | Volatilidad | Drawdown medio |
|---|---:|---:|---:|---:|---:|
| **Precio alto / dinámico / estable** (metro de Copenhague, Zealand 51 %) | 229 | 24,848 | +2.5 %/año | 0.19 | **−41.9 %** |
| **Precio bajo / plano / volátil** (Jutland/provincias) | 254 | 12,979 | +1.1 %/año | 0.42 | **−62.0 %** |

- El segmento barato **duplica la volatilidad (2.3×)** y sufre drawdowns **20 pp más profundos** — el peor binomio riesgo-retorno.
- **Matiz metodológico (honestidad):** las features derivan de precios correlacionados con la región, así que redescubrir Capital vs. Provincias es *esperable* — el resultado es **consistente con H2**, no una confirmación independiente. El aporte real: **granularidad a nivel zip** y **cuantificación del gap**.
- Silueta 0.265 = estructura **moderada**: un continuo con dos modos, no poblaciones disjuntas (reportado tal cual).

---

## Slide 11 — Hallazgos clave (los 4 mensajes)

1. **Divergencia regional estructural:** índice real 2024Q4 (base 1992=100): **Zealand 210 · Bornholm 141 · Jutland 110 · Fyn & islands 91**. La capital más que duplicó; Fyn sigue bajo su nivel de 1992. La brecha no se cerró tras las crisis → restricción de oferta urbana estructural.
2. **El riesgo es urbano, no recreativo (H3 refinada):** Apartment (σ=9.2, drawdown −92.1 %) y Townhouse (σ=10.2, −80.7 %) superan a Summerhouse (σ=3.9, −63.1 %); **Villa es el activo más estable** (σ=2.3, −44.1 %). Peor caso del dataset: Bornholm/Apartment 2018Q3 = **−92.1 %** (amplificado por liquidez n=5).
3. **La geografía duplica el riesgo:** segmentación zip-level — el segmento bajo-ticket combina menor retorno con drawdown −62 % vs −42 %.
4. **Transmisión hipotecaria asimétrica (H1):** correlación volumen↔bonos negativa en ~81 % de los trimestres, se agudiza hasta **−0.96 en la GFC** y se relaja en expansión → el canal de crédito opera sobre todo bajo estrés.

---

## Slide 12 — El dashboard: 6 vistas en secuencia narrativa

**Orden narrativo (numerado 1–6 en la UI, con puentes de transición entre pestañas):**

| # | Vista | Rol | Qué hace el cliente aquí |
|---|---|---|---|
| 1 | **Resumen** | Contexto: pregunta, KPIs, insight → driver → acción, semáforo H1/H2/H3 | Entiende el mensaje en 30 segundos |
| 2 | **Precios** | **Vista longitudinal**: índice regional 1992–2024, precio real/m², shocks marcados | Ve la divergencia capital-provincias en el tiempo |
| 3 | **Crisis y Riesgo** | Drawdowns y volatilidad por tipología cuando el ciclo golpea | Identifica qué tipologías evitar en crisis |
| 4 | **Geografía** | **Vista transversal**: mapa coroplético por zip con toggle **precio ↔ segmento riesgo-retorno**, heatmap región × tipología | Decide en qué zonas concentrar/evitar exposición |
| 5 | **Modelado** | Comparación de modelos, feature importance, decisiones de visualización (incl. gráficos descartados y por qué) | Confía en la base técnica |
| 6 | **Conclusiones** | H1/H2/H3 + sección **"¿Qué hacer con esto?"** con 3 recomendaciones | Se lleva acciones concretas |

- Stack: HTML + Chart.js + Leaflet + TopoJSON, alimentado por los marts Gold reales (`gs://danish-housing-gold/marts/`), desplegado en Netlify.
- Anotaciones de eventos (reforma hipotecaria 1995, GFC, COVID, alza 2022) sobre las series.

---

## Slide 13 — Recomendaciones al cliente (cierre del dashboard)

1. **Timing de entrada (H1):** en fases de alza del bono hipotecario, esperar 1–2 trimestres antes de comprar — el volumen cae con rezago (correlación negativa en 81 % de los trimestres).
2. **Selección tipología-región (H2/H3):** priorizar **Villa en Zealand** (drawdown −22.8 %) sobre **Apartment en provincias** (Jutland −56.9 %, Bornholm −92.1 %) — la escasez de oferta capitalina protege el precio en las caídas.
3. **Exclusión de zonas (segmentación):** evitar concentración en zips del segmento "precio bajo / plano / volátil": CAGR 1.1 %, volatilidad 2.3× y drawdown histórico −62 %.
4. **Monitoreo:** usar el bono hipotecario danés como *leading indicator* (~2 trimestres).

---

## Slide 14 — Calidad: QA técnico y accesibilidad

**QA automatizado (`scripts/run_qa.py`) — 23/23 chequeos OK:**
- Integridad: presencia y esquema de los marts, rangos válidos (drawdown ∈ [−100, 0], índice > 0), sin nulos en claves, integridad referencial zips ⊆ mapa (0 huérfanos), consistencia segmentos↔perfiles (483 = 483).
- **Reconciliación:** cada cifra del informe y del dashboard se **re-deriva desde los marts** y debe coincidir (peor drawdown, rankings, índice Zealand 210, XGBoost R²=0.44, k=2…). Sale ≠ 0 si algo falla → quality gate de CI-manual.
- Star schema validado: 0 huérfanos, 0 duplicados.

**Accesibilidad verificada (`docs/verificacion-accesibilidad.md`):**
- **Contraste WCAG AA:** 25 pares texto/fondo corregidos — 100 % pasan (≥4.5:1).
- **Daltonismo:** simulación protanopia/deuteranopia sobre todas las paletas; 3 colisiones corregidas (Zealand/Fyn, Villa/Townhouse, períodos de crisis); paleta de segmentos azul/naranja segura por diseño.
- **ARIA:** roles de tablist/tab/tabpanel, `aria-label` con el hallazgo en cada gráfico y en el mapa, headings jerárquicos, focus visible.
- Títulos **analíticos** (afirman el hallazgo) y ejes con unidades explícitas.

---

## Slide 15 — Reproducibilidad y pipeline de ejecución

```bash
uv sync --extra dev --extra notebook                                        # entorno
uv run python scripts/run_cleaning.py  --config configs/analysis.yaml       # Bronze → Silver (TB2)
uv run python scripts/run_pipeline.py  --config configs/analysis.yaml       # Silver + marts Gold (TB3)
uv run python scripts/export_marts.py  --config configs/analysis.yaml       # marts standalone
uv run python scripts/run_segmentation.py --config configs/analysis.yaml    # PCA/KMeans/t-SNE (TF)
uv run python scripts/run_qa.py                                             # quality gate 23/23
uv run pytest tests/                                                        # tests de limpieza
```

- Determinismo: semillas fijas (`random_state=42`), parámetros centralizados en `configs/analysis.yaml`.
- Runbooks end-to-end en `runbooks/` (ejecución completa, GCP medallion, GPU en Lightning.ai).
- Notebooks entregables: TB2 (perfilado/limpieza), TB3 (preprocesamiento/modelado), TB4 (segmentación por reglas + cálculos), **TF (PCA/KMeans/t-SNE)** — todos ejecutados con outputs.

---

## Slide 16 — Límites y supuestos (control de la defensa)

- Análisis **descriptivo-predictivo, no causal**; no se extrapola fuera de 1992–2024.
- **Deflactor derivado**, no observado: IPC reconstruido por cumulada de la inflación anual (fallback 2 % pre-1992) — todo "precio real" depende de esa aproximación.
- Precisión espacial a nivel de código postal (sin coordenadas exactas de propiedades).
- Gap macro 2023–2024 y período preliminar 1992–1994 **flagueados**, no ocultados.
- Segmentación: solo mercados líquidos (483/932 zips); silueta 0.265 = estructura moderada; descriptiva, no predictiva.
- Lag 2Q elegido a priori por el ciclo hipotecario; cross-correlation empírica lo ubica en la zona fuerte (lag 1 comparable) — documentado con honestidad.
- R² 0.44 refleja el distribution shift post-COVID del test out-of-time — el escenario realista.

---

## Slide 17 — Cobertura del curso y cierre

- **TB1** ficha y pregunta → **TB2** perfilado + limpieza con bitácora → **TB3** feature engineering anti-leakage + 4 modelos → **TB4** star schema + segmentación por reglas + KPIs → **TF** segmentación no supervisada + dashboard final + QA + accesibilidad.
- Vista **longitudinal** (índice/drawdowns 1992–2024) y **transversal** (mapa/heatmap/segmentos) claramente defendibles.
- El dashboard **responde la pregunta principal sin explicación externa**: pregunta en el header, semáforo de hipótesis, takeaway por gráfico y cierre accionable.
- Producto publicable: **demo funcional en vivo** → https://gruvizzgobpe.netlify.app/

---

## Anexo — Inventario de activos para las slides

| Activo | Ruta | Uso sugerido |
|---|---|---|
| Figura PCA + t-SNE | `docs/refs/segmentation_pca_tsne.png` | Slide 9 (única imagen estática del repo; el resto se captura del dashboard en vivo) |
| Dashboard en vivo | https://gruvizzgobpe.netlify.app/ | Screenshots de cada pestaña para slides 11–13 |
| Metodología segmentación | `docs/segmentation-pca-clustering-methodology.md` | Backup Q&A |
| Reporte de métricas TB3 | `docs/reporte-metricas-tb3.md` | Backup Q&A modelado |
| Verificación accesibilidad | `docs/verificacion-accesibilidad.md` | Slide 14 / evidencia |
| QA técnico | `docs/qa-tecnico.md` + `scripts/run_qa.py` | Slide 14 / demo en vivo del gate |
| Resumen ejecutivo | `docs/resumen-ejecutivo.md` | Base del guion oral |
| Informe Entrega 6 | `docs/informe-entrega6-secciones.md` | Texto pasteable |
| Notebooks | `notebook/TB2…`, `TB3…`, `TB4…`, `TF_segmentacion_pca_kmeans.ipynb` | Evidencia de cobertura |
