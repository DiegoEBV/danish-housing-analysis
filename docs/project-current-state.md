# Estado Actual del Proyecto

**Última actualización**: Entrega 6 — TF (Trabajo Final y defensa)
**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024
**Dashboard en vivo**: https://gruvizzgobpe.netlify.app/

---

## Estado por Entregable

| Entregable | Estado | Semana | Notas |
|-----------|--------|--------|-------|
| TB1 — Ficha del proyecto | ✅ Completo | S2 | Pregunta analítica, dataset, KPIs |
| TB2 — Perfilado y Limpieza | ✅ Completo | S4 | Reglas P1–P8 + bitácora |
| TB3 — Modelado y Métricas | ✅ Completo | S7 | M1–M4, XGBoost campeón, marts modelado |
| TB4 — Segmentación y cálculos | ✅ Completo | S9 | Star schema + segmentación por reglas + 5 KPIs |
| **TF — Trabajo final + defensa** | 🔄 En progreso | S15 | Dashboard, segmentación no supervisada, QA, defensa |

---

## Avance Entrega 6 (TF)

### ✅ Completado

- **Segmentación no supervisada (PCA + KMeans + t-SNE)** — `scripts/run_segmentation.py`.
  Segmenta 483 códigos postales por perfil riesgo-retorno en 2 clusters (k por silueta).
  Docu: `docs/segmentation-pca-clustering-methodology.md`. Marts: `mart_zip_segments.csv`,
  `mart_segment_profiles.csv`. Figura: `docs/refs/segmentation_pca_tsne.png`.
- **Resumen ejecutivo** — `docs/resumen-ejecutivo.md`.
- **QA técnico automatizado** — `scripts/run_qa.py` (23/23 OK) + `docs/qa-tecnico.md`.
- **Dashboard en modo claro** — `danish_housing_dashboard.html` (accesibilidad/contraste).
- **Base final** — star schema validado (0 huérfanos, 0 duplicados) + 7 marts Gold.
- **Pipeline reproducible** — scripts + `configs/analysis.yaml` + runbooks.

### 🔄 / ⬜ Pendiente

- ⬜ **Decisión de formato del dashboard**: el entregable pide "dashboard en Tableau"; el producto
  actual es HTML/Chart.js (Netlify). Confirmar con el docente si el HTML se acepta como demo
  funcional o si se migra a Tableau (`.twbx`).
- ⬜ **Presentación de defensa** (slides).
- ⬜ **Historia visual / guion de defensa**.
- ⬜ Integrar la capa de segmentación al mapa del dashboard (colorear zips por `cluster_label`).
- ⬜ Verificación formal de accesibilidad (WCAG AA / simulación de daltonismo).
- ⬜ Notebook final que consolide la técnica de segmentación de la Entrega 6.

---

## Marts Gold (capa `data/marts/` · bucket `danish-housing-gold`)

| Mart | Grano | Vista |
|---|---|---|
| `mart_quarterly_regional_index.csv` | region × quarter | Precios / índice regional |
| `mart_drawdowns.csv` | region × house_type × quarter | Crisis y Riesgo |
| `mart_volatility.csv` | house_type × quarter | Resumen / Volatilidad |
| `mart_macro_correlation.csv` | quarter | Conclusiones / macro |
| `mart_transactions_map.csv` | zip_code × year | Geografía / mapa |
| `mart_model_comparison.csv` · `mart_model_cv.csv` · `mart_feature_importance.csv` · `mart_predictions_sample.csv` | modelo | Modelado |
| **`mart_zip_segments.csv`** *(nuevo)* | zip_code | Geografía / segmentos |
| **`mart_segment_profiles.csv`** *(nuevo)* | cluster | Geografía / perfiles |

---

## Comandos clave (Entrega 6)

```bash
uv sync                                                   # entorno
uv run python scripts/export_marts.py --config configs/analysis.yaml       # marts KPIs
uv run python scripts/run_segmentation.py --config configs/analysis.yaml   # PCA/KMeans/t-SNE
uv run python scripts/run_qa.py                           # quality gate (23/23)
uv run pytest tests/ -q                                   # tests limpieza
```

---

## División de Tareas

| Tarea | Responsable |
|-------|-------------|
| Series temporales + Índice Regional | Rody Vilchez |
| Drawdowns + correlación macro | Diego Ballón |
| Volatilidad + marts Gold + GCP + segmentación | Christian Velásquez |
