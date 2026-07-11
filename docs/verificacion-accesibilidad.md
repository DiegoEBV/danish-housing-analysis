# Verificación de accesibilidad — `danish_housing_dashboard.html`

Evidencia de la validación de contraste, uso de color, etiquetas y títulos analíticos exigida
como criterio mínimo de aprobación (Entrega 6). Dashboard de una sola página (Chart.js +
Leaflet), sin alternancia de tema claro/oscuro: se verificó que no existe ningún `data-theme`,
`matchMedia` ni `localStorage` relacionado con tema — todo el CSS asume un único tema claro
(`--bg:#f4f6fb`, `--surface:#ffffff`), pero varios estilos de Chart.js (ticks `#8892aa`/`#94a3b8`,
varios acentos de badges) habían quedado configurados como si el fondo fuera oscuro. Esa
discrepancia es la causa raíz de la mayoría de fallos de contraste corregidos abajo.

## 1. Metodología

- **Contraste**: script Python (`contrast.py`, luminancia relativa y ratio WCAG estándar,
  con composición alfa manual para fondos `rgba(...)` traslúcidos) aplicado a cada par
  texto/fondo real extraído del CSS y de los estilos inline del HTML. Umbrales: 4.5:1 texto
  normal, 3:1 texto grande (≥24px o ≥18.66px negrita) y elementos gráficos no decorativos.
- **Daltonismo**: script Python (`cvd.py`) con matrices de aproximación lineal (Brettel/Viénot
  simplificadas) para protanopia y deuteranopia, aplicadas en sRGB a cada paleta categórica
  (`REGION_COLORS`, `TYPE_COLORS`, `PERIOD_COLORS`, `MODEL_COLORS`, `SEGMENT_COLORS`).
  Se calculó la distancia euclídea entre cada par de colores simulados; distancias <40 se
  marcaron como potencialmente confusas.
- **Verificación posterior**: se re-ejecutó el script de contraste sobre los 46 pares
  corregidos (todos en PASS) y `node --check` sobre el `<script>` extraído para confirmar que
  ningún cambio rompió la sintaxis JS. Se sirvió el HTML localmente (`python -m http.server`)
  y se confirmó una respuesta 200 sin errores de parseo (verificado también con
  `html.parser` de Python: 0 errores de anidamiento de etiquetas).

## 2. Contraste — pares corregidos (antes → después)

Todos verificados con el script; ratio "después" cumple el umbral aplicable.

| Elemento | Antes (ratio) | Después (ratio) | Umbral |
|---|---|---|---|
| KPI "Precio promedio/m²" | `#34d399` en blanco (1.92) | `#065f46` (7.68) | 3:1 (texto grande) |
| KPI "Peor drawdown" | `#f87171` en blanco (2.77) | `#b91c1c` (6.47) | 3:1 |
| KPI "Total transacciones" | `#60a5fa` en blanco (2.54) | `#1d4ed8` (6.70) | 3:1 |
| Badge "5 marts Gold" | `#2563eb` en `#e5effb` (4.45) | `#1d4ed8` (5.77) | 4.5:1 |
| Badge "4 regiones" | `#059669` en `#e3f5ea` (3.32) | `#065f46` (6.77) | 4.5:1 |
| `.delta-up` / `.badge-selected` | `#34d399` en tinte 12% (1.77) | `#065f46` en tinte 16% (5.92) | 4.5:1 |
| `.delta-neutral` | `#a78bfa` en tinte índigo (2.35, además desalineado de hue) | `#4338ca` en tinte 16% (6.06) | 4.5:1 |
| `.delta-down` / `.badge-discarded` | `#f87171` en tinte 12% (2.46) | `#b91c1c` en tinte 14% (5.08) | 4.5:1 |
| Tags H1/H2/H3 (encabezados de sección) | `var(--accent)` en tinte 15% (3.43) | `#4338ca` en tinte 18% (5.46) | 4.5:1 |
| Tag "✓ Soportada" | `#34d399` en tinte 10% (1.66) | `#065f46` en tinte 16% (5.54) | 4.5:1 |
| Tag "~ Refinada" | `#f59e0b` en tinte 10% (1.85) | `#92400e` en tinte 18% (4.95) | 4.5:1 |
| `.crisis-label` | `#f87171` en blanco (2.77) | `#b91c1c` (6.47) | 4.5:1 |
| `.ins-item-metric` | `#e11d48` (4.37) | `#be123c` (5.84) | 4.5:1 |
| `.synth-banner` | `#059669` (3.25) | `#065f46` (6.62) | 4.5:1 |
| `.takeaway-icon` ("→") | `var(--accent)` (4.15) | `#4338ca` (7.35) | 4.5:1 |
| `.ins-num`, flechas de acción | `#64748b` (4.42) | `#475569` (7.04) | 4.5:1 |
| Ejes de gráficos (ticks/leyendas Chart.js) | `#8892aa`/`#94a3b8` en tarjeta clara (2.56–3.12) | `#5b647a` (5.23–5.92) | 4.5:1 |
| "★ campeón" / nombre de modelo en tabla | `#f59e0b`/`MODEL_COLORS` en blanco (2.05–2.94) | `#92400e` y `MODEL_TEXT_COLORS` (6.70–7.68) | 4.5:1 |
| Etiquetas de evento macro en gráfico ("Lehman", "COVID"...) | paleta viva en fondo claro (~2.1–3) | variantes oscuras (6.47–7.68) | 4.5:1 |
| Nombre de tipología en checkboxes / small-multiples / tabla "Casos críticos" | `TYPE_COLORS` directo (2.60–4.06) | `TYPE_TEXT_COLORS` (4.84–9.15) | 4.5:1 |
| Nombre de región en "Comparativa por Región" | `REGION_COLORS` directo (2.15–4.47) | `REGION_TEXT_COLORS` (7.09–7.90) | 4.5:1 |
| Etiqueta de segmento (mapa/tabla de perfiles) | `#f97316`/`#9ca3af` (2.54–2.80) | `#c2410d`/`#6b7280` (4.83–5.18) | 4.5:1 |

