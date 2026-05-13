# Danish Residential Housing Analysis 🏠🇩🇰

**Divergencia Regional y Resiliencia Macroeconómica del Mercado Residencial Danés (1992–2024)**

Proyecto del curso **Data Visualization — UPC 2026-01**

| Código | Alumno |
|--------|--------|
| U202216562 | Vilchez Marín, Rody Sebastián |
| U201520327 | Ballón Villar, Diego Eduardo |
| U202218075 | Velásquez Borasino, Christian Aaron |

---

## Pregunta Analítica

> ¿Cómo se han diferenciado los precios residenciales entre la región capital y las provincias danesas bajo distintos regímenes de tasas de interés e inflación, y qué tipologías de vivienda muestran mayor volatilidad y peores drawdowns durante las crisis financieras entre 1992 y 2024?

---

## Estructura del Repositorio

```
danish-housing-analysis/
├── configs/                  # Parámetros de análisis (umbrales, filtros, paths)
├── docs/                     # Documentación técnica y diseño del dashboard
├── notebook/                 # Jupyter notebooks por etapa del proyecto
│   ├── TB2_perfilado_limpieza.ipynb
│   └── TB3_analisis_exploratorio.ipynb
├── plans/                    # Plan de trabajo por semanas
├── runbooks/                 # Guías de ejecución paso a paso
├── scripts/                  # Scripts Python reutilizables
├── src/danish_housing/       # Módulo Python del proyecto
├── tableau/                  # Especificaciones y recursos del dashboard
├── tests/                    # Tests unitarios
└── data/                     # (ignorado por git — ver .gitignore)
    ├── raw/
    └── processed/
```

---

## Dataset

- **Fuente**: [Kaggle — Danish Residential Housing Prices 1992–2024](https://www.kaggle.com/datasets/martinfrederiksen/danish-residential-housing-prices-1992-2024/data)
- **Volumen**: ~1,500,000 registros
- **Granularidad**: Transacción individual (dirección, código postal, fecha exacta)
- **Cobertura**: 1992–2024

---

## KPIs Principales

| KPI | Descripción |
|-----|-------------|
| **Precio Real/m²** | Precio deflactado con IPC danés (base 2024) |
| **Índice Regional** | Evolución normalizada base 1992 = 100 |
| **Drawdown Pico-Valle** | Caída máxima desde pico previo a crisis |
| **Volatilidad** | Desv. estándar cambio % precio (ventana 4 trimestres) |
| **Elasticidad Vol-Bonos** | Correlación volumen de ventas vs. bonos hipotecarios |

---

## Quickstart

```bash
# Clonar el repo
git clone https://github.com/<tu-usuario>/danish-housing-analysis.git
cd danish-housing-analysis

# Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Ejecutar pipeline de limpieza
python scripts/run_cleaning.py --config configs/analysis.yaml
```

---

## Hipótesis de Trabajo

1. **Correlación Inversa**: El volumen de ventas reacciona negativamente a la subida de tasas de bonos hipotecarios (rezago 1–2 trimestres).
2. **Efecto Capital**: Copenhague muestra precios más resilientes ante shocks por escasez crítica de oferta.
3. **Vulnerabilidad Recreativa**: Las *Summerhouses* presentan los drawdowns más profundos durante recesiones.

---

## Entregables por Semana

| Semana | Entregable |
|--------|-----------|
| TB2 (S4) | Perfilado, Diccionario de Datos y Limpieza Inicial |
| TB3 (S7) | Análisis Exploratorio y Preparación para Tableau |
| TF (S13) | Dashboard Tableau + Presentación Final |

---

## Herramienta de Visualización

**Tableau Desktop / Public** con:
- Cálculos LOD para índices regionales
- Series temporales macroeconómicas integradas
- Mapas de calor por código postal (join con shapefiles PostNord)
