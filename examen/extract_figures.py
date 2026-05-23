"""
extract_figures.py — Extrae las figuras de los gráficos malos del PDF del examen.
Fuente: examen-parcial-semanas-1-7.pdf (páginas 3, 5, 7, 9, 12)
Salida: examen/figures/casoN_grafico_mal_hecho.png
"""
from pathlib import Path
import fitz

PDF = Path(__file__).parent / "examen-parcial-semanas-1-7.pdf"
OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

FIGURAS = [
    (2,  "caso1_grafico_mal_hecho.png"),
    (4,  "caso2_grafico_mal_hecho.png"),
    (6,  "caso3_grafico_mal_hecho.png"),
    (8,  "caso4_grafico_mal_hecho.png"),
    (11, "caso5_modelado_modelos_posibles.png"),
]

doc = fitz.open(PDF)
for page_idx, filename in FIGURAS:
    imgs = doc[page_idx].get_images(full=True)
    if not imgs:
        print(f"⚠ Página {page_idx+1}: sin imágenes embebidas")
        continue
    xref = imgs[0][0]
    img = doc.extract_image(xref)
    dest = OUT / filename
    dest.write_bytes(img["image"])
    print(f"✓ {filename}  ({img['width']}×{img['height']} px, {len(img['image'])//1024} KB)")

doc.close()
print(f"\nFiguras en: {OUT}/")
