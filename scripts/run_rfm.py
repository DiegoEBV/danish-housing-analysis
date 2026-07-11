"""
scripts/run_rfm.py

RFM de ATRACTIVO DE MERCADO por codigo postal (Entrega 6 / TF, complemento analitico).

IMPORTANTE — encuadre honesto: el RFM clasico segmenta CLIENTES con compras repetidas.
Este dataset son transacciones de vivienda sin ID de comprador, asi que NO es RFM de
clientes. Es un reencuadre por MERCADO (zip_code):

    R (Recency)   = momentum reciente del mercado   (crecimiento ultimos anios)
    F (Frequency) = liquidez                         (volumen de transacciones)
    M (Monetary)  = nivel de precio real/m2

Cada zip recibe un score 1-5 por dimension (quintiles) y un segmento de negocio
interpretable. Complementa (no reemplaza) la segmentacion riesgo-retorno de
run_segmentation.py: aporta el eje temporal (¿mercado caliente o frio AHORA?) y un
scoring legible. Reusa build_features de run_segmentation para operar sobre los mismos
zips (mismos filtros de cobertura).

Salidas:
    - data/marts/mart_rfm_segments.csv : una fila por zip con R/F/M, score y segmento
    - docs/refs/rfm_segments.png        : figura (tamaños de segmento + scatter precio×momentum)

Uso:
    uv run python scripts/run_rfm.py --config configs/analysis.yaml
    uv run python scripts/run_rfm.py --config configs/analysis.yaml --no-plot

Parametros en configs/analysis.yaml -> rfm (y filtros de cobertura en -> segmentation).
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from run_segmentation import build_features  # mismo universo de zips (filtros de cobertura)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _quintile(series: pd.Series, n: int) -> pd.Series:
    """Score 1..n por quintiles (rank para romper empates de forma estable)."""
    return pd.qcut(series.rank(method="first"), n, labels=list(range(1, n + 1))).astype(int)


def label_rfm_segment(r: int, f: int, m: int) -> str:
    """Segmento de negocio interpretable a partir de los scores R/F/M (quintiles 1-5)."""
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions (premium caliente-liquido)"
    if m >= 4 and r <= 2:
        return "Premium frio (caro, sin momentum)"
    if f >= 4 and m <= 2:
        return "Value liquido (barato, accesible)"
    if r >= 4 and m <= 3:
        return "Emergente (momentum, ticket medio-bajo)"
    if r <= 2 and f <= 2:
        return "Periferico dormido (iliquido, frio)"
    return "Intermedio"


def compute_rfm(feats: pd.DataFrame, rcfg: dict) -> pd.DataFrame:
    n = rcfg["n_quantiles"]
    df = feats.copy()
    df["R"] = _quintile(df[rcfg["recency_feature"]], n)
    df["F"] = _quintile(df[rcfg["frequency_feature"]], n)
    df["M"] = _quintile(df[rcfg["monetary_feature"]], n)
    df["RFM_score"] = df["R"] + df["F"] + df["M"]
    df["RFM_code"] = df["R"].astype(str) + df["F"].astype(str) + df["M"].astype(str)
    df["rfm_segmento"] = [label_rfm_segment(r, f, m) for r, f, m in zip(df["R"], df["F"], df["M"], strict=True)]
    return df


def _cramers_v(ct: pd.DataFrame) -> float:
    """Asociacion entre dos categoricas (0=independiente, 1=redundante)."""
    from scipy.stats import chi2_contingency

    chi2, _, _, _ = chi2_contingency(ct)
    n = ct.values.sum()
    return float(np.sqrt(chi2 / (n * (min(ct.shape) - 1))))


def run(config_path: str, marts_dir: str | Path | None = None, make_plot: bool = True) -> None:
    cfg_all = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    scfg = cfg_all["segmentation"]
    rcfg = cfg_all["rfm"]
    marts_dir = Path(marts_dir) if marts_dir else Path("data/marts")

    src = marts_dir / f"{scfg['input_mart']}.csv"
    df_map = pd.read_csv(src, dtype={"zip_code": str})
    feats = build_features(df_map, scfg)
    logger.info("RFM sobre %d zips (mismo universo que la segmentacion)", len(feats))

    rfm = compute_rfm(feats, rcfg)

    out_cols = [
        "zip_code", "city", "region", "n_years",
        "growth_recent", "liquidity_log", "price_level", "max_drawdown",
        "R", "F", "M", "RFM_score", "RFM_code", "rfm_segmento",
    ]
    out = marts_dir / "mart_rfm_segments.csv"
    rfm[out_cols].round(4).to_csv(out, index=False)
    logger.info("Exportado %s (%d zips, %d segmentos)", out.name, len(rfm), rfm["rfm_segmento"].nunique())

    # Complementariedad vs la segmentacion riesgo-retorno (si existe el mart)
    seg_path = marts_dir / "mart_zip_segments.csv"
    if seg_path.exists():
        seg = pd.read_csv(seg_path, dtype={"zip_code": str})[["zip_code", "cluster_label"]]
        merged = rfm.merge(seg, on="zip_code", how="inner")
        ct = pd.crosstab(merged["rfm_segmento"], merged["cluster_label"])
        cv = _cramers_v(ct)
        logger.info("Cramer's V (RFM <-> arquetipos KMeans) = %.3f (0=independiente, 1=redundante)", cv)

    # Resumen legible
    print("\n=== PERFIL POR SEGMENTO RFM (medias reales) ===")
    prof = (
        rfm.groupby("rfm_segmento")
        .agg(n=("zip_code", "count"), growth=("growth_recent", "mean"),
             liquidez=("liquidity_log", "mean"), precio=("price_level", "mean"),
             drawdown=("max_drawdown", "mean"),
             region=("region", lambda s: s.value_counts().idxmax()))
        .sort_values("n", ascending=False)
    )
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(prof.round(3).to_string())

    if make_plot:
        _plot(rfm, Path("docs/refs") / "rfm_segments.png")


def _plot(rfm: pd.DataFrame, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_path.parent.mkdir(parents=True, exist_ok=True)
    segs = rfm["rfm_segmento"].value_counts()
    cmap = plt.get_cmap("tab10")
    seg_order = list(segs.index)
    color = {s: cmap(i) for i, s in enumerate(seg_order)}

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    axes[0].barh(segs.index[::-1], segs.values[::-1], color=[color[s] for s in segs.index[::-1]])
    axes[0].set_title("Tamaño de segmentos RFM (n zips)")
    axes[0].set_xlabel("zips")

    for s in seg_order:
        sub = rfm[rfm["rfm_segmento"] == s]
        axes[1].scatter(sub["growth_recent"], sub["price_level"], s=18, alpha=0.7,
                        color=color[s], label=s)
    axes[1].set_title("Zips por RFM — Monetary (precio) × Recency (momentum)")
    axes[1].set_xlabel("R: crecimiento reciente")
    axes[1].set_ylabel("M: precio real/m²")
    axes[1].legend(fontsize=7, loc="upper left")

    fig.suptitle("RFM de atractivo de mercado por zip (datos reales Gold)", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    logger.info("Figura guardada en %s", out_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="RFM de atractivo de mercado por zip")
    ap.add_argument("--config", default="configs/analysis.yaml")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--marts-dir", default=None)
    args = ap.parse_args()
    run(args.config, marts_dir=args.marts_dir, make_plot=not args.no_plot)


if __name__ == "__main__":
    main()
