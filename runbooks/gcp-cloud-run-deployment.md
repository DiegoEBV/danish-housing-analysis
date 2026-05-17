# Runbook: Deployment del pipeline a Cloud Run Job

**Issue bd**: `danish-housing-analysis-chl` (Fase 6 del plan TB3)
**Estado**: 🔄 Documentación inicial; implementación pendiente

## Objetivo

Ejecutar `scripts/run_pipeline.py` como Cloud Run Job, leyendo raw desde
`gs://danish-housing-bronze/` y escribiendo Silver/Gold a sus buckets.
Permite refrescar el pipeline a demanda (o por cron via Cloud Scheduler) sin
montar VMs persistentes.

## Arquitectura

```
Artifact Registry          Cloud Run Job             GCS buckets
─────────────────          ──────────────            ───────────
pipeline:latest    ──run─> danish-housing-pipeline ──> bronze/silver/gold
                                  ↑
                            Cloud Scheduler (opcional, mensual)
```

## Prerequisitos

1. Proyecto GCP creado (`project-43d6b6df-15b5-4496-a5e` o el que definas en
   `configs/analysis.yaml -> gcp.project_id`).
2. APIs habilitadas:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     artifactregistry.googleapis.com \
     storage.googleapis.com
   ```
3. Artifact Registry repo:
   ```bash
   gcloud artifacts repositories create danish-housing \
     --repository-format=docker --location=europe-west1
   ```
4. Service account con permisos `roles/storage.objectAdmin` sobre los 3 buckets.

## Build y push de imagen

```bash
gcloud builds submit --config=cloudbuild.yaml --substitutions=_TAG=latest
```

Esto usa `cloudbuild.yaml` en raíz que builds el `Dockerfile` y empuja a
`europe-west1-docker.pkg.dev/<PROJECT>/danish-housing/pipeline:latest`.

## Crear el Cloud Run Job (una vez)

```bash
gcloud run jobs create danish-housing-pipeline \
  --image=europe-west1-docker.pkg.dev/$PROJECT_ID/danish-housing/pipeline:latest \
  --region=europe-west1 \
  --service-account=danish-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --memory=8Gi \
  --cpu=4 \
  --max-retries=1 \
  --task-timeout=3600 \
  --set-env-vars=GCP_PROJECT=$PROJECT_ID
```

> **Memoria**: 1.2M filas + XGBoost+Optuna requieren ~6-8 GiB peak. Si solo
> se ejecuta cleaning + marts (sin modelado), 4 GiB es suficiente.

## Ejecutar el Job a demanda

```bash
gcloud run jobs execute danish-housing-pipeline --region=europe-west1 --wait
```

Logs:
```bash
gcloud run jobs executions list --job=danish-housing-pipeline --region=europe-west1
gcloud run jobs executions describe <EXECUTION_NAME> --region=europe-west1
```

## Configuración del Job

El container lee `configs/analysis.yaml` (copiado en build). Para ajustar:

- **Override de paths**: usar env vars `BRONZE_BUCKET`, etc. (TODO: agregar
  soporte en `run_pipeline.py` para leer estas env vars como overrides del
  YAML; hoy sólo soporta `GCP_PROJECT`).
- **Configs alternativas**: montar un YAML diferente desde GCS con
  `--update-env-vars=CONFIG_GCS=gs://.../analysis.yaml` y actualizar el
  entrypoint para descargarlo antes de correr.

## Cloud Scheduler (opcional)

Para refrescar mensualmente (el dataset no se actualiza, pero sirve como demo):

```bash
gcloud scheduler jobs create http danish-housing-monthly \
  --schedule="0 3 1 * *" \
  --uri="https://europe-west1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/danish-housing-pipeline:run" \
  --http-method=POST \
  --oauth-service-account-email=danish-pipeline@$PROJECT_ID.iam.gserviceaccount.com
```

## Verificación end-to-end

```bash
# 1) Subir raw a Bronze (una vez)
gcloud storage cp data/raw/DKHousingPrices.parquet gs://danish-housing-bronze/raw/

# 2) Ejecutar Job
gcloud run jobs execute danish-housing-pipeline --region=europe-west1 --wait

# 3) Validar outputs
gcloud storage ls gs://danish-housing-silver/processed/
gcloud storage ls gs://danish-housing-gold/marts/

# Espera: silver_parquet + bitacora_csv en silver bucket; 5 marts CSV en gold bucket
```

## Costes estimados

- **Build**: ~$0.10 por build (Cloud Build, E2_HIGHCPU_8, 5-10 min).
- **Run**: ~$0.02-0.05 por ejecución del Job (4 vCPU, 8 GiB, 5-15 min).
- **Storage**: <$1/mes (los 3 buckets, dataset 1.2M = ~300 MB total).
- **Scheduler**: $0.10/mes con free tier holgado.

## Pendiente para implementación completa

- [ ] Crear service account `danish-pipeline@...` con los roles correctos.
- [ ] Agregar a `run_pipeline.py` soporte para leer raw desde `gs://...` (hoy
      sólo desde filesystem). Opciones: usar `fsspec`/`gcsfs` o descargar
      con `gcloud storage cp` en un wrapper de entrypoint.
- [ ] Wire de logs a Cloud Logging con structured logging.
- [ ] (Opcional) Cloud Build trigger desde GitHub push a `main`.
