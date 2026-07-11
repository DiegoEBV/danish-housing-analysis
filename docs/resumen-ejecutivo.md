# Resumen Ejecutivo — Mercado Residencial Danés 1992–2024

**Curso:** Data Visualization · UPC 2026-01 · **Entrega:** TF (Entrega 6)
**Equipo:** Vilchez Marin · Ballon Villar · Velasquez Borasino
**Dashboard:** https://gruvizzgobpe.netlify.app/ · **Repositorio:** github.com/DiegoEBV/danish-housing-analysis

---

## Pregunta y alcance

¿Cómo se diferenciaron los precios residenciales entre la **región capital (Copenhague/Zealand)** y
las **provincias** danesas bajo distintos regímenes de tasas e inflación, y **qué tipologías y zonas
concentran la mayor volatilidad y los peores drawdowns** durante las crisis financieras entre 1992 y
2024? El análisis es **descriptivo-predictivo, no causal**, sobre ~1.5 M de transacciones reales
(dataset Kaggle · registros oficiales daneses).

## Hallazgos clave

1. **Divergencia regional estructural.** A 2024Q4, el índice de precio real (base 1992 = 100) alcanza
   **Zealand 210**, **Bornholm 141**, **Jutland 110** y **Fyn & islands 91** (por debajo de su nivel
   de 1992). Zealand **más que duplicó** su precio real; la brecha no se cerró en la recuperación
   post-crisis, lo que apunta a restricciones de oferta urbana de carácter estructural.

2. **El riesgo es urbano, no recreativo.** Contra la intuición inicial (H3), la mayor volatilidad y
   los peores drawdowns están en vivienda urbana de menor ticket: **Apartment** (σ=9.2, drawdown
   **−92.1 %**) y **Townhouse** (σ=10.2, −80.7 %) superan a **Summerhouse** (σ=3.9, −63.1 %). **Villa**
   es el activo más estable (σ=2.3, −44.1 %). El peor drawdown del dataset es Bornholm/Apartment
   2018Q3 (**−92.1 %**), amplificado por baja liquidez (n=5).

3. **La geografía duplica el riesgo (segmentación no supervisada).** Un clustering **PCA + KMeans**
   (sin usar la región como input) separa los códigos postales en **dos perfiles**: uno de
   **precio alto / crecimiento dinámico / bajo drawdown** (−42 %, concentrado en el metro de
   Copenhague) y otro de **precio bajo / plano / volátil** (−62 %, dominado por Jutland/provincias).
   El método **reconstruye de forma emergente la división Capital vs. Provincias de H2**.

4. **Transmisión hipotecaria asimétrica.** La correlación entre volumen de transacciones y
   rendimiento de bonos hipotecarios (rezago 2 trimestres) es negativa en promedio pero se **agudiza
   en crisis** (hasta −0.96 en la GFC) y se aproxima a cero en expansión: el canal de crédito opera
   sobre todo bajo estrés financiero.

5. **Modelo de precios.** El mejor modelo (**XGBoost**) explica un **R²=0.44** en el test out-of-time
   2018–2024 (MAE ≈ **867 k DKK**, MAPE ≈ 37 %), muy por encima del baseline lineal. El gap
   train→test refleja el *distribution shift* del boom post-COVID, no overfitting.

## Implicación para el usuario (inversor residencial danés)

- **Priorizar Villa/Apartment en Zealand** (metro capital): mejor binomio riesgo-retorno; la escasez
  de oferta protege el precio en las caídas.
- **Evitar Apartment/Townhouse en provincias periféricas** (Jutland, Bornholm) en ciclos de alza de
  tasas: combinan menor retorno con drawdowns más profundos y liquidez frágil.
- **Monitorear el bono hipotecario danés** como *leading indicator* con rezago de ~2 trimestres.

## Cómo responde el dashboard

El dashboard (6 pestañas: Resumen → Precios → Geografía → Crisis y Riesgo → Modelado → Conclusiones)
integra **vista longitudinal** (índice regional 1992–2024 y evolución de drawdowns, con marcadores de
shocks GFC/COVID/alza-2022) y **vista transversal** (mapa coroplético por código postal y heatmap
región × tipología). La pestaña Geografía incorpora la **segmentación PCA/KMeans** para colorear las
zonas por perfil de riesgo. Todo se alimenta de la capa **Gold real** (`gs://danish-housing-gold/marts/`).

## Límites y supuestos

Análisis **descriptivo, no causal**; precisión espacial a nivel de código postal (sin coordenadas
exactas); 2023–2024 con nulos macro flagueados; período 1992–1994 de menor completitud; deflactor
basado en `dk_ann_infl_rate`. No se extrapola fuera de 1992–2024.
