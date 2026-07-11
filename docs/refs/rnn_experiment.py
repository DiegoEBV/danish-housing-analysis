"""
Experimento de forecasting: ¿ayudan los modelos recurrentes (GRU/LSTM/RNN) a
predecir la serie trimestral del índice/precio real regional danés, frente a
baselines simples y árboles?

Tarea: forecast one-step-ahead (t+1) del log-precio real por m2, por región.
Validación TEMPORAL (walk-forward con modelo fijo): train = primeros ~75% de
trimestres, test = último ~25%. Sin shuffle.

Modelos:
  - naive (random walk: pred = ultimo valor)
  - seasonal_naive (pred = valor de t-4)
  - ridge_lags (regresion lineal L2 sobre lags de log-returns)
  - xgboost_lags (arboles sobre lags de log-returns)
  - gru, lstm, rnn (recurrentes chicos, 1 capa, dropout, early stopping)

Salidas: tabla de metricas (RMSE/MAE/MAPE/skill vs naive) promedio y por region,
CSV y figura comparativa.
"""
import os
import random
import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

import torch
import torch.nn as nn
torch.manual_seed(SEED)
torch.use_deterministic_algorithms(True, warn_only=True)

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
REPO = "/home/rosewt-dell/Code/cursos/vivienda-dinamarca/danish-housing-analysis"
DATA = os.path.join(REPO, "data/marts/mart_quarterly_regional_index.csv")
OUT_CSV = os.path.join(REPO, "data/marts/mart_rnn_experiment.csv")
OUT_FIG = os.path.join(REPO, "docs/refs/rnn_vs_baseline.png")

L = 8            # numero de lags (2 anos)
TEST_FRAC = 0.25 # ultimo 25% de trimestres como holdout

# ----------------------------------------------------------------------------
# Carga + reconstruccion de serie continua por region
# ----------------------------------------------------------------------------
def qnum(q):
    return int(q[:4]) * 4 + (int(q[-1]) - 1)

def qlabel(n):
    return f"{n // 4}Q{n % 4 + 1}"

df = pd.read_csv(DATA)
df["qn"] = df["quarter"].map(qnum)

series = {}   # region -> DataFrame(qn, quarter, price, logp) continua
for r, g in df.groupby("region"):
    g = g.sort_values("qn")
    full = np.arange(g["qn"].min(), g["qn"].max() + 1)
    s = (g.set_index("qn")["avg_sqm_price_real"]
           .reindex(full))
    logp = np.log(s).interpolate(method="linear")  # rellena el hueco 2017Q1-Q2
    series[r] = pd.DataFrame({
        "qn": full,
        "quarter": [qlabel(n) for n in full],
        "price": np.exp(logp.values),
        "logp": logp.values,
    })

regions = sorted(series.keys())

# cutoff temporal global: ultimo 25% de la linea de tiempo completa
all_qn = np.arange(min(s["qn"].min() for s in series.values()),
                   max(s["qn"].max() for s in series.values()) + 1)
cutoff = np.quantile(all_qn, 1 - TEST_FRAC)
print(f"Cutoff temporal (test empieza en): {qlabel(int(np.ceil(cutoff)))}")

# ----------------------------------------------------------------------------
# Dataset supervisado: features = L log-returns pasados (+ one-hot region);
# target = log-return t+1. Reconstruimos precio: p_hat = p_t * exp(r_hat).
# ----------------------------------------------------------------------------
def build_supervised():
    rows = []
    for ri, r in enumerate(regions):
        d = series[r]
        logp = d["logp"].values
        ret = np.diff(logp)                 # r_t = logp_t - logp_{t-1}
        qn = d["qn"].values
        # target index t+1 corresponde a ret[t]; features = ret[t-L .. t-1]
        for t in range(L, len(ret)):
            feat = ret[t - L:t]             # L returns previos
            target_ret = ret[t]            # return a predecir
            tgt_qn = qn[t + 1]             # trimestre del valor objetivo
            price_t = np.exp(logp[t])      # ultimo precio observado (base)
            price_next = np.exp(logp[t + 1])
            rows.append(dict(
                region=r, region_idx=ri, tgt_qn=tgt_qn,
                feat=feat, target_ret=target_ret,
                price_t=price_t, price_next=price_next,
                # seasonal naive: precio de t-3 (4 trimestres antes del objetivo)
                price_season=np.exp(logp[t - 3]),
            ))
    return rows

rows = build_supervised()
is_test = np.array([r["tgt_qn"] >= cutoff for r in rows])
tr = [r for r, m in zip(rows, is_test) if not m]
te = [r for r, m in zip(rows, is_test) if m]
print(f"Muestras: train={len(tr)}  test={len(te)}  (L={L}, regiones={len(regions)})")

