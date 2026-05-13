# Cloud Architecture — Danish Housing Analysis

**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024  
**Infraestructura**: Google Cloud Platform (GCP)

---

## Diagrama General

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE CLOUD PLATFORM                           │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   BRONZE     │    │   SILVER     │    │    GOLD      │              │
│  │  GCS Bucket  │───▶│  GCS Bucket  │───▶│  GCS Bucket  │──▶ Tableau  │
│  │  (raw data)  │    │  (clean data)│    │  (marts)     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         ▲                   ▲                   ▲                       │
│         │                   │                   │                       │
│    Kaggle CSV          TB2 Pipeline         TB3 Pipeline                │
│                      (cleaning.py)         (marts.py)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Componentes

### 1. Google Cloud Storage (GCS) — Arquitectura Medallion

| Capa | Bucket | Contenido | Quién escribe | Quién lee |
|------|--------|-----------|---------------|-----------|
| **Bronze** | `danish-housing-bronze` | CSV crudo de Kaggle, sin modificar | Pipeline de ingesta manual | Pipeline Silver |
| **Silver** | `danish-housing-silver` | Parquet limpio (flags P1–P8) + bitácora | `run_cleaning.py` (TB2) | Pipeline Gold |
| **Gold** | `danish-housing-gold` | CSVs de marts para Tableau | `export_marts.py` (TB3) | Tableau Desktop |

### 2. Flujo de datos

```
Kaggle Dataset (CSV ~1.5M filas)
        │
        ▼
[Bronze] danish-housing-bronze/raw/danish_housing_prices.csv
        │
        │  scripts/run_cleaning.py
        │  → Aplica reglas P1–P8
        │  → Crea flags de calidad
        │
        ▼
[Silver] danish-housing-silver/processed/
        ├── danish_housing_clean.parquet    (~1.45M filas, 20+ columnas)
        └── bitacora_limpieza.csv           (8 entradas)
        │
        │  scripts/export_marts.py
        │  → Agrega por región/trimestre
        │  → Calcula KPIs (índice, drawdown, volatilidad)
        │
        ▼
[Gold] danish-housing-gold/marts/
        ├── mart_quarterly_regional_index.csv
        ├── mart_drawdowns.csv
        ├── mart_volatility.csv
        ├── mart_macro_correlation.csv
        ├── mart_transactions_map.csv
        ├── mart_model_comparison.csv
        ├── mart_predictions.csv
        └── mart_feature_importance.csv
        │
        ▼
   Tableau Desktop
   (conecta a Gold via CSV descargado o URL pública)
```

---

## Configuración de Buckets GCP

### Crear buckets (una sola vez)

```bash
gcloud config set project danish-housing-upc

# Bronze: almacenamiento frío, append-only
gsutil mb -l us-central1 -c STANDARD gs://danish-housing-bronze

# Silver: acceso frecuente durante desarrollo
gsutil mb -l us-central1 -c STANDARD gs://danish-housing-silver

# Gold: acceso público de lectura para Tableau
gsutil mb -l us-central1 -c STANDARD gs://danish-housing-gold
```

### Permisos de lectura pública para Gold (Tableau)

```bash
gsutil iam ch allUsers:objectViewer gs://danish-housing-gold
```

Esto permite que Tableau descargue los marts sin necesitar credenciales.

---

## Estructura de archivos en GCS

```
gs://danish-housing-bronze/
└── raw/
    └── danish_housing_prices.csv          ← Kaggle, append-only

gs://danish-housing-silver/
└── processed/
    ├── danish_housing_clean.parquet
    └── bitacora_limpieza.csv

gs://danish-housing-gold/
└── marts/
    ├── mart_quarterly_regional_index.csv
    ├── mart_drawdowns.csv
    ├── mart_volatility.csv
    ├── mart_macro_correlation.csv
    ├── mart_transactions_map.csv
    ├── mart_model_comparison.csv
    ├── mart_predictions.csv
    └── mart_feature_importance.csv
```

---

## Costos estimados (proyecto académico)

| Recurso | Estimado |
|---------|----------|
| Storage Bronze (~200MB CSV) | ~$0.004/mes |
| Storage Silver (~300MB parquet) | ~$0.006/mes |
| Storage Gold (~50MB CSVs) | ~$0.001/mes |
| Transferencia saliente (<1GB/mes) | Gratis |
| **Total mensual** | **< $0.02/mes** |

> GCP ofrece $300 de crédito gratuito para cuentas nuevas.

---

## Autenticación

```bash
# Desarrollo local
gcloud auth application-default login

# Verificar acceso a los buckets
gsutil ls gs://danish-housing-bronze/
gsutil ls gs://danish-housing-silver/
gsutil ls gs://danish-housing-gold/
```

---

## Decisiones de diseño

| Decisión | Alternativa considerada | Razón de elección |
|----------|------------------------|-------------------|
| GCS + CSV/Parquet | BigQuery | Simplicidad para proyecto académico; Tableau lee CSV directamente |
| Parquet en Silver | CSV | 3–5× menor tamaño, lectura más rápida con pandas |
| CSV en Gold | Parquet | Tableau Desktop puede conectar CSV sin plugins adicionales |
| us-central1 | southamerica-east1 | Menor costo; latencia no crítica en análisis por lotes |
