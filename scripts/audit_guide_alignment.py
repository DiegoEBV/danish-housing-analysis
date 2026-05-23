#!/usr/bin/env python3
"""
Validate that examen/examen_respuestas.html is aligned with the style guidelines
extracted from the converted guide Markdown.

Checks whether each exam case implements (or explicitly addresses) the key rules
mentioned in the guide. Outputs a structured report to stdout.

Usage:
    python scripts/audit_guide_alignment.py
    python scripts/audit_guide_alignment.py --guide examen/guia/semana-07-seleccion-y-calculos.md
    python scripts/audit_guide_alignment.py --html examen/examen_respuestas.html
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GUIDE = ROOT / "examen/guia/semana-07-seleccion-y-calculos.md"
DEFAULT_HTML = ROOT / "examen/examen_respuestas.html"


# ── rule definitions ────────────────────────────────────────────────────────

@dataclass
class Rule:
    """A style rule extracted from the guide, with evidence pointers."""
    id: str
    description: str
    guide_keywords: list[str]       # phrases from guide that support this rule
    html_must_contain: list[str]    # strings/patterns the HTML must contain (any)
    html_must_not_contain: list[str] = field(default_factory=list)  # forbidden patterns
    case: str = ""                  # "c1"…"c5" or "" for global
    search_js: bool = False         # True = search full HTML (including JS), not just panel div
    guide_optional: bool = False    # True = skip guide-evidence warning (concept from another week)


RULES: list[Rule] = [
    # ── Case 1 — ONPE pie chart ──────────────────────────────────────────────
    Rule(
        id="C1-pie-denominador",
        description="C1: Identifica que el pie mezcla denominadores distintos (votos válidos vs emitidos)",
        guide_keywords=["denominador", "pie", "votos válidos", "votos emitidos"],
        html_must_contain=["denominador", "votos válidos", "votos emitidos"],
        case="c1",
    ),
    Rule(
        id="C1-otros-visible",
        description="C1: La categoría 'Otros' debe ser visible en el gráfico alternativo",
        guide_keywords=["pie", "otras categorías"],
        html_must_contain=["Otros"],
        case="c1",
    ),
    Rule(
        id="C1-alternativa-barras",
        description="C1: La alternativa usa barras horizontales (no pie) para comparar proporciones",
        guide_keywords=["Barras (longitud + posición) baten al pie (ángulo)",
                        "barras baten al pie"],
        html_must_contain=["bar"],          # Chart.js type='bar' or type=bar
        html_must_not_contain=[],
        case="c1",
    ),
    # ── Case 2 — Mesas 900001 dual axis ──────────────────────────────────────
    Rule(
        id="C2-no-dual-axis",
        description="C2: Rechaza el doble eje y usa escala única",
        guide_keywords=[
            '"comparación" de dos métricas con escalas diferentes en el mismo eje (dual axis)',
            "dual axis",
            "dual axis con tendencias opuestas",
        ],
        # HTML uses Spanish "doble eje"; guide mentions "dual axis"
        html_must_contain=["doble eje"],
        html_must_not_contain=[],
        case="c2",
    ),
    Rule(
        id="C2-eje-desde-cero",
        description="C2: El eje Y de la alternativa comienza en 0 (beginAtZero: true en Chart.js)",
        guide_keywords=["iniciar en 0", "eje y truncado sin avisar", "Eje desde cero"],
        html_must_contain=["beginAtZero: true"],
        case="c2",
        search_js=True,  # Chart.js options live in global <script>, not inside the panel div
    ),
    Rule(
        id="C2-scope-anotado",
        description="C2: El ámbito (Nacional vs Circunscripción) está explícito en el gráfico",
        guide_keywords=["granularidad", "scope"],
        html_must_contain=["Nacional", "Circunscripción"],
        case="c2",
    ),
    # ── Case 3 — Pobreza-voto ecological fallacy ─────────────────────────────
    Rule(
        id="C3-scatter-district",
        description="C3: Usa scatter/bubble a nivel distrital, no departamental",
        guide_keywords=["Permite ver outliers, clusters y no linealidad", "dispersión"],
        html_must_contain=["scatter", "distrito"],
        case="c3",
    ),
    Rule(
        id="C3-no-causal-headline",
        description="C3: El titular no afirma causalidad pobreza→voto; menciona falacia ecológica",
        guide_keywords=["falacia ecológica"],
        html_must_not_contain=["determina el voto", "causa el voto"],
        html_must_contain=["falacia ecológica"],
        case="c3",
        guide_optional=True,  # concepto de semana 6, no cubierto en semana-07
    ),
    Rule(
        id="C3-tipo-area-segmentado",
        description="C3: El scatter segmenta por tipo_area (rural/urbano/periurbano)",
        guide_keywords=["codificación visual", "color"],
        html_must_contain=["tipo_area", "rural"],
        case="c3",
    ),
    # ── Case 4 — Obras paralizadas normalización ──────────────────────────────
    Rule(
        id="C4-metrica-normalizada",
        description="C4: Usa monto_por_obra (normalizado) como métrica principal, no monto bruto",
        guide_keywords=["mapas requieren cartograma o normalización",
                        "normalizar", "Buenas decisiones aumentan el numerador y reducen el denominador"],
        html_must_contain=["monto_por_obra"],
        case="c4",
    ),
    Rule(
        id="C4-outlier-identificado",
        description="C4: Identifica y discute la sensibilidad a outliers del monto bruto",
        guide_keywords=["outlier", "Permite ver outliers"],
        html_must_contain=["outlier"],
        case="c4",
    ),
    # ── Case 5 — DWH modeling ─────────────────────────────────────────────────
    Rule(
        id="C5-estrella-snowflake",
        description="C5: Presenta modelo estrella y copo de nieve con fact grain y claves",
        guide_keywords=[],  # guide doesn't cover DWH modeling directly
        html_must_contain=["fact_mesa", "estrella", "copo de nieve"],
        case="c5",
    ),
    Rule(
        id="C5-cardinalidad",
        description="C5: Incluye verificación de cardinalidad (fan trap / exploding joins)",
        guide_keywords=[],
        html_must_contain=["cardinalidad", "fan trap"],
        case="c5",
    ),
    # ── Global Tufte / style rules ─────────────────────────────────────────────
    Rule(
        id="GLOBAL-no-3d",
        description="GLOBAL: No usa gráficos 3D (chartjunk puro)",
        guide_keywords=["3D innecesario: chartjunk puro", "gráficos 3D que no representan tres dimensiones reales"],
        html_must_not_contain=["3d", "3D"],
        html_must_contain=[],
        case="",
    ),
    Rule(
        id="GLOBAL-no-rainbow",
        description="GLOBAL: No usa paleta rainbow (accesibilidad / daltonismo)",
        guide_keywords=["daltonismo", "rainbow"],
        html_must_not_contain=["rainbow", "hsl("],
        html_must_contain=[],
        case="",
    ),
]


# ── checker ─────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    rule_id: str
    status: str      # "PASS" | "FAIL" | "WARN"
    detail: str


def _panel_html(html: str, case: str) -> str:
    """Extract the HTML fragment for a specific tab panel."""
    if not case:
        return html
    m = re.search(
        rf'id="panel-{re.escape(case)}"(.*?)(?=id="panel-c[1-5]"|</body>)',
        html, re.DOTALL | re.IGNORECASE,
    )
    return m.group(0) if m else html


def _check_rule(rule: Rule, html: str, guide_md: str) -> Finding:
    # For JS-level checks use full HTML; otherwise scope to the tab panel
    scope = html if rule.search_js else _panel_html(html, rule.case)
    scope_lower = scope.lower()

    missing_must = [
        p for p in rule.html_must_contain
        if p.lower() not in scope_lower
    ]
    found_forbidden = [
        p for p in rule.html_must_not_contain
        if p.lower() in scope_lower
    ]

    if missing_must:
        return Finding(rule.id, "FAIL",
                       f"Missing in HTML: {missing_must}")
    if found_forbidden:
        return Finding(rule.id, "FAIL",
                       f"Forbidden content found: {found_forbidden}")

    # Verify guide actually supports this rule (skip if guide_optional)
    if rule.guide_keywords and not rule.guide_optional:
        guide_supported = any(
            kw.lower() in guide_md.lower() for kw in rule.guide_keywords
        )
        if not guide_supported:
            return Finding(rule.id, "WARN",
                           "Rule not found in guide — check keyword alignment")

    return Finding(rule.id, "PASS", rule.description)


# ── report ──────────────────────────────────────────────────────────────────

def run_audit(guide_path: Path, html_path: Path) -> int:
    if not guide_path.exists():
        print(f"Guide not found: {guide_path}")
        print("Run: python scripts/convert_guide_to_md.py examen/guia/semana-07-seleccion-y-calculos.pdf")
        return 1
    if not html_path.exists():
        print(f"HTML not found: {html_path}")
        return 1

    guide_md = guide_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")

    findings: list[Finding] = [_check_rule(r, html, guide_md) for r in RULES]

    passes = [f for f in findings if f.status == "PASS"]
    warns  = [f for f in findings if f.status == "WARN"]
    fails  = [f for f in findings if f.status == "FAIL"]

    print("=" * 72)
    print("ALIGNMENT AUDIT — examen vs guide")
    print(f"Guide : {guide_path.relative_to(ROOT)}")
    print(f"HTML  : {html_path.relative_to(ROOT)}")
    print("=" * 72)

    if fails:
        print("\n🔴 FAILS")
        for f in fails:
            print(f"  [{f.rule_id}] {RULES[[r.id for r in RULES].index(f.rule_id)].description}")
            print(f"    → {f.detail}")

    if warns:
        print("\n🟡 WARNINGS")
        for f in warns:
            print(f"  [{f.rule_id}] {f.detail}")

    if passes:
        print(f"\n🟢 PASSES ({len(passes)}/{len(findings)})")
        for f in passes:
            print(f"  [{f.rule_id}]")

    print("\n" + "=" * 72)
    print(f"Result: {len(passes)} pass · {len(warns)} warn · {len(fails)} fail")
    print("=" * 72)

    return 1 if fails else 0


def main(argv: list[str] = sys.argv[1:]) -> int:
    guide = DEFAULT_GUIDE
    html = DEFAULT_HTML

    if "--guide" in argv:
        guide = Path(argv[argv.index("--guide") + 1])
    if "--html" in argv:
        html = Path(argv[argv.index("--html") + 1])

    return run_audit(guide, html)


if __name__ == "__main__":
    raise SystemExit(main())
