# QA Técnico — Entrega 6 (TF)

Checklist de aseguramiento de calidad de la capa Gold, con verificación **automatizada** y
reproducible. El objetivo es garantizar que (a) los datos son íntegros, (b) el pipeline es
reproducible end-to-end y (c) **las cifras que aparecen en el informe y en el dashboard se
re-derivan de los marts** y coinciden.

## Cómo ejecutar

```bash
# 1. Regenerar la capa Gold desde Silver (marts de KPIs)
uv run python scripts/export_marts.py --config configs/analysis.yaml

# 2. Regenerar la segmentación no supervisada (PCA + KMeans + t-SNE)
uv run python scripts/run_segmentation.py --config configs/analysis.yaml

# 3. Quality gate automatizado (sale != 0 si algo falla)
uv run python scripts/run_qa.py

# 4. Tests unitarios de las reglas de limpieza
uv run pytest tests/ -q
```

## Resultado de la última corrida

`scripts/run_qa.py` → **23/23 chequeos OK**.

## A. Integridad de datos

| Chequeo | Criterio | Estado |
|---|---|---|
| Presencia de marts | 8 marts Gold existen y tienen filas | ✅ |
| Esquema | cada mart contiene sus columnas mínimas | ✅ |
| Rango de drawdown | `drawdown_pct ∈ [-100, 0]` (sin valores imposibles) | ✅ (min −92.11) |
| Índice regional | `regional_index > 0` en todas las filas | ✅ (min 51.5) |
| Nulos en claves | sin nulos en columnas clave de drawdowns y segmentos | ✅ |
| **Integridad referencial** | todos los zips segmentados existen en `mart_transactions_map` | ✅ (0 huérfanos) |
| Consistencia segmentos↔perfiles | mismos clusters y `Σ n_zips == n filas` | ✅ (483=483) |

## B. Reconciliación informe/dashboard ↔ marts

Cada cifra citada en el resumen ejecutivo y en el dashboard se recalcula desde los marts:

| Cifra publicada | Fuente (mart) | Verificación |
|---|---|---|
| Peor drawdown **−92.1 %** (Bornholm/Apartment/2018Q3) | `mart_drawdowns` | ✅ −92.11 % |
| Ranking riesgo: Apartment peor → Villa mejor | `mart_drawdowns` | ✅ Apartment > Townhouse > Farm > Summerhouse > Villa |
| Volatilidad: Townhouse/Apartment top, Villa fondo | `mart_volatility` | ✅ mismo orden |
| Índice **Zealand 2024Q4 ≈ 210** (>2× base 1992) | `mart_quarterly_regional_index` | ✅ 210.3 |
| Fyn & islands **< 100** (bajo su nivel de 1992) | `mart_quarterly_regional_index` | ✅ 90.8 |
| Campeón **XGBoost R²=0.44, MAE≈867k DKK** | `mart_model_comparison` | ✅ R²=0.440, MAE 866 618 |
| Segmentación: **2 clusters** (k por silueta) | `mart_segment_profiles` | ✅ |
| Cluster caro tiene menor drawdown que el barato | `mart_segment_profiles` | ✅ −41.9 % vs −62.0 % |

## C. Reproducibilidad end-to-end

- **Determinismo:** PCA, KMeans y t-SNE usan `random_state = 42`; dos corridas producen los mismos
  clusters y marts idénticos.
- **Sin números mágicos:** todos los parámetros de negocio viven en `configs/analysis.yaml`
  (limpieza P1–P8, KPIs, `marts`, `segmentation`). El código los lee vía `yaml.safe_load`.
- **Trazabilidad TB2:** las reglas de limpieza flaguean en vez de borrar; la bitácora
  (`bitacora_limpieza.csv`) registra cada transformación.
- **Entorno fijado:** dependencias congeladas en `uv.lock`; Python ≥ 3.12.
- **Cobertura de tests:** `tests/test_cleaning.py` cubre las 8 reglas de limpieza.

## D. Accesibilidad y diseño visual (validación manual)

| Ítem | Estado |
|---|---|
| Tema del dashboard en **modo claro** (contraste sobre fondo blanco) | ✅ |
| Ejes, grillas y etiquetas legibles en claro (texto oscuro, grilla suave) | ✅ |
| Títulos **analíticos** (no meramente descriptivos) en cada vista | ✅ |
| Tooltips con `n_transactions` para evitar malinterpretar zonas de baja muestra | ✅ |
| Paleta categórica consistente por región/tipología entre vistas | ✅ |
| **Gobernanza de color**: 3 capas separadas (categórica / magnitud rosa / editorial slate), sin hues con doble significado | ✅ |
| Eliminado el banner de metadatos técnicos (`gs://…`) de la vista del usuario | ✅ |
| Pendiente sugerido: verificación formal de ratios WCAG AA y simulación de daltonismo | ⬜ |

Detalle de la gobernanza de color en `docs/informe-entrega6-secciones.md → sección 32`.

## Issues conocidos / pendientes

- La silueta de la segmentación (0.27) indica estructura **moderada**: se reporta como continuo
  riesgo-retorno con dos modos, no como poblaciones disjuntas.
- 449 zips de baja cobertura (<10 años o <15 txns/año) quedan fuera de la segmentación por diseño.
- Falta la verificación formal de accesibilidad (WCAG AA / daltonismo) como artefacto documentado.
