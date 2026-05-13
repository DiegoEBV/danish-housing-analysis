# Cómo subir este proyecto a GitHub

## 1. Crear el repositorio en GitHub

1. Ve a https://github.com/new
2. Nombre sugerido: `danish-housing-analysis`
3. Descripción: `Dinámica de precios residenciales en Dinamarca 1992–2024 | UPC Data Visualization 2026-01`
4. Visibilidad: Public (o Private si el curso lo requiere)
5. **No** inicialices con README (ya lo tienes)
6. Clic en "Create repository"

## 2. Subir los archivos

En tu terminal, desde la carpeta del proyecto:

```bash
cd danish-housing-analysis

git init
git add .
git commit -m "feat: estructura inicial del proyecto TB2 + módulo de limpieza"

git remote add origin https://github.com/<TU_USUARIO>/danish-housing-analysis.git
git branch -M main
git push -u origin main
```

## 3. Verificar que .gitignore está funcionando

Los datos NUNCA deben subirse:

```bash
git status
# No debe aparecer ningún .csv ni .parquet
```

## 4. Agregar a tus compañeros como colaboradores

Settings → Collaborators → Add people → buscar por usuario de GitHub:
- Rody Vilchez
- Diego Ballón
- Christian Velásquez Borasino

## 5. Estructura final esperada en GitHub

```
danish-housing-analysis/
├── README.md          ← portada del repo
├── CLAUDE.md          ← instrucciones para Claude Code
├── .gitignore
├── requirements.txt
├── configs/
│   └── analysis.yaml
├── docs/
│   └── tableau-dashboard-design.md
├── notebook/
│   └── TB2_perfilado_limpieza.ipynb   ← copiar desde tu archivo local
├── plans/
│   └── project_plan.md
├── runbooks/
│   └── full-execution.md
├── scripts/
│   └── run_cleaning.py
├── src/danish_housing/
│   ├── __init__.py
│   ├── cleaning.py
│   └── kpis.py
└── tests/
    └── test_cleaning.py
```

## 6. Copiar tu notebook TB2

```bash
# Copia el notebook de TB2 a la carpeta notebook/
cp /ruta/a/TB2_Perfilado_Limpieza_Vilchez_Borasino_Ballon.ipynb notebook/TB2_perfilado_limpieza.ipynb
git add notebook/
git commit -m "docs: agregar notebook TB2 perfilado y limpieza"
git push
```
