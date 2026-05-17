"""
scripts/run_modeling.py — Fase 4 del plan TB3.

Entrena 4 modelos (Lineal, Ridge, RandomForest, XGBoost+Optuna) sobre el
Silver layer usando src/danish_housing/features.py. Reporta metricas SIEMPRE
en escala nominal (purchase_price en DKK), nunca en log.

Genera 3 marts en el Gold layer:
- mart_model_comparison.csv: R²/MAE/MAPE/RMSE por modelo (train y test)
- mart_predictions.csv: y_true, y_pred, residual por fila del test set
- mart_feature_importance.csv: importancia por feature, top-K por modelo

Uso:
    uv run python scripts/run_modeling.py --config configs/analysis.yaml
    uv run python scripts/run_modeling.py --config configs/analysis.yaml --no-optuna
    uv run python scripts/run_modeling.py --config configs/analysis.yaml --optuna-trials 20
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from danish_housing.features import build_feature_matrix, temporal_train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1.0))) * 100)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape_pct": mape,
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def train_linear(X_train, y_train_log, X_test):
    from sklearn.linear_model import LinearRegression
    m = LinearRegression()
    m.fit(X_train, y_train_log)
    return m, np.expm1(m.predict(X_train)), np.expm1(m.predict(X_test))


def train_ridge(X_train, y_train_log, X_test):
    from sklearn.linear_model import Ridge
    m = Ridge(alpha=1.0, random_state=42)
    m.fit(X_train, y_train_log)
    return m, np.expm1(m.predict(X_train)), np.expm1(m.predict(X_test))


def train_rf(X_train, y_train_log, X_test):
    from sklearn.ensemble import RandomForestRegressor
    m = RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
    m.fit(X_train, y_train_log)
    return m, np.expm1(m.predict(X_train)), np.expm1(m.predict(X_test))


def train_xgb(X_train, y_train_log, X_test, optuna_trials: int, device: str = "cpu"):
    from xgboost import XGBRegressor

    # Para GPU XGBoost 2.0+ usa device='cuda', tree_method='hist' (no 'gpu_hist' deprecado)
    base_kwargs = {"n_jobs": -1, "random_state": 42, "verbosity": 0, "tree_method": "hist"}
    if device == "cuda":
        base_kwargs["device"] = "cuda"

    if optuna_trials > 0:
        import optuna
        from sklearn.model_selection import KFold

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 200, 800, step=100),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 2.0),
                **base_kwargs,
            }
            # CV simple sobre train (3 folds para velocidad)
            kf = KFold(n_splits=3, shuffle=True, random_state=42)
            scores = []
            for tr, va in kf.split(X_train):
                model = XGBRegressor(**params)
                model.fit(X_train.iloc[tr], y_train_log.iloc[tr])
                p = model.predict(X_train.iloc[va])
                # Optimizar sobre RMSE en escala log (estable)
                scores.append(float(np.sqrt(np.mean((p - y_train_log.iloc[va]) ** 2))))
            return float(np.mean(scores))

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=optuna_trials, show_progress_bar=False)
        best_params = study.best_params
        logger.info(f"XGB Optuna best params (device={device}): {best_params}")
    else:
        best_params = {
            "n_estimators": 400, "max_depth": 6, "learning_rate": 0.05,
            "subsample": 0.85, "colsample_bytree": 0.85,
        }

    m = XGBRegressor(**best_params, **base_kwargs)
    m.fit(X_train, y_train_log)
    return m, np.expm1(m.predict(X_train)), np.expm1(m.predict(X_test))


def feature_importance(model, feature_names: list[str]) -> pd.DataFrame:
    """Importancia normalizada por modelo. Sklearn linear → coef abs; tree → feature_importances_."""
    if hasattr(model, "feature_importances_"):
        imp = pd.Series(model.feature_importances_, index=feature_names)
    elif hasattr(model, "coef_"):
        imp = pd.Series(np.abs(model.coef_), index=feature_names)
    else:
        return pd.DataFrame()
    imp = imp / imp.sum() if imp.sum() > 0 else imp
    return imp.sort_values(ascending=False).to_frame("importance").reset_index().rename(columns={"index": "feature"})


def parse_args():
    p = argparse.ArgumentParser(description="Fase 4: entrenamiento M1-M4 + reporte de metricas")
    p.add_argument("--config", default="configs/analysis.yaml")
    p.add_argument("--no-optuna", action="store_true", help="Skip Optuna; usa XGB defaults")
    p.add_argument("--optuna-trials", type=int, default=30, help="Numero de trials Optuna para M4")
    p.add_argument("--top-k-importance", type=int, default=20)
    p.add_argument("--train-end-year", type=int, default=2017)
    p.add_argument("--test-start-year", type=int, default=2018)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu",
                   help="Device para XGBoost (cuda requiere GPU NVIDIA + xgboost compilado con CUDA)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = yaml.safe_load(open(args.config))

    silver = Path(cfg["paths"]["silver_parquet"])
    gold = Path(cfg["paths"]["gold_dir"])
    marts = Path(cfg["paths"]["marts_dir"])
    gold.mkdir(parents=True, exist_ok=True)
    marts.mkdir(parents=True, exist_ok=True)

    if not silver.exists():
        logger.error(f"Silver no encontrado: {silver}. Corre run_cleaning.py primero.")
        sys.exit(1)

    logger.info(f"Cargando Silver desde {silver}")
    df = pd.read_parquet(silver)
    logger.info(f"  {len(df):,} filas")

    # Construir features
    df_feat, feature_names, audit = build_feature_matrix(
        df, target_col="purchase_price",
        window_years=12, min_obs_per_window=30,
        include_causal_derived=False, use_log_target=True,
    )
    logger.info(f"Feature matrix: {audit['n_rows']:,} filas x {audit['n_features']} features")
    logger.info(f"Anti-leak guard: {'PASS' if audit['leakage_check_passed'] else 'FAIL'}")

    # Split temporal
    train, test = temporal_train_test_split(
        df_feat, train_end=args.train_end_year, test_start=args.test_start_year,
    )
    if len(train) < 100 or len(test) < 100:
        logger.warning(f"Splits pequenos: train={len(train)}, test={len(test)}. Resultados poco confiables.")

    # Imputar NaN con mediana del TRAIN (no del df completo)
    medians = train[feature_names].median()
    X_train = train[feature_names].fillna(medians)
    X_test = test[feature_names].fillna(medians)
    y_train_log = np.log1p(train["purchase_price"])
    y_train = train["purchase_price"].values
    y_test = test["purchase_price"].values

    # Entrenamiento
    trials = 0 if args.no_optuna else args.optuna_trials
    models = {}
    logger.info("Entrenando M1 Lineal...")
    models["M1_Linear"] = train_linear(X_train, y_train_log, X_test)
    logger.info("Entrenando M2 Ridge...")
    models["M2_Ridge"] = train_ridge(X_train, y_train_log, X_test)
    logger.info("Entrenando M3 RandomForest...")
    models["M3_RandomForest"] = train_rf(X_train, y_train_log, X_test)
    logger.info(f"Entrenando M4 XGBoost{' + Optuna ' + str(trials) + 'trials' if trials else ' (no Optuna)'} (device={args.device})...")
    models["M4_XGBoost"] = train_xgb(X_train, y_train_log, X_test, optuna_trials=trials, device=args.device)

    # Comparativa (metricas en escala NOMINAL via expm1)
    comparison_rows = []
    predictions_rows = []
    importance_rows = []
    for name, (model, pred_train, pred_test) in models.items():
        train_m = metrics(y_train, pred_train)
        test_m = metrics(y_test, pred_test)
        comparison_rows.append({
            "model": name,
            "train_r2": train_m["r2"], "train_mae": train_m["mae"], "train_mape_pct": train_m["mape_pct"], "train_rmse": train_m["rmse"],
            "test_r2": test_m["r2"], "test_mae": test_m["mae"], "test_mape_pct": test_m["mape_pct"], "test_rmse": test_m["rmse"],
            "n_train": len(y_train), "n_test": len(y_test),
        })
        for i, (yt, yp) in enumerate(zip(y_test, pred_test, strict=False)):
            predictions_rows.append({
                "model": name, "row_id": int(test.iloc[i].get("house_id", i)),
                "year": int(test.iloc[i]["year"]),
                "region": test.iloc[i].get("region", "Unknown"),
                "y_true": float(yt), "y_pred": float(yp), "residual": float(yt - yp),
            })
        imp_df = feature_importance(model, feature_names)
        for _, row in imp_df.head(args.top_k_importance).iterrows():
            importance_rows.append({"model": name, "feature": row["feature"], "importance": float(row["importance"])})

    comparison_df = pd.DataFrame(comparison_rows)
    predictions_df = pd.DataFrame(predictions_rows)
    importance_df = pd.DataFrame(importance_rows)

    for out_dir in (gold, marts):
        comparison_df.to_csv(out_dir / "mart_model_comparison.csv", index=False)
        predictions_df.to_csv(out_dir / "mart_predictions.csv", index=False)
        importance_df.to_csv(out_dir / "mart_feature_importance.csv", index=False)

    # Audit final
    audit_path = gold / "modeling_audit.json"
    audit_path.write_text(json.dumps({
        "feature_matrix": audit,
        "split": {"train_end": args.train_end_year, "test_start": args.test_start_year,
                  "n_train": len(train), "n_test": len(test)},
        "metrics_scale": "nominal_purchase_price_dkk",
        "log_target_used_for_training": True,
        "back_transform": "np.expm1",
        "optuna_trials": trials,
        "device": args.device,
    }, indent=2))

    # Print resumen
    print("\n" + "=" * 60)
    print("RESULTADOS — metricas en escala NOMINAL (purchase_price DKK)")
    print("=" * 60)
    print(comparison_df[["model", "test_r2", "test_mae", "test_mape_pct", "test_rmse"]].to_string(index=False))
    print("=" * 60)
    print("Marts: mart_model_comparison.csv, mart_predictions.csv, mart_feature_importance.csv")
    print(f"Audit: {audit_path}")


if __name__ == "__main__":
    main()
