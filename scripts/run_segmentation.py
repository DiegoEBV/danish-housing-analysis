"""
scripts/run_segmentation.py

Segmentacion no supervisada del mercado residencial danes (Entrega 6 / TF).

Aplica reduccion de dimensionalidad (PCA + t-SNE) y clustering (KMeans) sobre un
espacio de features de perfil riesgo-retorno construido por codigo postal a partir
del mart Gold real `mart_transactions_map`. El objetivo es descubrir, de forma
data-driven (no por reglas), grupos de zonas con dinamica de precios homogenea y
conectarlos con las hipotesis H1-H3 y las vistas del dashboard.

Salidas (capa Gold, listas para Tableau / dashboard):
    - mart_zip_segments.csv    : una fila por zip con features, PCA, t-SNE y cluster
    - mart_segment_profiles.csv: perfil agregado (centroide interpretable) por cluster
    - segmentation_pca_tsne.png: figura diagnostica (varianza PCA, silueta, embeddings)

Uso:
    uv run python scripts/run_segmentation.py --config configs/analysis.yaml
    uv run python scripts/run_segmentation.py --config configs/analysis.yaml --no-plot

Todos los parametros viven en configs/analysis.yaml -> segmentation.
"""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Feature engineering por codigo postal ─────────────────────────────────────

def _cagr(series: pd.Series, smoothing: int) -> float:
    """CAGR robusto: promedia los `smoothing` extremos para atenuar ruido de muestra."""
    s = series.dropna()
    if len(s) < 2 * smoothing:
        return np.nan
    inicio = s.iloc[:smoothing].mean()
    fin = s.iloc[-smoothing:].mean()
    anios = s.index[-1] - s.index[0]
    if inicio <= 0 or anios <= 0:
        return np.nan
    return (fin / inicio) ** (1 / anios) - 1


def _max_drawdown(series: pd.Series) -> float:
    """Peor caida pico-valle (%) sobre la serie anual de precio real/m2."""
    s = series.dropna()
    if len(s) < 2:
        return np.nan
    cummax = s.cummax()
    dd = (s - cummax) / cummax
    return float(dd.min() * 100)


