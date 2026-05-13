# Diseño del Dashboard Tableau

## Descripción General

Dashboard interactivo en Tableau que explora la **divergencia regional y resiliencia
macroeconómica** del mercado residencial danés (1992–2024).

**Usuario objetivo primario**: Inversores inmobiliarios  
**Usuarios secundarios**: Analistas de riesgo, Consultores públicos

---

## Estructura de Vistas

### Vista 1 — Línea de Tiempo Regional
**Pregunta**: ¿Cómo evolucionaron los precios en Copenhague vs. provincias?

- Tipo: Dual-axis line chart
- X: Trimestre (1992 Q1 → 2024 Q4)
- Y izquierda: Índice Regional (base 1992 = 100)
- Y derecha: Rendimiento bonos hipotecarios (%)
- Color: región (Copenhague destacado)
- Filtros: house_type, región
- LOD: `FIXED [region], YEAR([date]) : AVG([sqm_price_real])`

### Vista 2 — Mapa de Precios por Código Postal
**Pregunta**: ¿Dónde están los precios más altos hoy vs. en el pasado?

- Tipo: Filled map (choropleth)
- Granularidad: zip_code (join con shapefiles PostNord)
- Color: precio real/m² (gradiente)
- Filtro temporal: slider de año
- Tooltip: ciudad, precio promedio, n° transacciones

### Vista 3 — Drawdown por Tipología
**Pregunta**: ¿Qué tipos de vivienda cayeron más durante la crisis 2007–2012?

- Tipo: Area chart (drawdown negativo)
- X: Trimestre
- Y: Drawdown % desde pico
- Facets: house_type
- Destacado: período de crisis con banda sombreada
- LOD: `FIXED [house_type] : RUNNING_MAX([sqm_price_real])`

### Vista 4 — Volatilidad Comparada
**Pregunta**: ¿Qué tipología muestra mayor riesgo histórico?

- Tipo: Box plots + línea de volatilidad rolling
- X: Período (5-year bins)
- Y: Desv. estándar cambio % trimestral
- Color: house_type

### Vista 5 — Correlación Volumen-Bonos
**Pregunta**: ¿Cómo responde el mercado a cambios en tasas?

- Tipo: Scatter + línea de tendencia
- X: Rendimiento bonos hipotecarios (rezago 2 Q)
- Y: Volumen de ventas trimestral
- Color: período (pre/durante/post crisis)
- Anotaciones: crisis 2008, subida de tasas 2022

---

## Cálculos LOD Clave

```
// Índice Regional Normalizado
[Regional Index] = 
  AVG([sqm_price_real]) / 
  {FIXED [region] : 
    AVG(IF YEAR([date]) = 1992 THEN [sqm_price_real] END)
  } * 100

// Pico histórico por tipología (para drawdown)
[Peak Price] = 
  {FIXED [house_type] : 
    RUNNING_MAX(AVG([sqm_price_real]))
  }

// Drawdown
[Drawdown %] = 
  (AVG([sqm_price_real]) - [Peak Price]) / [Peak Price] * 100
```

---

## Marts de Datos Necesarios

| Archivo | Descripción | Columnas Clave |
|---------|-------------|----------------|
| `mart_quarterly_regional_index.csv` | Índice trimestral por región | quarter, region, regional_index, avg_price_real |
| `mart_drawdowns.csv` | Drawdown por región y tipología | quarter, region, house_type, drawdown_pct |
| `mart_volatility.csv` | Volatilidad rolling por tipología | quarter, house_type, volatility_4q |
| `mart_macro_correlation.csv` | Volumen vs. bonos | quarter, n_transactions, avg_bond_yield, bond_yield_lag2 |
| `mart_transactions_map.csv` | Precios por zip_code para mapa | year, zip_code, avg_sqm_price_real, n_transactions |

---

## Disclaimer Metodológico

> Este dashboard es de naturaleza **descriptiva**, no predictiva. Las correlaciones
> observadas entre variables macroeconómicas y precios no implican causalidad.
> Los datos 1992–1994 pueden tener menor completitud por la transición al sistema digital.
