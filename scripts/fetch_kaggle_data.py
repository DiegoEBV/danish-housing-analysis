"""
scripts/fetch_kaggle_data.py — Descarga el dataset de Kaggle.

Dataset: martinfrederiksen/danish-residential-housing-prices-1992-2024
Output: data/raw/DKHousingPrices.parquet (preferido) + CSV alternos.

Prerequisito:
  1. Ir a https://www.kaggle.com/settings/account
  2. "Create New API Token" -> descarga kaggle.json
  3. mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/
     chmod 600 ~/.kaggle/kaggle.json

Uso:
  uv run python scripts/fetch_kaggle_data.py
  uv run python scripts/fetch_kaggle_data.py --output-dir data/raw/
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATASET = "martinfrederiksen/danish-residential-housing-prices-1992-2024"


def check_credentials() -> None:
    kj = Path.home() / ".kaggle" / "kaggle.json"
    if not kj.exists():
        logger.error(
            f"No se encontro {kj}.\n"
            "Sigue: https://www.kaggle.com/settings/account -> Create New API Token\n"
            "Luego: mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json"
        )
        sys.exit(1)
    perms = oct(kj.stat().st_mode)[-3:]
    if perms != "600":
        logger.warning(f"~/.kaggle/kaggle.json tiene permisos {perms}; recomendado 600. Aplicando chmod.")
        os.chmod(kj, 0o600)


def fetch(output_dir: Path, force: bool) -> Path:
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Descargando dataset {DATASET} a {output_dir} ...")
    api.dataset_download_files(DATASET, path=str(output_dir), unzip=True, force=force)

    # Identificar el parquet (nombre canonico)
    parquets = list(output_dir.glob("*.parquet"))
    csvs = list(output_dir.glob("*.csv"))
    logger.info(f"  {len(parquets)} parquet(s), {len(csvs)} csv(s) descargados")

    target = output_dir / "DKHousingPrices.parquet"
    if not target.exists():
        # Buscar cualquier parquet con nombre parecido y renombrar
        for p in parquets:
            if "housing" in p.name.lower() or "DKHousing" in p.name:
                logger.info(f"  Renombrando {p.name} -> DKHousingPrices.parquet")
                p.rename(target)
                break

    if not target.exists() and parquets:
        # Si no encontramos uno con nombre obvio, tomamos el primero
        logger.warning(f"  No hay parquet con nombre canonico; renombrando {parquets[0].name} -> DKHousingPrices.parquet")
        parquets[0].rename(target)

    return target


def main() -> None:
    p = argparse.ArgumentParser(description=f"Descarga {DATASET} desde Kaggle")
    p.add_argument("--config", default="configs/analysis.yaml")
    p.add_argument("--output-dir", default=None, help="Override de paths.raw_parquet directory")
    p.add_argument("--force", action="store_true", help="Re-descargar aunque exista")
    args = p.parse_args()

    check_credentials()

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        cfg = yaml.safe_load(open(args.config))
        out_dir = Path(cfg["paths"]["raw_parquet"]).parent

    target = fetch(out_dir, args.force)

    if target.exists():
        import pandas as pd
        df = pd.read_parquet(target)
        logger.info(f"\nParquet listo: {target}")
        logger.info(f"  {len(df):,} filas x {df.shape[1]} columnas")
        logger.info(f"  Tamano: {target.stat().st_size / 1e6:.1f} MB")
        logger.info(f"  Rango fechas: {pd.to_datetime(df['date']).min().date()} -> {pd.to_datetime(df['date']).max().date()}")
    else:
        logger.error(f"\nNo se encontro parquet en {out_dir}. Listado de archivos:")
        for f in out_dir.iterdir():
            logger.error(f"  {f.name} ({f.stat().st_size / 1e6:.1f} MB)")
        sys.exit(1)


if __name__ == "__main__":
    main()
