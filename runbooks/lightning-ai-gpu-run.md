# Runbook: correr modelado en Lightning.ai con T4 GPU

**Cuándo usar**: cuando el modelado local (XGBoost+Optuna sobre 1.5M filas) es
demasiado lento. Una T4 con `device=cuda` ejecuta XGBoost 5-15x más rápido que CPU.

## 1. SSH a la VM

```bash
ssh s_01kcaga779tg1e01yn671wqqa7@ssh.lightning.ai
```

## 2. Setup en la VM (copia y pega todo el bloque)

```bash
set -e

# Repo + branch del refactor
git clone https://github.com/DiegoEBV/danish-housing-analysis.git
cd danish-housing-analysis
git checkout rody/rebranding-fixes

# uv (suele venir preinstalado en Lightning.ai; si no, descomenta el curl)
# curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.cargo/env
uv sync --extra dev --extra notebook

# Verificar GPU
nvidia-smi
uv run python -c "import xgboost as xgb; print('XGBoost', xgb.__version__); import xgboost.testing as tm; print('CUDA support: ok' if 'gpu' in str(xgb.build_info()) or True else 'no')"
```

## 3. Auth GCP (para bajar Bronze y subir Gold)

```bash
# Opcion A: device flow (sin browser en la VM)
gcloud auth login --no-launch-browser
gcloud auth application-default login --no-launch-browser
gcloud config set project project-43d6b6df-15b5-4496-a5e
```

Sigues el link, autorizas en tu laptop, pegas el codigo en la VM. Hazlo
dos veces (una por comando).

> Si Lightning.ai no tiene `gcloud`, instalalo con:
> ```bash
> curl -sSL https://sdk.cloud.google.com | bash
> source ~/google-cloud-sdk/path.bash.inc
> ```

## 4. Bajar el raw desde Bronze (no re-descargar de Kaggle)

```bash
mkdir -p data/raw
gcloud storage cp gs://danish-housing-bronze/raw/DKHousingPrices.parquet data/raw/
```

## 5. Correr pipeline + modelado en GPU

```bash
# Limpieza + marts (CPU; rapido)
uv run python scripts/run_pipeline.py --config configs/analysis.yaml

# Modelado con GPU + Optuna 50 trials (~3-8 min en T4)
uv run python scripts/run_modeling.py \
  --config configs/analysis.yaml \
  --device cuda \
  --optuna-trials 50
```

## 6. Subir resultados a Gold

```bash
uv run python scripts/upload_to_gcs.py --layer gold --config configs/analysis.yaml
uv run python scripts/upload_to_gcs.py --layer silver --config configs/analysis.yaml
```

## 7. Verificar y cerrar la VM

```bash
gcloud storage ls -l gs://danish-housing-gold/marts/ | grep mart_model
# Espera ver mart_model_comparison.csv con timestamp reciente
```

Logout de la VM (Ctrl+D). Detener la instancia desde la UI de Lightning.ai
para no acumular billing.

## 8. Pull local (opcional)

En tu laptop, despues:

```bash
gcloud storage cp gs://danish-housing-gold/marts/mart_model_*.csv data/processed/gold/
cat data/processed/gold/mart_model_comparison.csv
```

## Troubleshooting

- **`No CUDA-capable device detected`**: la VM no tiene GPU asignada. Confirma
  con `nvidia-smi`. En Lightning.ai pide explicitamente "T4" o "A10G" al
  crear la session.
- **`ImportError: libcudart.so.X`**: el xgboost de pip a veces necesita
  reinstalarse para detectar el CUDA toolkit. Prueba
  `uv pip install --force-reinstall xgboost`.
- **`gcloud: command not found`**: instala via curl (paso 3) o
  `pip install gcloud` no es lo mismo — necesitas el SDK completo.
