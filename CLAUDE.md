# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

## Project context

Academic project for **Data Visualization — UPC 2026-01**: análisis del mercado residencial danés 1992–2024 (~1.5M transacciones desde el dataset de Kaggle "Danish Residential Housing Prices"). El entregable final es un dashboard de Tableau; el repo contiene el pipeline de limpieza/feature engineering y la generación de marts Gold que alimentan ese dashboard.

**Research question**: ¿qué tipologías de vivienda muestran la mayor volatilidad y drawdowns durante crisis financieras, y cómo difieren los precios entre Copenhague y las provincias bajo distintos regímenes de tasas/inflación?

La documentación interna y los nombres de variables/columnas están **en español y danés** (regiones, `house_type` con valores como `Ejerlejlighed`, `Fritidshus`, etc.) — preservar ese estilo en código nuevo y commits.

## Commands

```bash
# Setup (uv 0.9+ requerido)
uv sync --extra dev --extra notebook

# Cleaning solo (Bronze → Silver; prefiere parquet si existe, sino CSV)
uv run python scripts/run_cleaning.py --config configs/analysis.yaml
uv run python scripts/run_cleaning.py --config configs/analysis.yaml --sample 10000   # smoke test

# Pipeline completo (Silver + 5 marts Gold) — lee parquet 1.2M
uv run python scripts/run_pipeline.py --config configs/analysis.yaml
uv run python scripts/run_pipeline.py --config configs/analysis.yaml --sample 1000    # smoke

# Marts standalone (lee Silver, escribe Gold)
uv run python scripts/export_marts.py --config configs/analysis.yaml

# Subir capas a GCS (requiere gcloud auth application-default login)
uv run python scripts/upload_to_gcs.py --layer all --config configs/analysis.yaml

# Generar marts sintéticos (sin data real, para previews)
uv run python scripts/generate_tableau.py

# Tests
uv run pytest tests/                               # toda la suite
uv run pytest tests/test_cleaning.py::test_<name>  # un solo test
uv run pytest tests/ --cov=src/danish_housing      # con cobertura

# Linters (config en pyproject.toml)
uv run ruff check src/ scripts/ tests/
uv run black src/ scripts/ tests/
uv run mypy src/
```

**Datos**: `data/` está en `.gitignore` y no se commitea. El raw debe colocarse manualmente. Rutas configurables en `configs/analysis.yaml -> paths.raw_csv` (CSV de Kaggle) y `paths.raw_parquet` (1.2M filas, preferido cuando existe).

## Architecture

### Medallion (Bronze → Silver → Gold)

```
Kaggle CSV/Parquet (~1.5M rows)
    ↓  run_cleaning.py / run_pipeline.py
Bronze: data/raw/                         (bucket danish-housing-bronze)
    ↓  src/danish_housing/cleaning.py     (reglas P1–P8)
Silver: data/processed/.../*.parquet      (bucket danish-housing-silver)
    ↓  src/danish_housing/kpis.py         (KPIs 1–5)
Gold:   data/processed/tableau_marts/     (bucket danish-housing-gold)
    ↓
Tableau Desktop (.twbx)
```

- **Bronze** = CSV/Parquet crudo de Kaggle.
- **Silver** = dataset limpio con flags y columnas derivadas. Las reglas viven en `src/danish_housing/cleaning.py` como funciones P1–P8 puras + un `run_cleaning_pipeline` que las orquesta y devuelve `(df_clean, bitacora)`. La **bitácora** (`bitacora_limpieza.csv`) es un artefacto entregable del TB2 — toda regla de limpieza nueva debe loguear vía `_log()` para aparecer en ella.
- **Gold** = 5 marts agregados para Tableau: `mart_quarterly_regional_index`, `mart_drawdowns`, `mart_volatility`, `mart_macro_correlation`, `mart_transactions_map`. Cada mart corresponde a una vista del dashboard final — al añadir/modificar uno, sincronizar `docs/data-dictionary-gold.md` y `docs/tableau-dashboard-design.md`.

### Dos pipelines, no uno

Hay **dos scripts de pipeline** que no son intercambiables — esto es deliberado, no un bug:

- `scripts/run_cleaning.py` — entrega TB2, lee CSV o Parquet desde `configs/analysis.yaml -> paths.raw_*` (prefiere parquet si ambos existen), delega en `src/danish_housing/cleaning.py:run_cleaning_pipeline`, escribe Silver parquet + bitácora.
- `scripts/run_pipeline.py` — entrega TB3, lee Parquet (1.2M filas) desde `paths.raw_parquet` configurable, **inlinea** las reglas P1–P8 + genera los 5 marts Gold en una sola corrida memory-efficient (libera el raw antes de generar marts, recarga sólo las columnas necesarias). **No reusa `cleaning.py`** porque está optimizado para 1.2M filas en RAM limitada.
- `scripts/export_marts.py` — generación de marts standalone leyendo Silver. Pendiente de absorber por completo la FASE B de `run_pipeline.py` (issue `ixa`).

Si tocas reglas de limpieza, **actualiza ambos** o documenta explícitamente la divergencia. El plan de medio plazo (issue `ixa`) es extraer la lógica de marts a `scripts/export_marts.py` reutilizable.

### Configuración

