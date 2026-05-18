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
import os
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_gcs_client(project_id: str):
    try:
        from google.cloud import storage
        return storage.Client(project=project_id)
    except ImportError:
        logger.error("google-cloud-storage no instalado. Ejecuta: pip install google-cloud-storage")
        sys.exit(1)


def upload_file(client, bucket_name: str, local_path: Path, gcs_path: str) -> None:
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(str(local_path))
    logger.info(f"✅ Subido: gs://{bucket_name}/{gcs_path}")


def upload_bronze(client, cfg: dict) -> None:
    """BRONZE: raw de Kaggle (CSV + Parquet) sin modificar."""
    logger.info("── BRONZE LAYER ──────────────────────────────────")
    bucket = cfg["gcp"]["buckets"]["bronze"]
    prefix = cfg["gcp"]["prefixes"]["bronze"]

    candidates = [
        Path(cfg["paths"].get("raw_csv", "")),
        Path(cfg["paths"].get("raw_parquet", "")),
    ]
    subido = False
    for p in candidates:
        if str(p) and p.exists():
            upload_file(client, bucket, p, f"{prefix}{p.name}")
            subido = True
        else:
            logger.warning(f"No encontrado: {p}. Salta.")
    if subido:
        logger.info("Bronze: raws subidos (append-only)")


def upload_silver(client, cfg: dict) -> None:
    """SILVER: dataset limpio + bitacora (output de TB2)."""
    logger.info("── SILVER LAYER ──────────────────────────────────")
    bucket = cfg["gcp"]["buckets"]["silver"]
    prefix = cfg["gcp"]["prefixes"]["silver"]

    silver_files = [
        Path(cfg["paths"]["silver_parquet"]),
        Path(cfg["paths"]["bitacora_csv"]),
    ]

    for f in silver_files:
        if f.exists():
            upload_file(client, bucket, f, f"{prefix}{f.name}")
        else:
            logger.warning(f"No encontrado: {f}")


def upload_gold(client, cfg: dict) -> None:
    """GOLD: marts analiticos para Tableau (output de TB3)."""
    logger.info("── GOLD LAYER ────────────────────────────────────")
    bucket = cfg["gcp"]["buckets"]["gold"]
    prefix = cfg["gcp"]["prefixes"]["gold"]

    # Buscar marts en gold_dir y marts_dir (segun donde haya corrido el pipeline)
    candidate_dirs = [Path(cfg["paths"]["gold_dir"]), Path(cfg["paths"]["marts_dir"])]
    found_any = False
    for d in candidate_dirs:
        if not d.exists():
            continue
        for f in list(d.glob("*.csv")) + list(d.glob("*.parquet")):
            upload_file(client, bucket, f, f"{prefix}{f.name}")
            found_any = True
    if not found_any:
        logger.warning(f"Sin marts en {candidate_dirs}. Ejecuta export_marts.py o run_pipeline.py primero.")


def parse_args():
    parser = argparse.ArgumentParser(description="Upload datos a GCS Medallion")
    parser.add_argument("--layer", choices=["bronze", "silver", "gold", "all"], required=True)
    parser.add_argument("--config", default="configs/analysis.yaml")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    project_id = os.environ.get("GCP_PROJECT") or cfg["gcp"]["project_id"]
    client = get_gcs_client(project_id)
    logger.info(f"Conectado a GCP project: {project_id}")

    if args.layer in ("bronze", "all"):
        upload_bronze(client, cfg)
    if args.layer in ("silver", "all"):
        upload_silver(client, cfg)
    if args.layer in ("gold", "all"):
        upload_gold(client, cfg)

    logger.info("✅ Upload completado")
    for layer in ("bronze", "silver", "gold"):
        b = cfg["gcp"]["buckets"][layer]
        p = cfg["gcp"]["prefixes"][layer]
        logger.info(f"  {layer.capitalize():<6}: gs://{b}/{p}")


if __name__ == "__main__":
    main()
