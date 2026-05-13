# Estado Actual del Proyecto

**Última actualización**: Semana 7 — Entrega TB3  
**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024

---

## Estado por Entregable

| Entregable | Estado | Semana | Notas |
|-----------|--------|--------|-------|
| TB1 — Ficha del proyecto | ✅ Completo | S2 | Pregunta analítica, dataset, KPIs definidos |
| TB2 — Perfilado y Limpieza | ✅ Completo | S4 | Reglas P1–P8 implementadas y documentadas |
| TB3 — Modelado y Métricas | 🔄 En progreso | S7 | Notebook + comparativa + reporte |
| TF — Dashboard Tableau | ⏳ Pendiente | S13 | — |

---

## Componentes Listos

### Código
- [x] `src/danish_housing/cleaning.py` — reglas P1–P8 como funciones Python
- [x] `src/danish_housing/kpis.py` — cálculo de los 5 KPIs
- [x] `scripts/run_cleaning.py` — pipeline ejecutable Bronze → Silver
- [x] `scripts/upload_to_gcs.py` — upload a GCP (Bronze / Silver / Gold)
- [x] `tests/test_cleaning.py` — tests unitarios para las 8 reglas de limpieza

### Documentación
- [x] `docs/cloud-architecture.md` — arquitectura GCP Medallion
- [x] `docs/preprocessing-medallion-pipeline.md` — pipeline paso a paso
- [x] `docs/data-dictionary-gold.md` — diccionario de todas las variables
- [x] `docs/forecasting-optimization-methodology.md` — metodología de modelado
- [x] `docs/tableau-dashboard-design.md` — diseño de las 5 vistas del dashboard
- [x] `docs/reporte-metricas-tb3.md` — reporte de métricas y decisión del modelo
- [x] `runbooks/gcp-medallion-setup.md` — guía para crear buckets en GCP

### Notebooks
- [x] `notebook/TB2_perfilado_limpieza.ipynb` — perfilado y limpieza (entregado S4)
- [x] `notebook/TB3_preprocesamiento_modelado.ipynb` — modelado (entrega S7)

### Configuración
- [x] `configs/analysis.yaml` — todos los parámetros centralizados
- [x] `requirements.txt` — dependencias completas
- [x] `.gitignore` — excluye datos y entornos

---

## Pendiente para TB3 (Sábado)

- [ ] Ejecutar `TB3_preprocesamiento_modelado.ipynb` con datos reales (no sintéticos)
- [ ] Obtener métricas exactas del modelo con 1.5M registros
- [ ] Crear los 3 buckets en GCP y subir las capas
- [ ] Verificar que `gsutil ls gs://danish-housing-gold/marts/` muestra los marts
- [ ] Completar `scripts/export_marts.py` (generación automática de marts Gold)

---

## Pendiente para TF (Semana 13)

- [ ] Conectar Tableau a Gold layer (CSV desde GCS o local)
- [ ] Construir Vista 1: Línea de tiempo regional con overlay macroeconómico
- [ ] Construir Vista 2: Mapa choropleth por zip_code
- [ ] Construir Vista 3: Drawdowns por tipología (crisis 2007–2012)
- [ ] Construir Vista 4: Volatilidad comparada por tipología
- [ ] Construir Vista 5: Correlación volumen-bonos
- [ ] Calcular LODs: índice regional, pico histórico, drawdown
- [ ] Publicar en Tableau Public
- [ ] Grabar video demo (5 min)

---

## Arquitectura GCP — Estado

| Bucket | Creado | Datos subidos |
|--------|--------|--------------|
| `danish-housing-bronze` | ⏳ Pendiente | ⏳ |
| `danish-housing-silver` | ⏳ Pendiente | ⏳ |
| `danish-housing-gold` | ⏳ Pendiente | ⏳ |

---

## División de Tareas (Semanas 5–7)

| Tarea | Responsable | Estado |
|-------|-------------|--------|
| Análisis series temporales + Índice Regional | Rody Vilchez | 🔄 |
| Drawdowns crisis 2007–2012 + correlación macro | Diego Ballón | 🔄 |
| Volatilidad por tipología + marts Gold + GCP | Christian Velásquez | 🔄 |