Todo parámetro de negocio vive en `configs/analysis.yaml` y es leído por los scripts vía `yaml.safe_load`. Los nombres de columnas danesas, regiones, tipologías de vivienda, períodos de crisis, año base IPC (2024) y año base del índice regional (1992) están todos centralizados ahí. **No hardcodees** estos valores en código nuevo — añádelos al YAML.

## Source module: `src/danish_housing/`

**[cleaning.py](src/danish_housing/cleaning.py)** — 8 reglas de limpieza, cada una función independiente:

- **P1**: Imputar `city` faltante con `"Unknown"`
- **P2**: Flagear macro faltante (`macro_nulo`, gap 2023–2024)
- **P3**: Flagear ventas no-mercado (`sales_type_valido`: transferencias familiares, tipo `"-"`)
- **P4**: Flagear `year_build < 1800`
- **P5**: Detección de outliers IQR × 3.0 sobre `purchase_price` (`purchase_price_outlier`)
- **P6**: Flagear 1992–1994 como período preliminar (`periodo_preliminar`, menor completitud)
- **P7**: Padding de `zip_code` a 4 dígitos string
- **P8**: Renombrar columnas con `%25` URL-encoded → `_pct`

Entry point: `run_cleaning_pipeline(df, config)` → `(cleaned_df, audit_log_df)`.

**[kpis.py](src/danish_housing/kpis.py)** — 5 KPIs sobre Silver:

1. **Precio Real/m²** (`compute_real_price_per_sqm`) — deflactado con IPC danés (base 2024). El IPC no viene en el dataset; se **deriva** de `dk_ann_infl_rate_pct` haciendo cumulada desde el año más reciente hacia atrás (ver `run_pipeline.py` líneas 70–84). Para años pre-1992 se asume 2% anual de fallback.
2. **Índice Regional** (`compute_regional_index`) — base 1992 = 100, por región. Si una región no tiene observaciones en 1992 el fallback es el primer trimestre disponible.
3. **Drawdown** (`compute_drawdown`) — máximo acumulado por `(region, house_type)` con `cummax`; `drawdown_pct = (precio − cummax) / cummax × 100`.
4. **Volatilidad** (`compute_volatility`) — std del `pct_change` trimestral en ventana móvil de 4 trimestres por `house_type`.
5. **Elasticidad volumen-bonos** (`compute_volume_bond_correlation`) — correlación rodante (8 trimestres) entre `n_transactions` y `yield_mortgage_bonds_pct` con lag de 2 trimestres.

## Gold Marts (Tableau)

| Archivo | Contenido |
|---|---|
| `mart_quarterly_regional_index.csv` | Precios trimestrales + índice base 1992=100 por región |
| `mart_drawdowns.csv` | Drawdown % por trimestre, región, house_type |
| `mart_volatility.csv` | Volatilidad rolling 4Q por house_type |
| `mart_macro_correlation.csv` | Volumen vs. bond yields con lag 2Q |
| `mart_transactions_map.csv` | Agregado por `zip_code` para vista de mapa |

Versiones sintéticas (sin data real) se generan con `scripts/generate_tableau.py`.

## Scripts vs. Notebooks

- **Scripts** (`scripts/`) son los ejecutores autoritativos del pipeline — usa estos para runs reproducibles.
- **Notebooks** (`notebook/`) son artefactos entregables (TB2, TB3) para evaluación; duplican algo de lógica para demostración.
- Al modificar lógica de limpieza, actualizar primero `src/danish_housing/cleaning.py`; los notebooks referencian esas funciones.

## Datos

- **Regiones (5)**: `København` (capital), `Sjælland`, `Syddanmark`, `Midtjylland`, `Nordjylland`.
- **Tipologías de interés (4)**: `Villa`, `Ejerlejlighed` (apartamento), `Fritidshus` (casa de verano), `Rækkehus` (adosada).
- **Períodos de crisis** definidos en config: 2007–2012 (GFC) y 2006–2009 (burbuja inmobiliaria).
- Silver usa Parquet con compresión Snappy; los scripts usan `gc.collect()` explícito para manejar peak memory en runs de 1.5M filas.
- Las columnas `*_pct` originales vienen con `%25` (URL-encoded `%`) en el nombre y son renombradas por la regla P8.

Las reglas de limpieza **flagean** en vez de borrar: `sales_type_valido`, `purchase_price_outlier`, `periodo_preliminar`, `macro_nulo`, etc. Los marts Gold filtran usando esos flags (`sv_c = sv[sv["sales_type_valido"] & ~sv["purchase_price_outlier"] & ...]`). No conviertas estos flags en filtros destructivos en Silver — la trazabilidad del TB2 depende de mantener todas las filas.

## Convenciones de lenguaje

- Código y nombres de variables: inglés (con tokens daneses cuando son nombres propios de dominio: `house_type`, `Ejerlejlighed`).
- Comentarios, documentación y notebooks: español.
- Claves de config: inglés.
- Mensajes de commit: español o inglés, consistente con el contexto del cambio.

## Documentación y entregables

El proyecto se entrega por semanas: TB2 (S4, limpieza ✅), TB3 (S7, modelado y marts 🔄), TF (S13, dashboard ⏳). El estado en vivo está en `docs/project-current-state.md` y el plan en `plans/project_plan.md`. Los runbooks de ejecución end-to-end están en `runbooks/` (`full-execution.md`, `gcp-medallion-setup.md`). Los pendientes de TB3/TF ya están trackeados en `bd` — usar `bd ready` para ver el siguiente trabajo disponible.