X_tr = np.stack([r["feat"] for r in tr])
X_te = np.stack([r["feat"] for r in te])
y_tr = np.array([r["target_ret"] for r in tr])
y_te = np.array([r["target_ret"] for r in te])
reg_tr = np.array([r["region_idx"] for r in tr])
reg_te = np.array([r["region_idx"] for r in te])

# one-hot region para modelos poolados (Ridge/XGB)
def onehot(idx):
    m = np.zeros((len(idx), len(regions)))
    m[np.arange(len(idx)), idx] = 1
    return m

Xoh_tr = np.hstack([X_tr, onehot(reg_tr)])
Xoh_te = np.hstack([X_te, onehot(reg_te)])

# escalado de returns (fit en train)
sc = StandardScaler().fit(X_tr)
Xs_tr = sc.transform(X_tr)
Xs_te = sc.transform(X_te)

# ----------------------------------------------------------------------------
# Metricas: se calculan sobre el PRECIO real (nivel), reconstruido.
# ----------------------------------------------------------------------------
def ret_to_price(records, ret_hat):
    return np.array([rec["price_t"] * np.exp(rr) for rec, rr in zip(records, ret_hat)])

def metrics(y_true_price, y_hat_price):
    err = y_hat_price - y_true_price
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mape = float(np.mean(np.abs(err / y_true_price)) * 100)
    return rmse, mae, mape

price_te = np.array([r["price_next"] for r in te])

# ----------------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------------
preds = {}  # nombre -> precio predicho en test

# Baseline naive: random walk -> ret_hat = 0
preds["naive"] = ret_to_price(te, np.zeros(len(te)))
# Seasonal naive: precio = precio 4 trimestres antes
preds["seasonal_naive"] = np.array([r["price_season"] for r in te])

# Ridge sobre lags + region
ridge = Ridge(alpha=1.0, random_state=SEED)
ridge.fit(Xoh_tr, y_tr)
preds["ridge_lags"] = ret_to_price(te, ridge.predict(Xoh_te))

# XGBoost sobre lags + region
xgb = XGBRegressor(
    n_estimators=300, max_depth=3, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
    random_state=SEED, n_jobs=4, verbosity=0,
)
xgb.fit(Xoh_tr, y_tr)
preds["xgboost_lags"] = ret_to_price(te, xgb.predict(Xoh_te))

# ----------------------------------------------------------------------------
# Recurrentes: input = secuencia de L returns escalados con one-hot region
# concatenado en cada paso temporal. Salida = return t+1.
# ----------------------------------------------------------------------------
def make_seq(Xs, reg_idx):
    # (N, L, 1 + n_regions)
    N = Xs.shape[0]
    oh = onehot(reg_idx)                       # (N, R)
    seq = np.zeros((N, L, 1 + len(regions)), dtype=np.float32)
    seq[:, :, 0] = Xs
    seq[:, :, 1:] = oh[:, None, :]
    return seq

seq_tr = torch.tensor(make_seq(Xs_tr, reg_tr))
seq_te = torch.tensor(make_seq(Xs_te, reg_te))
yt_tr = torch.tensor(y_tr, dtype=torch.float32).view(-1, 1)

# split de validacion interno (ultimo 15% del train, temporal por tgt_qn)
order = np.argsort([r["tgt_qn"] for r in tr])
n_val = max(8, int(0.15 * len(tr)))
val_idx = order[-n_val:]
trn_idx = order[:-n_val]

