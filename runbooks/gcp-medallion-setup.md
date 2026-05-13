# Runbook — Arquitectura Medallion en GCP

## Qué es la Arquitectura Medallion

Organiza los datos en 3 capas progresivas en Google Cloud Storage (GCS):

```
Kaggle CSV
    ↓
┌─────────────────────────────────────────────────────────┐
│  BRONZE  gs://danish-housing-bronze/raw/                │
│  Datos crudos, sin modificar, tal como llegan           │
└──────────────────────────┬──────────────────────────────┘
                           ↓ Pipeline TB2 (cleaning.py)
┌─────────────────────────────────────────────────────────┐
│  SILVER  gs://danish-housing-silver/processed/          │
│  Datos limpios con flags de calidad (P1–P8)             │
└──────────────────────────┬──────────────────────────────┘
                           ↓ Pipeline TB3 (marts)
┌─────────────────────────────────────────────────────────┐
│  GOLD    gs://danish-housing-gold/marts/                │
│  Marts analíticos listos para Tableau                   │
└─────────────────────────────────────────────────────────┘
                           ↓
                      Tableau Desktop
```

---

## Paso 1 — Crear proyecto en GCP

1. Ir a https://console.cloud.google.com
2. Crear nuevo proyecto: `danish-housing-upc`
3. Habilitar la API de Cloud Storage:
   ```
   Menú → APIs y servicios → Biblioteca → Cloud Storage → Habilitar
   ```

---

## Paso 2 — Crear los 3 buckets

En la consola GCP → Cloud Storage → Crear bucket:

| Bucket | Nombre | Región sugerida |
|--------|--------|----------------|
| Bronze | `danish-housing-bronze` | us-central1 |
| Silver | `danish-housing-silver` | us-central1 |
| Gold   | `danish-housing-gold`   | us-central1 |

**Configuración recomendada para cada bucket:**
- Clase de almacenamiento: **Standard**
- Control de acceso: **Uniforme**
- Protección de datos: Desactivar versioning (proyecto académico)

O con gcloud CLI (más rápido):
```bash
gcloud config set project danish-housing-upc

gsutil mb -l us-central1 gs://danish-housing-bronze
gsutil mb -l us-central1 gs://danish-housing-silver
gsutil mb -l us-central1 gs://danish-housing-gold
```

---

## Paso 3 — Autenticación local

```bash
# Instalar Google Cloud SDK (si no está)
# https://cloud.google.com/sdk/docs/install

# Login
gcloud auth application-default login

# Verificar
gcloud auth list
```

---

## Paso 4 — Instalar dependencias Python

```bash
pip install google-cloud-storage
```

---

## Paso 5 — Subir cada capa

### Bronze (datos crudos de Kaggle)
```bash
python scripts/upload_to_gcs.py --layer bronze --config configs/analysis.yaml
```
Sube: `danish_housing_prices.csv` → `gs://danish-housing-bronze/raw/`

### Silver (datos limpios del TB2)
```bash
# Primero ejecutar limpieza si no tienes el parquet
python scripts/run_cleaning.py --config configs/analysis.yaml

# Luego subir
python scripts/upload_to_gcs.py --layer silver --config configs/analysis.yaml
```
Sube:
- `danish_housing_clean.parquet` → `gs://danish-housing-silver/processed/`
- `bitacora_limpieza.csv` → `gs://danish-housing-silver/processed/`

### Gold (marts del TB3 para Tableau)
```bash
# Primero ejecutar el notebook TB3 completo para generar los marts
# Luego subir
python scripts/upload_to_gcs.py --layer gold --config configs/analysis.yaml
```
Sube todos los CSVs de `data/processed/gold/` → `gs://danish-housing-gold/marts/`

### Todo de una vez
```bash
python scripts/upload_to_gcs.py --layer all --config configs/analysis.yaml
```

---

## Paso 6 — Verificar en la consola GCP

```
Cloud Storage → Buckets → danish-housing-bronze → raw/ → danish_housing_prices.csv ✓
Cloud Storage → Buckets → danish-housing-silver → processed/ → danish_housing_clean.parquet ✓
Cloud Storage → Buckets → danish-housing-gold   → marts/ → mart_*.csv ✓
```

O con gsutil:
```bash
gsutil ls gs://danish-housing-bronze/raw/
gsutil ls gs://danish-housing-silver/processed/
gsutil ls gs://danish-housing-gold/marts/
```

---

## Paso 7 — Conectar Tableau a Gold

1. En Tableau Desktop → Conectar → Google Cloud Storage
   - O conectar via CSV desde URL pública del bucket Gold
2. Alternativa (más simple): Tableau → Conectar → Texto (CSV) → subir mart desde local

---

## Estructura final en GCS

```
gs://danish-housing-bronze/
└── raw/
    └── danish_housing_prices.csv          ← Kaggle original

gs://danish-housing-silver/
└── processed/
    ├── danish_housing_clean.parquet       ← TB2 output
    └── bitacora_limpieza.csv              ← log de transformaciones

gs://danish-housing-gold/
└── marts/
    ├── mart_model_comparison.csv          ← comparativa de modelos
    ├── mart_predictions.csv               ← predicciones RF
    ├── mart_feature_importance.csv        ← importancia de variables
    ├── mart_quarterly_regional_index.csv  ← para vista 1 Tableau
    ├── mart_drawdowns.csv                 ← para vista 3 Tableau
    └── mart_volatility.csv                ← para vista 4 Tableau
```

---

## Costos estimados (proyecto académico)

| Recurso | Costo aproximado |
|---------|-----------------|
| Storage 3 buckets (~2GB total) | ~$0.05/mes |
| Transferencia de datos | Gratis (< 1GB/mes) |
| **Total** | **< $0.10/mes** |

GCP ofrece $300 de crédito gratuito para cuentas nuevas — más que suficiente para este proyecto.
