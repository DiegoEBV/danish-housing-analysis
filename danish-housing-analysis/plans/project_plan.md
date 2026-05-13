# Plan de Trabajo — Danish Housing Analysis

**Curso**: Data Visualization — UPC 2026-01  
**Equipo**: Vilchez · Ballón · Velásquez Borasino

---

## Resumen de Entregables

| Entregable | Semana | Descripción |
|-----------|--------|-------------|
| TB1 | S2 | Ficha del proyecto, pregunta analítica, dataset ✅ |
| TB2 | S4 | Perfilado, diccionario, limpieza inicial ✅ |
| TB3 | S7 | Análisis exploratorio + preparación para Tableau 🔄 |
| TF  | S13 | Dashboard Tableau + presentación final |

---

## Semana 5–7: TB3 — Análisis Exploratorio (EN CURSO)

### Objetivo
Obtener hallazgos exploratorios que validen/rechacen las 3 hipótesis de trabajo
y generar los marts de datos para Tableau.

### Tareas por persona

#### Rody Vilchez
- [ ] Análisis de series de tiempo de precios por región (1992–2024)
- [ ] Cálculo del Índice Regional (base 1992 = 100)
- [ ] Visualización de evolución por tipología de vivienda

#### Diego Ballón
- [ ] Análisis de drawdowns durante crisis 2007–2012
- [ ] Comparativa Copenhague vs. provincias
- [ ] Correlación precio real vs. inflación

#### Christian Velásquez Borasino
- [ ] Análisis de volatilidad por tipología (Summerhouse vs Villa vs Apartamento)
- [ ] Correlación volumen de ventas vs. rendimiento bonos hipotecarios (rezago 1–2 Q)
- [ ] Preparación y exportación de marts para Tableau

### Estructura del notebook TB3

```
notebook/TB3_analisis_exploratorio.ipynb

Sección 1: Carga de datos limpios
Sección 2: Análisis de series temporales
  2.1 Precio real por región (1992–2024)
  2.2 Índice Regional normalizado
  2.3 Heatmap de precios por código postal (mapa)
Sección 3: Análisis por tipología
  3.1 Distribución de precios por house_type
  3.2 Volatilidad comparada
  3.3 Drawdowns por tipología
Sección 4: Análisis macroeconómico
  4.1 Series de tasas de interés e inflación
  4.2 Correlación volumen-bonos
  4.3 Scatter precio real vs. inflación
Sección 5: Hallazgos y validación de hipótesis
Sección 6: Exportación de marts para Tableau
```

### Marts a exportar (para Tableau)
- `mart_quarterly_regional_index.csv` — índice regional trimestral
- `mart_drawdowns.csv` — drawdowns por región y tipología
- `mart_volatility.csv` — volatilidad por tipología y período
- `mart_macro_correlation.csv` — volumen vs. bonos hipotecarios
- `mart_transactions_map.csv` — agregado por zip_code para mapa

---

## Semana 8–12: Dashboard Tableau

### Vistas planificadas

1. **Vista Principal — Línea de tiempo**: Índice Regional Capital vs. Provincias (1992–2024) con overlay de tasas de interés
2. **Vista Crisis**: Drawdowns por tipología durante 2007–2012
3. **Mapa de Precios**: Heatmap por código postal con filtro por año
4. **Vista Macroeconómica**: Scatter y correlación volumen-bonos con rezago

### Cálculos LOD en Tableau
- `FIXED [region], [year] : AVG([sqm_price_real])` — precio promedio anual por región
- `FIXED [house_type] : MAX([sqm_price_real])` — pico histórico por tipología (para drawdown)

---

## Semana 13: Presentación Final

- [ ] Dashboard publicado en Tableau Public
- [ ] Grabación de video demo (5 min)
- [ ] Informe final