**Total: 25 pares distintos fallaban → los 25 pasan tras el ajuste** (46 verificaciones
puntuales en total, incluyendo variantes por fondo, todas en PASS).

**Patrón de la corrección**: se añadieron variables/constantes de "color de texto" oscurecidas
(`--ok-text`, `--danger-text`, `--warn-text`, `--info-text`, `--accent-text` en CSS;
`TYPE_TEXT_COLORS`, `REGION_TEXT_COLORS`, `MODEL_TEXT_COLORS`, `SEGMENT_TEXT_COLORS` en JS) que
conviven con las paletas vivas originales. Las paletas vivas se conservan intactas para marcas
de gráfico (líneas, barras, relleno del mapa) — ahí el color siempre va acompañado de eje,
leyenda o tooltip redundante y no está sujeto al umbral de texto. Sólo se oscurece el color
cuando la misma paleta se reutiliza como **color de texto** sobre un fondo claro.

**Excepciones decorativas fuera de alcance**: `.hyp-badge`/`.hyp-supported`/`.hyp-refined`
(CSS definido pero sin ningún elemento del HTML que lo instancie actualmente — código muerto,
no se tocó) y el `bodyColor`/`titleColor` del tooltip de Chart.js, que ya pasaban porque su
propio fondo (`#1a1d27`) es oscuro y autocontenido (no depende del tema de la página).

## 3. Daltonismo (protanopia / deuteranopia)

Simulación matemática sobre las 5 paletas categóricas del dashboard. Pares con distancia
euclídea simulada <40 se consideran potencialmente confusos.

| Paleta | Par confuso detectado | Distancia antes | Corrección | Distancia después |
|---|---|---|---|---|
| `REGION_COLORS` | Zealand (índigo) vs. Fyn & islands (verde) | 31.4 (deuteranopia) | Fyn & islands `#34d399`→`#059669` | 104.6 |
| `TYPE_COLORS` | Villa (mostaza) vs. Townhouse (naranja) | 8.4–11.4 (ambos tipos) | Townhouse `#ea580c`→`#334155` (slate) | 61.5–62.7 |
| `PERIOD_COLORS` | Boom pre-crisis / GFC / Corrección 2022+ (cúmulo cálido ámbar-rojo-naranja) | 31.0–39.6 | Corrección 2022+ `#fb923c`→`#0f766e` (teal oscuro) | 98.2–217.1 |
| `MODEL_COLORS` | Ninguno (todas las distancias ≥48) | — | Sin cambios | — |
| `SEGMENT_COLORS` (azul/naranja del modo "Segmento riesgo-retorno") | Ninguno (ya diseñada para evitar rojo/verde, distancias ≥134) | — | Sin cambios | — |

El modo "Segmento riesgo-retorno" del mapa (azul `#2563eb` / naranja `#f97316` / gris
`#9ca3af` sin datos) ya estaba bien diseñado para daltonismo — se mantuvo sin cambios en el
mapa; sólo se introdujo `SEGMENT_TEXT_COLORS` para cuando esos mismos colores se usan como
texto (ver tabla de contraste).