def build_features(df_map: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Construye la matriz de features por zip_code a partir de mart_transactions_map.

    Cada zip queda descrito por 6 variables interpretables de perfil riesgo-retorno:
    nivel de precio, crecimiento (CAGR), volatilidad, drawdown, liquidez y crecimiento
    reciente. Estas features son la entrada de PCA / KMeans / t-SNE.
    """
    min_years = cfg["min_years_coverage"]
    min_txn = cfg["min_avg_transactions"]
    smoothing = cfg["smoothing_years"]
    recent = cfg["recent_years"]

    df = df_map.sort_values(["zip_code", "year"]).copy()
    filas = []
    for zip_code, g in df.groupby("zip_code", sort=False):
        g = g.dropna(subset=["avg_sqm_price_real"])
        if g["year"].nunique() < min_years:
            continue
        if g["n_transactions"].mean() < min_txn:
            continue

        precios = g.set_index("year")["avg_sqm_price_real"]
        pct = precios.pct_change().dropna()
        recientes = precios.tail(recent)

        filas.append(
            {
                "zip_code": zip_code,
                "city": g["city"].iloc[-1],
                "region": g["region"].iloc[-1],
                "n_years": int(g["year"].nunique()),
                "price_level": float(recientes.median()),
                "cagr_real": _cagr(precios, smoothing),
                "volatility": float(pct.std()),
                "max_drawdown": _max_drawdown(precios),
                "liquidity_log": float(np.log1p(g["n_transactions"].mean())),
                "growth_recent": float(recientes.iloc[-1] / recientes.iloc[0] - 1)
                if len(recientes) >= 2 and recientes.iloc[0] > 0
                else np.nan,
            }
        )

    feats = pd.DataFrame(filas).dropna().reset_index(drop=True)
    logger.info(
        "Features construidas: %d zips (de %d) sobrevivieron los filtros de cobertura",
        len(feats),
        df["zip_code"].nunique(),
    )
    return feats


# ── PCA + seleccion de k + KMeans + t-SNE ─────────────────────────────────────

def choose_k(X: np.ndarray, k_range: list[int], k_override, random_state: int):
    """Elige k por coeficiente de silueta (o respeta k_override)."""
    if k_override:
        logger.info("k fijado manualmente = %d", k_override)
        return int(k_override), {}
    scores = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X)
        scores[k] = silhouette_score(X, labels)
        logger.info("  k=%d -> silueta=%.4f", k, scores[k])
    best = max(scores, key=scores.get)
    logger.info("k elegido por silueta = %d (silueta=%.4f)", best, scores[best])
    return best, scores


def label_clusters(profiles: pd.DataFrame) -> dict:
    """
    Etiqueta cada cluster con un nombre interpretable a partir de la posicion de su
    centroide en nivel de precio, crecimiento y volatilidad (terciles relativos).
    """
    p = profiles.copy()
    nivel = pd.qcut(p["price_level"].rank(method="first"), 3, labels=["bajo", "medio", "alto"])
    vol = pd.qcut(p["volatility"].rank(method="first"), 3, labels=["estable", "medio", "volatil"])
    crec = pd.qcut(p["cagr_real"].rank(method="first"), 3, labels=["plano", "medio", "dinamico"])
    labels = {}
    for i, row in p.iterrows():
        c = int(row["cluster"])
        labels[c] = f"Precio {nivel[i]} / {crec[i]} / {vol[i]}"
    return labels


def run(config_path: str, make_plot: bool = True, marts_dir: str | Path | None = None) -> None:
    cfg_all = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    scfg = cfg_all["segmentation"]
    # Dir de marts: por defecto los marts trackeados que alimentan el dashboard.
    # run_pipeline.py puede pasar su propio marts_dir para integrarlo en la FASE C.
    marts_dir = Path(marts_dir) if marts_dir else Path("data/marts")
    rs = scfg["random_state"]

    # 1. Carga del mart Gold real
    src = marts_dir / f"{scfg['input_mart']}.csv"
    df_map = pd.read_csv(src, dtype={"zip_code": str})
    logger.info("Cargado %s: %d filas", src.name, len(df_map))

    # 2. Feature engineering por zip
    feats = build_features(df_map, scfg)
    feature_cols = scfg["features"]

    # 3. Winsorizacion (recorte a [p_lo, p_hi]) + estandarizacion.
    # El recorte evita que un zip atipico (mercado erratico de baja liquidez) domine
    # la varianza y capture un cluster propio de tamano 1.
    wp = scfg.get("winsorize_pct", 0.0)
    Xraw = feats[feature_cols].copy()
    if wp and wp > 0:
        lo = Xraw.quantile(wp)
        hi = Xraw.quantile(1 - wp)
        Xraw = Xraw.clip(lower=lo, upper=hi, axis=1)
    scaler = StandardScaler()
    X = scaler.fit_transform(Xraw.to_numpy())

    # 4. PCA (varianza explicada + embedding 2D)
    pca = PCA(n_components=scfg["pca_components"], random_state=rs)
    pcs = pca.fit_transform(X)
    var = pca.explained_variance_ratio_
    logger.info(
        "PCA: %d comps explican %.1f%% de la varianza (%.1f%% + %.1f%%)",
        len(var), var.sum() * 100, var[0] * 100, var[1] * 100,
    )

    # 5. Seleccion de k + KMeans (clustering sobre features estandarizadas)
    k, sil_scores = choose_k(X, scfg["kmeans_k_range"], scfg["kmeans_k_override"], rs)
    km = KMeans(n_clusters=k, random_state=rs, n_init=10)
    feats["cluster"] = km.fit_predict(X)
    feats["pca1"], feats["pca2"] = pcs[:, 0], pcs[:, 1]

    # 6. t-SNE (embedding no lineal para visualizacion)
    perp = min(scfg["tsne_perplexity"], (len(feats) - 1) // 3)
    tsne = TSNE(n_components=2, perplexity=perp, random_state=rs, init="pca")
    emb = tsne.fit_transform(X)
    feats["tsne1"], feats["tsne2"] = emb[:, 0], emb[:, 1]

    # 7. Perfil (centroide interpretable) por cluster + etiquetas
    profiles = (
        feats.groupby("cluster")
        .agg(
            n_zips=("zip_code", "count"),
            **{c: (c, "mean") for c in feature_cols},
        )
        .reset_index()
    )
    labels = label_clusters(profiles)
    profiles["cluster_label"] = profiles["cluster"].map(labels)
    feats["cluster_label"] = feats["cluster"].map(labels)
    # region dominante por cluster (para conectar con H2)
    reg_dom = feats.groupby("cluster")["region"].agg(lambda s: s.value_counts().idxmax())
    profiles["region_dominante"] = profiles["cluster"].map(reg_dom)

    # 8. Export marts Gold
    out_seg = marts_dir / "mart_zip_segments.csv"
    out_prof = marts_dir / "mart_segment_profiles.csv"
    cols_seg = [
        "zip_code", "city", "region", "n_years",
        *feature_cols, "pca1", "pca2", "tsne1", "tsne2", "cluster", "cluster_label",
    ]
    feats[cols_seg].round(4).to_csv(out_seg, index=False)
    profiles.round(4).to_csv(out_prof, index=False)
    logger.info("Exportado %s (%d zips)", out_seg.name, len(feats))
    logger.info("Exportado %s (%d clusters)", out_prof.name, len(profiles))

    # 9. Figura diagnostica para el informe (docs/refs, trackeable en git)
    if make_plot:
        fig_dir = Path("docs/refs")
        fig_dir.mkdir(parents=True, exist_ok=True)
        _plot(feats, pca, sil_scores, k, fig_dir / "segmentation_pca_tsne.png")

    # Resumen legible en consola (para QA / informe)
    print("\n=== PERFIL DE SEGMENTOS (centroides) ===")
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(profiles[["cluster", "cluster_label", "n_zips", "region_dominante",
                        "price_level", "cagr_real", "volatility", "max_drawdown"]].to_string(index=False))


def _plot(feats, pca, sil_scores, k, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    clusters = sorted(feats["cluster"].unique())
    cmap = plt.get_cmap("tab10")

    # (a) varianza acumulada PCA (sobre las comps retenidas)
    var = pca.explained_variance_ratio_
    axes[0].bar(range(1, len(var) + 1), var * 100, color="#6366f1")
    axes[0].set_title(f"PCA - varianza explicada\n(total {var.sum()*100:.1f}%)")
    axes[0].set_xlabel("Componente principal")
    axes[0].set_ylabel("% varianza")

    # (b) PCA scatter coloreado por cluster
    for c in clusters:
        sub = feats[feats["cluster"] == c]
        axes[1].scatter(sub["pca1"], sub["pca2"], s=12, color=cmap(c), label=f"C{c}", alpha=0.7)
    axes[1].set_title("Proyeccion PCA (2D) por cluster")
    axes[1].set_xlabel("PC1")
    axes[1].set_ylabel("PC2")
    axes[1].legend(fontsize=8, markerscale=1.5)

    # (c) t-SNE scatter coloreado por cluster
    for c in clusters:
        sub = feats[feats["cluster"] == c]
        axes[2].scatter(sub["tsne1"], sub["tsne2"], s=12, color=cmap(c), label=f"C{c}", alpha=0.7)
    axes[2].set_title(f"Embedding t-SNE (2D) - k={k}")
    axes[2].set_xlabel("t-SNE 1")
    axes[2].set_ylabel("t-SNE 2")

    fig.suptitle("Segmentacion no supervisada de zonas (PCA + KMeans + t-SNE) - datos reales Gold", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    logger.info("Figura guardada en %s", out_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Segmentacion no supervisada (PCA + KMeans + t-SNE)")
    ap.add_argument("--config", default="configs/analysis.yaml", help="Ruta al YAML de configuracion")
    ap.add_argument("--no-plot", action="store_true", help="No generar la figura diagnostica")
    ap.add_argument("--marts-dir", default=None, help="Dir de marts (default: data/marts)")
    args = ap.parse_args()
    run(args.config, make_plot=not args.no_plot, marts_dir=args.marts_dir)


if __name__ == "__main__":
    main()
