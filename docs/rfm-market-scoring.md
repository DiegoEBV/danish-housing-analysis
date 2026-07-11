# RFM de atractivo de mercado por código postal

**Entrega 6 / TF — complemento analítico de la segmentación no supervisada.**

## 1. Encuadre honesto: NO es RFM de clientes

El RFM clásico (Recency, Frequency, Monetary) segmenta **clientes con compras repetidas**
(retail/marketing). Este dataset son **transacciones de vivienda sin ID de comprador**, así que un
RFM de clientes **no aplica**. Lo reformulamos como **RFM de atractivo de mercado por `zip_code`**:

| Dimensión | Proxy de mercado | Feature |
|---|---|---|
| **R**ecency | momentum reciente (¿el mercado está caliente *ahora*?) | `growth_recent` |
| **F**requency | liquidez (¿se puede transar con facilidad?) | `liquidity_log` |
| **M**onetary | nivel de precio / valor | `price_level` |

Cada zip recibe un **score 1–5 por dimensión** (quintiles) y un segmento de negocio. Reusa
`build_features` de `run_segmentation.py` → mismo universo de **483 zips** (mismos filtros de
cobertura: ≥10 años, ≥15 transacciones/año).

## 2. Segmentos resultantes (483 zips)

| Segmento | n | R (growth) | F (liquidez) | M (precio/m²) | drawdown | región dom. |
|---|--:|--:|--:|--:|--:|--|
| **Champions** (premium caliente-líquido) | 51 | +0.25 | alta | 27.9k | −45.8% | Zealand |
| **Premium frío** (caro, sin momentum) | 39 | −0.11 | alta | 26.5k | −48.7% | Jutland |
| **Emergente** (momentum, ticket medio-bajo) | 93 | +0.19 | media | 12.9k | −57.0% | Jutland |
| **Value líquido** (barato, accesible) | 36 | −0.11 | alta | 11.6k | −53.1% | Jutland |
| **Periférico dormido** (ilíquido, frío) | 70 | −0.21 | baja | 11.2k | −61.3% | Jutland |
| Intermedio | 194 | — | — | 21.3k | −49.5% | Zealand |

## 3. ¿Aporta o es redundante con la segmentación KMeans?

**Cramér's V (RFM ↔ arquetipos KMeans) = 0.443** → asociación **moderada**, lejos de 1
(redundante). El RFM **complementa**, no repite:

- **KMeans mete todo lo premium en un solo cluster** ("Premium estable/líquido"). El RFM lo **parte
  por momentum**: *Champions* (premium **caliente**) vs *Premium frío* (caro pero **sin impulso**).
  Esa distinción — comprar premium *con* o *sin* momentum — el clustering de riesgo-retorno no la ve.
- El RFM aísla los **"Periférico dormido"** (mercados fríos e ilíquidos) que KMeans dispersa entre
  sus clusters.

**Valor agregado real:** la dimensión **Recency/momentum** (eje temporal que la segmentación
riesgo-retorno no scorea) + un **scoring 1–5 legible** para el inversor.

**Solape (honestidad):** F y M reusan liquidez y precio, que ya son features de la segmentación; lo
genuinamente nuevo es R y el scoring. Por eso se posiciona como **vista complementaria de decisión**,
no como una segmentación alternativa.

## 4. Uso en el dashboard

El inversor filtra por **arquetipo de riesgo-retorno** (¿qué perfil?) **Y** por **RFM** (¿está
atractivo *ahora*?): p.ej. un "Value con crecimiento" que además es "Emergente" (RFM) = oportunidad
de momentum; un "Premium frío" = caro sin impulso, esperar.

## 5. Reproducibilidad

```bash
uv run python scripts/run_rfm.py --config configs/analysis.yaml
```

- Determinista (quintiles por rank estable). Parámetros en `configs/analysis.yaml → rfm`.
- Salidas: `data/marts/mart_rfm_segments.csv`, `docs/refs/rfm_segments.png`.

## 6. Limitaciones

- **No es RFM de clientes** — es un reencuadre por mercado; se declara explícitamente.
- Solape parcial con la segmentación (F≈liquidez, M≈precio); el aporte es Recency + interpretabilidad.
- Descriptivo: score de atractivo histórico/reciente, no predice retorno futuro.
