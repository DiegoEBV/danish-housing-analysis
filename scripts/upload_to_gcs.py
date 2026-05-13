"""
scripts/upload_to_gcs.py

Sube datos a Google Cloud Storage siguiendo la arquitectura Medallion:
  Bronze → datos crudos tal como llegan de Kaggle
  Silver → datos limpios con flags (output de TB2)
  Gold   → marts analíticos listos para Tableau (output de TB3)

Prerequisitos:
  pip install google-cloud-storage
  gcloud auth application-default login
  # O setear: export GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json

Uso:
  python scripts/upload_to_gcs.py --layer bronze --config configs/analysis.yaml
  python scripts/upload_to_gcs.py --layer silver --config configs/analysis.yaml
  python scripts/upload_to_gcs.py --layer gold   --config configs/analysis.yaml
  python scripts/upload_to_gcs.py --layer all    --config configs/analysis.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Configuración GCP ─────────────────────────────────────────────────────────
GCP_PROJECT  = "danish-housing-upc"       # Cambiar por tu project ID
BUCKET_BRONZE = "danish-housing-bronze"   # gs://danish-housing-bronze
BUCKET_SILVER = "danish-housing-silver"   # gs://danish-housing-silver
BUCKET_GOLD   = "danish-housing-gold"     # gs://danish-housing-gold


def get_gcs_client():
    try:
        from google.cloud import storage
        return storage.Client(project=GCP_PROJECT)
    except ImportError:
        logger.error("google-cloud-storage no instalado. Ejecuta: pip install google-cloud-storage")
        sys.exit(1)


def upload_file(client, bucket_name: str, local_path: Path, gcs_path: str) -> None:
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(str(local_path))
    logger.info(f"✅ Subido: gs://{bucket_name}/{gcs_path}")


def upload_bronze(client, cfg: dict) -> None:
    """
    BRONZE: Datos crudos de Kaggle sin modificar.
    Estructura en GCS: gs://danish-housing-bronze/raw/
    """
    logger.info("── BRONZE LAYER ──────────────────────────────────")
    raw_path = Path(cfg["paths"]["raw_data"])

    if not raw_path.exists():
        logger.warning(f"No encontrado: {raw_path}. Salta Bronze.")
        return

    upload_file(client, BUCKET_BRONZE, raw_path, f"raw/{raw_path.name}")
    logger.info("Bronze: datos crudos subidos (append-only, sin modificar)")


def upload_silver(client, cfg: dict) -> None:
    """
    SILVER: Datos limpios con flags de calidad (output de TB2).
    Estructura en GCS: gs://danish-housing-silver/processed/
    """
    logger.info("── SILVER LAYER ──────────────────────────────────")
    processed_dir = Path(cfg["paths"]["processed_dir"])

    silver_files = [
        processed_dir / "danish_housing_clean.parquet",
        processed_dir / "bitacora_limpieza.csv",
    ]

    for f in silver_files:
        if f.exists():
            upload_file(client, BUCKET_SILVER, f, f"processed/{f.name}")
        else:
            logger.warning(f"No encontrado: {f}")

    logger.info("Silver: datos validados y limpios subidos")


def upload_gold(client, cfg: dict) -> None:
    """
    GOLD: Marts analíticos para Tableau (output de TB3).
    Estructura en GCS: gs://danish-housing-gold/marts/
    """
    logger.info("── GOLD LAYER ────────────────────────────────────")
    gold_dir = Path(cfg["paths"]["processed_dir"]) / "gold"

    if not gold_dir.exists():
        logger.warning(f"Carpeta gold no encontrada: {gold_dir}")
        logger.warning("Ejecuta primero el notebook TB3 para generar los marts.")
        return

    for f in gold_dir.glob("*.csv"):
        upload_file(client, BUCKET_GOLD, f, f"marts/{f.name}")

    for f in gold_dir.glob("*.parquet"):
        upload_file(client, BUCKET_GOLD, f, f"marts/{f.name}")

    logger.info("Gold: marts para Tableau subidos")


def parse_args():
    parser = argparse.ArgumentParser(description="Upload datos a GCS Medallion")
    parser.add_argument("--layer", choices=["bronze", "silver", "gold", "all"], required=True)
    parser.add_argument("--config", default="configs/analysis.yaml")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    client = get_gcs_client()
    logger.info(f"Conectado a GCP project: {GCP_PROJECT}")

    if args.layer in ("bronze", "all"):
        upload_bronze(client, cfg)
    if args.layer in ("silver", "all"):
        upload_silver(client, cfg)
    if args.layer in ("gold", "all"):
        upload_gold(client, cfg)

    logger.info("✅ Upload completado")
    logger.info(f"  Bronze: gs://{BUCKET_BRONZE}/raw/")
    logger.info(f"  Silver: gs://{BUCKET_SILVER}/processed/")
    logger.info(f"  Gold:   gs://{BUCKET_GOLD}/marts/")


if __name__ == "__main__":
    main()
