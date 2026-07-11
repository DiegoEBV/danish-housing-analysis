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
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
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

def _cluster_stability(X: np.ndarray, k: int, rs: int, n_boot: int = 12, frac: float = 0.8) -> float:
    """Estabilidad del particionado: ARI medio entre el fit base y n_boot subsamples."""
    rng = np.random.default_rng(rs)
    base = KMeans(n_clusters=k, random_state=rs, n_init=10).fit(X)
    aris = []
    for _ in range(n_boot):
        idx = rng.choice(len(X), int(frac * len(X)), replace=False)
        lb = KMeans(n_clusters=k, random_state=int(rng.integers(1_000_000)), n_init=10).fit_predict(X[idx])
        aris.append(adjusted_rand_score(base.labels_[idx], lb))
    return float(np.mean(aris))


def _gap_statistic(X: np.ndarray, k: int, rs: int, n_ref: int = 15) -> float:
    """Gap statistic (Tibshirani): log(WCSS_ref) - log(WCSS_datos) sobre refs uniformes."""
    rng = np.random.default_rng(rs + k)
    wk = KMeans(n_clusters=k, random_state=rs, n_init=10).fit(X).inertia_
    mins, maxs = X.min(0), X.max(0)
    logs = [
        np.log(KMeans(n_clusters=k, random_state=rs, n_init=10).fit(rng.uniform(mins, maxs, size=X.shape)).inertia_)
        for _ in range(n_ref)
    ]
    return float(np.mean(logs) - np.log(wk))


def _eta2(v: np.ndarray, labels: np.ndarray) -> float:
    """Varianza de la variable `v` explicada por el clustering (eta^2 = SS_between / SS_total)."""
    grand = v.mean()
    sst = ((v - grand) ** 2).sum()
    if sst == 0:
        return 0.0
    ssb = sum((labels == c).sum() * (v[labels == c].mean() - grand) ** 2 for c in np.unique(labels))
    return float(ssb / sst)


def evaluate_k(X: np.ndarray, feats: pd.DataFrame, k_range: list[int], rs: int) -> pd.DataFrame:
    """
    Consenso AMPLIO de validez de cluster (7 criterios) + informatividad de negocio.

    Criterios de calidad: silueta / Calinski-Harabasz (alto mejor), Davies-Bouldin /
    GMM-BIC (bajo mejor), estabilidad ARI y gap statistic. Ademas, para justificar el
    k operativo, se mide cuanta varianza de RETORNO (cagr, growth) y RIESGO (volatilidad,
    drawdown) explica el clustering (eta^2): un k con peor silueta puede ser mas util
    para negocio si separa mejor los ejes riesgo-retorno.
    """
    ret_cols = ["cagr_real", "growth_recent"]
    rsk_cols = ["volatility", "max_drawdown"]
    rows = []
    for k in k_range:
        lab = KMeans(n_clusters=k, random_state=rs, n_init=10).fit(X).labels_
        rows.append({
            "k": k,
            "silhouette": silhouette_score(X, lab),
            "calinski_harabasz": calinski_harabasz_score(X, lab),
            "davies_bouldin": davies_bouldin_score(X, lab),
            "stability_ari": _cluster_stability(X, k, rs),
            "gap": _gap_statistic(X, k, rs),
            "inertia": KMeans(n_clusters=k, random_state=rs, n_init=10).fit(X).inertia_,
            "gmm_bic": GaussianMixture(n_components=k, random_state=rs, n_init=2).fit(X).bic(X),
            "eta2_return": float(np.mean([_eta2(feats[c].to_numpy(), lab) for c in ret_cols])),
            "eta2_risk": float(np.mean([_eta2(feats[c].to_numpy(), lab) for c in rsk_cols])),
        })
        logger.info("  k=%d -> sil=%.3f CH=%.0f DB=%.3f estab=%.3f gap=%.3f eta2_risk=%.3f",
                    k, rows[-1]["silhouette"], rows[-1]["calinski_harabasz"],
                    rows[-1]["davies_bouldin"], rows[-1]["stability_ari"], rows[-1]["gap"],
                    rows[-1]["eta2_risk"])
    return pd.DataFrame(rows)


def choose_k_scientific(val_df: pd.DataFrame) -> int:
    """
    k 'cientifico' por consenso de los criterios de CALIDAD de cluster (separacion +
    estabilidad): silueta, Calinski-Harabasz y estabilidad ARI. Es la particion robusta.
    Los criterios que premian k mas alto (DB/BIC/gap) solo reflejan que un continuo se
    puede rebanar mas fino, sin robustez, por eso NO entran al voto cientifico.
    """
    votes = [
        int(val_df.loc[val_df["silhouette"].idxmax(), "k"]),
        int(val_df.loc[val_df["calinski_harabasz"].idxmax(), "k"]),
        int(val_df.loc[val_df["stability_ari"].idxmax(), "k"]),
    ]
    return int(pd.Series(votes).mode().iloc[0])


