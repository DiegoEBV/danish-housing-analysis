# Plan de Construcción del Dashboard — Tableau

**Proyecto**: Dinámica de precios residenciales en Dinamarca 1992–2024  
**Herramienta**: Tableau Desktop / Tableau Public  
**Semana objetivo**: S13 (entrega final)

---

## Fuentes de Datos

Conectar Tableau a los marts Gold. Orden de conexión recomendado:

```
1. mart_quarterly_regional_index.csv   ← Vista 1 (principal)
2. mart_transactions_map.csv           ← Vista 2 (mapa)
3. mart_drawdowns.csv                  ← Vista 3 (crisis)
4. mart_volatility.csv                 ← Vista 4 (volatilidad)
5. mart_macro_correlation.csv          ← Vista 5 (macro)
```

Relaciones en Tableau:
- `mart_quarterly_regional_index` LEFT JOIN `mart_drawdowns` ON `quarter` + `region`
- `mart_quarterly_regional_index` LEFT JOIN `mart_volatility` ON `quarter` + `house_type`

---

## Vista 1 — Evolución Regional (Hoja: `regional_timeline`)

### Tipo de gráfico
Dual-axis line chart

### Configuración
| Eje | Campo | Pill |
|-----|-------|------|
| Columns | `quarter` | Continuo (fecha) |
| Rows (eje izq.) | `AVG(regional_index)` | Medida |
| Rows (eje der.) | `AVG(yield_mortgage_bonds_pct)` | Medida |
| Color | `region` | Dimensión |
| Filtros | `house_type`, `region` | — |

### Cálculos LOD necesarios

```
// Precio base para normalización (1992)
[Base Price 1992] = 
  {FIXED [region] : 
    AVG(IF YEAR([quarter]) = 1992 THEN [avg_sqm_price_real] END)
  }

// Índice Regional (si no viene calculado del mart)
[Regional Index Calc] = 
  AVG([avg_sqm_price_real]) / [Base Price 1992] * 100
```

### Formato
- Línea Copenhague: rojo (#C8102E), grosor 2.5
- Líneas provincias: azules con opacidad 60%
- Eje derecho (yield): gris punteado
- Bandas sombreadas en crisis: 2007–2012, COVID 2020

---

## Vista 2 — Mapa de Precios por Código Postal (Hoja: `price_map`)

### Tipo de gráfico
Filled Map (choropleth)

### Configuración
| Shelf | Campo | Notas |
|-------|-------|-------|
| Columns | `Longitude` (generado) | Tableau geocodifica zip_code danés |
| Rows | `Latitude` (generado) | — |
| Color | `AVG(avg_sqm_price_real)` | Gradiente: azul (bajo) → rojo (alto) |
| Tooltip | `city`, `avg_sqm_price_real`, `n_transactions` | — |
| Filtro de página | `year` | Slider de año |

### Pasos para configurar el mapa
1. Drag `zip_code` al canvas → Tableau lo detecta como geográfico
2. Si no funciona: Editar ubicaciones → País: Denmark, Código postal
3. Añadir `avg_sqm_price_real` como color
4. Crear parámetro `p_year` (entero, 1992–2024) como filtro del slider

---

## Vista 3 — Drawdown por Tipología (Hoja: `drawdown_crisis`)

### Tipo de gráfico
Area chart (valores negativos)

### Configuración
| Shelf | Campo | Notas |
|-------|-------|-------|
| Columns | `quarter` | Continuo |
| Rows | `MIN(drawdown_pct)` | Valores negativos → área hacia abajo |
| Color | `house_type` | 4 colores distintos |
| Rows adicional | `AVG(avg_sqm_price_real)` | Dual axis para contexto |

### Cálculo LOD para drawdown

```
// Máximo histórico acumulado por región y tipología
[Cumulative Max Price] = 
  RUNNING_MAX(AVG([avg_sqm_price_real]))

// Drawdown
[Drawdown %] = 
  (AVG([avg_sqm_price_real]) - [Cumulative Max Price]) 
  / [Cumulative Max Price] * 100
```

### Anotaciones
- Banda sombreada 2007–2012: "Crisis Financiera Global"
- Referencia línea 0%: precio en el pico

---

## Vista 4 — Volatilidad Comparada (Hoja: `volatility_comparison`)

### Tipo de gráfico
Line chart con área sombreada

### Configuración
| Shelf | Campo | Notas |
|-------|-------|-------|
| Columns | `quarter` | Continuo |
| Rows | `AVG(volatility_4q)` | — |
| Color | `house_type` | Summerhouse destacado en rojo |
| Filtros | Período macro | Menú desplegable |

---

## Vista 5 — Correlación Volumen-Bonos (Hoja: `macro_scatter`)

### Tipo de gráfico
Scatter plot + línea de tendencia

### Configuración
| Shelf | Campo | Notas |
|-------|-------|-------|
| Columns | `AVG(bond_yield_lag2q)` | Eje X: yield con rezago 2Q |
| Rows | `SUM(n_transactions)` | Eje Y: volumen trimestral |
| Color | `periodo_macro` | 5 períodos con colores distintos |
| Size | Fijo | — |

### Línea de tendencia
Tableau → Analytics → Trend Line → Linear  
Mostrar R² y p-value en tooltip

---

## Dashboard Principal — Layout

```
┌─────────────────────────────────────────────────────────┐
│  TÍTULO + Filtros globales (región, tipo, año)          │
├──────────────────────────┬──────────────────────────────┤
│                          │                              │
│   Vista 1: Timeline      │   Vista 2: Mapa              │
│   (60% ancho)            │   (40% ancho)                │
│                          │                              │
├──────────┬───────────────┴──────────────────────────────┤
│          │                                              │
│ Vista 3  │   Vista 4: Volatilidad  │  Vista 5: Macro    │
│ Drawdown │                         │  Scatter           │
│          │                         │                    │
└──────────┴─────────────────────────┴────────────────────┘
```

### Filtros globales (aplican a todas las vistas)
- `house_type`: multiselect (Villa, Apartamento, Summerhouse, Adosado)
- `region`: multiselect (5 regiones)
- Slider de año: 1992–2024

---

## Checklist de Construcción

### Semana 8–9: Datos y conexión
- [ ] Descargar marts Gold desde GCS
- [ ] Conectar Tableau a los 5 CSVs
- [ ] Configurar relaciones entre fuentes
- [ ] Crear parámetros: `p_year`, `p_region`, `p_house_type`

### Semana 10–11: Vistas
- [ ] Vista 1: timeline regional completo
- [ ] Vista 2: mapa choropleth funcional
- [ ] Vista 3: drawdown con bandas de crisis
- [ ] Vista 4: volatilidad por tipología
- [ ] Vista 5: scatter macro + tendencia

### Semana 12: Dashboard y pulido
- [ ] Unir las 5 vistas en un dashboard
- [ ] Configurar filtros globales
- [ ] Agregar tooltips informativos
- [ ] Añadir disclaimers metodológicos
- [ ] Revisar paleta de colores (UPC: rojo #C8102E, azul #003087)

### Semana 13: Publicación
- [ ] Publicar en Tableau Public
- [ ] Grabar video demo de 5 minutos
- [ ] Subir URL de Tableau al repositorio como `docs/tableau-public-url.md`