Todas las paletas corregidas quedaron con distancia mínima ≥57.5 en ambos tipos de daltonismo
simulados. El único par que sigue por debajo de 60 y no se tocó es "Recuperación" vs.
"Boom 2015-2022" (41.4/54.5) en `PERIOD_COLORS`: se dejó así porque, a diferencia de los otros
casos, esos dos períodos también se distinguen por su posición temporal en el eje X del
scatter (H1), no sólo por color, y tocar más colores de esa paleta hubiese sido
sobre-corrección fuera del criterio mínimo pedido.

## 4. ARIA y semántica aplicados

- Navegación de pestañas: `role="tablist"` en el contenedor, `role="tab"` + `aria-selected`
  (actualizado dinámicamente en `switchTab()`) + `aria-controls` en cada botón; cada
  `.tab-section` recibió `role="tabpanel"`, `id="panel-*"`, `aria-labelledby` y `tabindex="0"`.
- `aria-label` descriptivo (con el hallazgo, no genérico) en los 10 `<canvas>` estáticos, en el
  canvas dinámico de cada small-multiple de volatilidad (incluye la tipología focal) y en el
  heatmap de drawdowns.
- `aria-label` en el contenedor del mapa Leaflet (`#choroMap`) y en los 4 `<select>`
  (modo/año del mapa, unidad del índice regional, orden del top de ciudades).
- `role="group"` + `aria-label` en el grupo de checkboxes de tipología (pestaña Crisis).
- Foco visible (`:focus-visible`) añadido para pestañas, selects y checkboxes — antes no había
  ningún estilo de foco distinto del default del navegador.
- Jerarquía de encabezados: había un solo `<h1>` y un solo `<h2>` (ambos en la pestaña
  Resumen); el resto de "encabezados" de pestaña eran `<div class="section-heading">` sin
  semántica. Se convirtieron a `<h2>` los 5 encabezados principales de Precios, Geografía,
  Crisis, Modelado y Conclusiones, y a `<h3>` el subtítulo "Decisiones de Visualización"
  (anidado bajo el `<h2>` de Conclusiones). `lang="es"` ya estaba presente en `<html>`.

## 5. Títulos y etiquetas analíticos revisados

Se reescribieron dos encabezados de pestaña que eran descriptivos en vez de afirmar el
hallazgo:

- Geografía: "Distribución Geográfica · Precio real/m² por Región y Ciudad" →
  **"Copenhague concentra el premio de precio: 2–3× por sobre Jutlandia, Fyn y Bornholm"**.
- Modelado: "Modelado Predictivo · Comparativa M1–M4" →
  **"XGBoost reduce el error de predicción frente al baseline lineal · Comparativa M1–M4"**.

El resto de gráficos ya declaraban el hallazgo en su título o en el `takeaway` inmediato
(p. ej. "Copenhague muestra respuesta más amortiguada...", "Zealand más que duplicó su
índice..."), y los ejes ya mostraban unidades explícitas vía `callback` de Chart.js (DKK/m²,
%, k transacciones) o título de eje (`chartScatter`, `chartBubble`, `chartPredScatter`); no se
tocaron por no ser genéricos.

## 6. Fuera de alcance

- Prueba con lector de pantalla real (NVDA/VoiceOver/JAWS) — sólo se verificó la semántica
  ARIA estáticamente, no el comportamiento de anuncio real.
- `role="img"` en el contenedor de Leaflet (`#choroMap`) es una simplificación: el mapa
  contiene controles interactivos reales (zoom, capa de ciudades) que un lector de pantalla
  seguirá exponiendo dentro de la región; una implementación completa requeriría un patrón
  ARIA más elaborado (p. ej. `application` + descripciones vivas por hover), fuera del
  alcance del criterio mínimo de esta entrega.
- No se auditó el HTML de la rama `visualization`/GitHub Pages por separado; los cambios se
  hicieron sobre `danish_housing_dashboard.html` en la rama de trabajo actual
  (`fix-netlify-paths`) y deben replicarse si existe una copia divergente para GitHub Pages.
- No se implementó alternancia de tema claro/oscuro (el dashboard nunca la tuvo) — la
  verificación asumió un único tema claro, que es el real.

## 7. Scripts de verificación

Los scripts usados (`contrast.py`, `cvd.py`) son utilitarios de una sola sesión y no se
commitearon al repo (viven en el scratchpad de la sesión). Reproducir la metodología: extraer
pares color-texto/fondo del CSS/inline styles y aplicar la fórmula de luminancia relativa WCAG
2.1 §1.4.3, y para daltonismo aplicar una matriz de simulación lineal de protanopia/
deuteranopia sobre cada paleta categórica declarada en el `<script>` del dashboard
(`REGION_COLORS`, `TYPE_COLORS`, `PERIOD_COLORS`, `MODEL_COLORS`, `SEGMENT_COLORS`).