def _label_arquetipos_4(p: pd.DataFrame) -> dict:
    """
    Mapea los 4 clusters a los arquetipos de inversion (perfiles de negocio del dashboard).
    Asignacion DETERMINISTA por posicion del centroide (los labels de KMeans son arbitrarios):
      1. Premium estable/liquido  = mayor nivel de precio
      2. Volatil / alto riesgo    = mayor volatilidad entre el resto
      3. Value con crecimiento    = mayor CAGR entre el resto
      4. Value estable/liquido    = el cluster restante
    """
    labels: dict[int, str] = {}
    restantes = set(p["cluster"].astype(int))

    def _asignar(col: str, nombre: str) -> None:
        sub = p[p["cluster"].astype(int).isin(restantes)]
        c = int(sub.loc[sub[col].idxmax(), "cluster"])
        labels[c] = nombre
        restantes.discard(c)

    _asignar("price_level", "Premium estable/liquido")
    _asignar("volatility", "Volatil / alto riesgo")
    _asignar("cagr_real", "Value con crecimiento")
    labels[int(next(iter(restantes)))] = "Value estable/liquido"
    return labels


def label_clusters(profiles: pd.DataFrame) -> dict:
    """
    Etiqueta cada cluster con un nombre interpretable a partir de su centroide.
    Con k=4 usa los arquetipos de negocio; con otros k, cae a terciles relativos.
    """
    p = profiles.copy()
    if len(p) == 4:
        return _label_arquetipos_4(p)
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

    # 5. Validacion amplia (7 criterios + eta^2 de negocio) y seleccion de k.
    #    Se reportan DOS k: el 'cientifico' (consenso de calidad de cluster) y el
    #    'operativo' (perfiles de negocio del dashboard). Ver mart_segmentation_validation.
    logger.info("Consenso amplio de validez de cluster:")
    val_df = evaluate_k(X, feats, scfg["kmeans_k_range"], rs)
    k_sci = choose_k_scientific(val_df)
    if scfg.get("kmeans_k_override"):
        k = int(scfg["kmeans_k_override"])
    else:
        k = int(scfg.get("kmeans_k_operativo") or k_sci)
    er = val_df.set_index("k")["eta2_risk"]
    ret = val_df.set_index("k")["eta2_return"]
    logger.info("k CIENTIFICO (consenso silueta+CH+estabilidad) = %d", k_sci)
    logger.info("k OPERATIVO (perfiles de negocio) = %d", k)
    logger.info("Justificacion eta^2: riesgo k=%d->%.3f vs k=%d->%.3f | retorno k=%d->%.3f vs k=%d->%.3f",
                k_sci, er.get(k_sci, float("nan")), k, er.get(k, float("nan")),
                k_sci, ret.get(k_sci, float("nan")), k, ret.get(k, float("nan")))
    sil_scores = dict(zip(val_df["k"], val_df["silhouette"], strict=True))

    km = KMeans(n_clusters=k, random_state=rs, n_init=10)
    feats["cluster"] = km.fit_predict(X)
    feats["pca1"], feats["pca2"] = pcs[:, 0], pcs[:, 1]

    # 6. t-SNE (embedding no lineal SOLO para exploracion visual, NO valida clusters).
    #    Hiperparametros fijados y documentados en config para reproducibilidad.
    perp = min(scfg["tsne_perplexity"], (len(feats) - 1) // 3)
    tsne = TSNE(
        n_components=2,
        perplexity=perp,
        learning_rate=scfg.get("tsne_learning_rate", "auto"),
        max_iter=int(scfg.get("tsne_max_iter", 1000)),
        init="pca",
        random_state=rs,
    )
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
    out_val = marts_dir / "mart_segmentation_validation.csv"
    feats[cols_seg].round(4).to_csv(out_seg, index=False)
    profiles.round(4).to_csv(out_prof, index=False)
    val_df.assign(k_cientifico=k_sci, k_operativo=k).round(4).to_csv(out_val, index=False)
    logger.info("Exportado %s (%d zips)", out_seg.name, len(feats))
    logger.info("Exportado %s (%d clusters)", out_prof.name, len(profiles))
    logger.info("Exportado %s (validacion k=%s)", out_val.name, list(val_df["k"]))

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
