"""
scripts/run_cleaning.py

Pipeline de limpieza de datos (reglas P1–P8 del TB2).

Uso:
    python scripts/run_cleaning.py --config configs/analysis.yaml
    python scripts/run_cleaning.py --config configs/analysis.yaml --sample 10000
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# Añadir src al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from danish_housing.cleaning import run_cleaning_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpieza del dataset danés")
    parser.add_argument("--config", default="configs/analysis.yaml")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Limitar a N filas para pruebas",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Cargar configuración
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    raw_path = Path(cfg["paths"]["raw_data"])
    processed_dir = Path(cfg["paths"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Cargar datos
    logger.info(f"Cargando datos desde {raw_path}")
    if not raw_path.exists():
        logger.error(
            f"No se encontró el archivo: {raw_path}\n"
            "Descarga el dataset desde Kaggle y colócalo en data/raw/"
        )
        sys.exit(1)

    df_raw = pd.read_csv(raw_path, nrows=args.sample)
    logger.info(f"Datos cargados: {df_raw.shape[0]:,} filas × {df_raw.shape[1]} columnas")

    # Ejecutar limpieza
    cleaning_cfg = cfg.get("cleaning", {})
    df_clean, bitacora = run_cleaning_pipeline(df_raw, cleaning_cfg)

    # Guardar resultados
    output_path = processed_dir / "danish_housing_clean.parquet"
    df_clean.to_parquet(output_path, index=False)
    logger.info(f"Dataset limpio guardado en {output_path}")

    bitacora_path = processed_dir / "bitacora_limpieza.csv"
    bitacora.to_csv(bitacora_path, index=False)
    logger.info(f"Bitácora guardada en {bitacora_path}")

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE LIMPIEZA")
    print("=" * 60)
    print(bitacora.to_string(index=False))
    print("=" * 60)
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