class RecNet(nn.Module):
    def __init__(self, kind, in_dim, hidden=24, dropout=0.15):
        super().__init__()
        rnn = {"gru": nn.GRU, "lstm": nn.LSTM, "rnn": nn.RNN}[kind]
        self.rnn = rnn(in_dim, hidden, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.rnn(x)
        last = out[:, -1, :]
        return self.head(self.drop(last))

def train_rec(kind, max_epochs=250, patience=25, lr=5e-3):
    torch.manual_seed(SEED)
    net = RecNet(kind, in_dim=1 + len(regions))
    opt = torch.optim.Adam(net.parameters(), lr=lr, weight_decay=1e-4)
    lossf = nn.MSELoss()
    Xtn, ytn = seq_tr[trn_idx], yt_tr[trn_idx]
    Xvl, yvl = seq_tr[val_idx], yt_tr[val_idx]
    best, best_state, bad = np.inf, None, 0
    for ep in range(max_epochs):
        net.train()
        opt.zero_grad()
        loss = lossf(net(Xtn), ytn)
        loss.backward()
        opt.step()
        net.eval()
        with torch.no_grad():
            vl = lossf(net(Xvl), yvl).item()
        if vl < best - 1e-6:
            best, best_state, bad = vl, {k: v.clone() for k, v in net.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        rh = net(seq_te).numpy().ravel()
    return rh

for kind in ["rnn", "gru", "lstm"]:
    rh = train_rec(kind)
    preds[kind] = ret_to_price(te, rh)

# ----------------------------------------------------------------------------
# Tabla de resultados: global (promedio across regiones) y por region
# ----------------------------------------------------------------------------
records = []
naive_rmse_global = metrics(price_te, preds["naive"])[0]

# por-region rmse naive para skill por region
def region_mask(idx):
    return reg_te == idx

naive_rmse_reg = {}
for ri, r in enumerate(regions):
    m = region_mask(ri)
    naive_rmse_reg[r] = metrics(price_te[m], preds["naive"][m])[0]

for name, ph in preds.items():
    rmse, mae, mape = metrics(price_te, ph)
    skill = 1 - rmse / naive_rmse_global
    records.append(dict(model=name, scope="GLOBAL", region="ALL",
                        rmse=rmse, mae=mae, mape=mape, skill_vs_naive=skill,
                        n=len(price_te)))
    for ri, r in enumerate(regions):
        m = region_mask(ri)
        rm, ma, mp = metrics(price_te[m], ph[m])
        sk = 1 - rm / naive_rmse_reg[r]
        records.append(dict(model=name, scope="REGION", region=r,
                            rmse=rm, mae=ma, mape=mp, skill_vs_naive=sk,
                            n=int(m.sum())))

res = pd.DataFrame(records)
res.to_csv(OUT_CSV, index=False)

# ----------------------------------------------------------------------------
# Reporte a consola
# ----------------------------------------------------------------------------
order_models = ["naive", "seasonal_naive", "ridge_lags", "xgboost_lags",
                "rnn", "gru", "lstm"]
g = (res[res.scope == "GLOBAL"]
     .set_index("model").loc[order_models]
     [["rmse", "mae", "mape", "skill_vs_naive"]])
print("\n=== GLOBAL (promedio across regiones, holdout temporal) ===")
print(g.round(3).to_string())

print("\n=== RMSE por region (nivel de precio real DKK/m2) ===")
piv = (res[res.scope == "REGION"]
       .pivot(index="model", columns="region", values="rmse")
       .loc[order_models])
print(piv.round(1).to_string())

print("\n=== SKILL vs naive por region (>0 mejor que naive) ===")
pivs = (res[res.scope == "REGION"]
        .pivot(index="model", columns="region", values="skill_vs_naive")
        .loc[order_models])
print(pivs.round(3).to_string())

# ----------------------------------------------------------------------------
# Figura comparativa
# ----------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# (a) skill vs naive global por modelo
colors = ["#9e9e9e", "#9e9e9e", "#4c72b0", "#dd8452", "#c44e52", "#55a868", "#8172b3"]
skills = [g.loc[m, "skill_vs_naive"] for m in order_models]
axes[0].bar(order_models, skills, color=colors)
axes[0].axhline(0, color="k", lw=0.8)
axes[0].set_ylabel("Skill score vs naive  (1 - RMSE/RMSE_naive)")
axes[0].set_title("(a) Mejora sobre naive — holdout temporal")
axes[0].tick_params(axis="x", rotation=45)
for i, v in enumerate(skills):
    axes[0].text(i, v + (0.005 if v >= 0 else -0.02), f"{v:+.3f}",
                 ha="center", va="bottom" if v >= 0 else "top", fontsize=8)

# (b) forecast vs real en test para Zealand
r = "Zealand"
ri = regions.index(r)
m = reg_te == ri
qs = [rec["tgt_qn"] for rec, mm in zip(te, m) if mm]
xlab = [qlabel(int(q)) for q in qs]
xr = np.arange(len(qs))
axes[1].plot(xr, price_te[m], "k-o", ms=3, label="real")
for name, ls in [("naive", ":"), ("xgboost_lags", "--"), ("gru", "-"), ("lstm", "-")]:
    axes[1].plot(xr, preds[name][m], ls, lw=1.4, label=name, alpha=0.85)
axes[1].set_title(f"(b) Forecast t+1 vs real — {r} (holdout)")
axes[1].set_ylabel("Precio real DKK/m2")
step = max(1, len(xr) // 8)
axes[1].set_xticks(xr[::step])
axes[1].set_xticklabels(xlab[::step], rotation=45, fontsize=8)
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig(OUT_FIG, dpi=120)
print(f"\nGuardado: {OUT_CSV}")
print(f"Guardado: {OUT_FIG}")
