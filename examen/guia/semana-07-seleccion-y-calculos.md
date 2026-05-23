# Data Visualization — Semana 7 — Selección de gráficos y cálculos analíticos — Cómo elegir el gráfico correcto y cómo cal


---

<!-- slide 1 -->
### Data Visualization
Semana 7 — Selección de gráficos y cálculos analíticos
Cómo elegir el gráfico correcto y cómo calcular las métricas que muestra
UPC · Curso de Visualización de Datos

---

<!-- slide 2 -->
### Meta de aprendizaje
Al cerrar la sesión, el estudiante puede:
Selección visual
Justificar la elección de un gráfico a partir de la pregunta analítica, no del catálogo de Tableau.
Aplicar principios de Tufte: data-ink ratio, chartjunk y lie factor.
Reconocer cuándo un gráfico tradicional (pie, dual axis, 3D, rainbow) mete ruido en la lectura.
Cálculos analíticos
Distinguir formalmente entre cálculo a nivel de fila y cálculo agregado.
Diseñar campos calculados, parámetros y table calculations.
Resolver problemas de granularidad con LOD ( FIXED , INCLUDE , EXCLUDE ).
Justificar el nivel semántico en el que se computa cada métrica.

---

<!-- slide 3 -->
### Mapa de la clase (4 horas)
Bloque A · Selección visual (1h45)
1. Taxonomía pregunta → gráfico y árbol de decisión.
2. Galería con guía de uso (barras, líneas, dispersión, distribución, jerarquía, mapas).
3. Fundamentos de Tufte: data-ink, chartjunk, lie factor, sparklines.
4. Codificaciones visuales (Cleveland / Mackinlay).
5. Errores frecuentes en gráficos.
6. Accesibilidad, daltonismo y chartjunk real.
7. Marco práctico y checklist.
8. Ejemplos icónicos: Minard, Snow.
9. Implementación en Tableau.
Bloque B · Cálculos analíticos (1h45)
10. Row-level vs aggregate. Campos calculados.
11. Parámetros y patrón parameter swap.
12 Table calculations LOD ( FIXED
INCLUDE
EXCLUDE )

---

<!-- slide 4 -->
### Flujo de la sesión
Pregunta
analítica
Estructura
del dato
Codiﬁcación
visual
Tipo de
gráﬁco
Revisión
de errores
Decisión
defendible
Dos preguntas directrices, una misma sesión:
A: ¿Qué gráfico hace que la verdad del dato sea inmediatamente legible?
B: ¿En qué nivel semántico se computa la métrica que ese gráfico va a mostrar?

---

<!-- slide 5 -->
### Apertura
"Above all else show the data." — Tufte
Mathias: "El dashboard tiene 12 gráficos y dice que el margen subió 8%."
Yunguri: "¿Cuántos de esos 12 responden la pregunta del decisor? Y ese 8%, ¿es promedio de promedios o
sobre los agregados?"
Mathias: "..."
Takeaway doble: un gráfico se elige por la pregunta; una métrica se define por su nivel. Cualquier sesión seria de
visualización junta ambas decisiones.

---

<!-- slide 6 -->
## Parte 1 · ¿Qué pregunta intentas responder?
La pregunta dicta el gráfico
La taxonomía clásica funciona si se respeta este orden:
1. Formular la pregunta en lenguaje natural.
2. Identificar la estructura del dato (categórico, numérico, temporal, geográfico).
3. Elegir la codificación visual (posición, longitud, ángulo, área, color).
4. Elegir el gráfico.
Cambiar este orden produce dashboards bonitos que no responden nada.

---

<!-- slide 7 -->
### Pregunta → gráfico recomendado
Pregunta típica
Estructura del dato
Gráfico recomendado
Trampa frecuente
¿Cuál es mayor?
categórico → numérico
barra horizontal ordenada
usar pie con muchas categorías
¿Cómo cambió en el tiempo?
tiempo → numérico
línea, sparkline
barras con 30 puntos
¿Cómo se distribuye?
numérico
histograma, boxplot, strip
reportar solo la media
¿Qué relación hay entre A y B?
numérico × numérico
dispersión
dual axis "trends"
¿Cómo se compone el total?
categórico → proporción
barra apilada, waffle
pie de 8 slices
¿Qué difiere entre subgrupos?
dimensión adicional
pequeños múltiplos
spaghetti chart
¿Dónde ocurre?
geográfico
mapa coroplético, dot map
mapa sin proyección consciente
¿Cómo se jerarquiza?
árbol
treemap, sunburst (con cuidado)
sunburst de 5 niveles

---

<!-- slide 8 -->
### Árbol de decisión rápido
¿Qué pregunta quieres responder?
Comparar
Cambio / tiempo
Relación / distribución
Pocas categorías
Barra horizontal
Muchas categorías
Dot plot ordenado
Serie larga
Línea / sparkline
Dos puntos
Slope graph
Numéricas
Dispersión
Una variable
Hist. + box
¿Hay subgrupos?
Usa pequeños múltiplos
¿Eje truncado?
Decláralo en el título
¿>7 series en un eje?
Separa o agrega
Regla por defecto: si dudas, elige el gráﬁco más simple que conserve la verdad del dato.
Regla por defecto: si dudas, elige el gráfico más simple que conserve la verdad del dato.

---

<!-- slide 9 -->
## Parte 2 · Galería con guía de uso
Barras: cuándo sí
Comparar magnitudes entre pocas categorías (4 a 20).
Categorías ordenadas por valor, no por alfabeto.
Eje empezando en cero.
Etiquetas directas mejor que leyenda.
Cuándo no:
series temporales largas (usar línea)
proporciones de un total con muchas categorías (usar dot plot o barra ordenada)
categorías sin orden natural y con valores casi iguales

---

<!-- slide 10 -->
### Pie vs barras ordenadas
A
B
C
D
E
F
G
H
Pie chart con muchas categorías
Participación (%)
H
G
F
E
D
C
B
A
6%
8%
9%
11%
12%
14%
18%
22%
Barras ordenadas, etiquetadas y comparables
Misma composición, distinta facilidad de lectura
Pie chart funciona cuando hay ≤ 3 categorías y se quiere remarcar "parte de un todo". Para todo lo demás, una
barra horizontal ordenada gana en lectura.

---

<!-- slide 11 -->
### Líneas y serie temporal
Usar línea cuando:
el eje horizontal es continuo (tiempo, dosis, frecuencia)
existe al menos una decena de puntos
importa la dirección del movimiento
Cuándo no:
comparación de categorías sin orden natural
"comparación" de dos métricas con escalas diferentes en el mismo eje (dual axis)

---

<!-- slide 12 -->
### Slope graph para "antes vs después"
2023
2025
Ingeniería 18
32 Ingeniería
Ventas 24
27 Ventas
Operaciones 21
19 Operaciones
Soporte 11
23 Soporte
Marketing 14
12 Marketing
Slope graph: foco en dirección y magnitud del cambio
Cuando solo importan dos puntos en el tiempo, el slope graph supera tanto a las barras como a la línea. Codifica
dirección, magnitud y ranking en una sola lectura.

---

<!-- slide 13 -->
### Distribuciones
Una sola media oculta forma, sesgo y multimodalidad.
Casi normal
media
mediana
Bimodal
Sesgada a la derecha
Distribuciones: el promedio solo no basta
Reglas:
histograma para forma global
boxplot para comparar varios grupos
strip / jitter para mostrar cada observación
violin cuando el detalle de la densidad importa

---

<!-- slide 14 -->
### Relación entre dos numéricas
Dispersión ( scatter plot ) es la opción por defecto.
Más informativa que un coeficiente de correlación solo.
Permite ver outliers, clusters y no linealidad.
Agregar línea de tendencia con criterio, no por hábito.
La correlación numérica miente cuando la forma no es lineal. Lo demuestra el cuarteto de Anscombe.

---

<!-- slide 15 -->
### Cuarteto de Anscombe
Conjunto I
Conjunto II
Conjunto III
Conjunto IV
#### Cuarteto de Anscombe — mismas estadísticas, distinta historia
ȳ ≈ 7.5 • x̄ = 9 • r ≈ 0.82 • pendiente ≈ 0.5 para los cuatro conjuntos
Cuatro datasets con mismas estadísticas resumen, formas radicalmente distintas. Lección: mirar el gráfico es
parte de la estadística.

---

<!-- slide 16 -->
### Jerarquía y composición
Para mostrar partes anidadas:
treemap funciona con jerarquías de 2 niveles
stacked bar funciona si el orden de las series es estable
sunburst suele ser bonito y poco legible más allá de 3 anillos
icon array / waffle funciona para proporciones humanas (1 de cada 8 personas...)
Regla práctica: si el área es la codificación principal, comparar áreas pequeñas es difícil. Reservar para totales y
ballpark.

---

<!-- slide 17 -->
### Mapas
Un mapa solo se justifica cuando la geografía es la pregunta, no el adorno.
Coroplético: variable continua por región. Cuidar tamaños desiguales (Lima vs Madre de Dios).
Punto/dot map: ubicación de eventos puntuales.
Cartograma: corrige áreas según el dato (población, votos).
Hex bin / símbolo proporcional: cuando el detalle por región no aporta.
Sin proyección consciente, los mapas mienten: la mayor parte del color tapa la mayor parte del área, no la mayor
parte del dato.

---

<!-- slide 18 -->
## Parte 3 · Fundamentos de Tufte
Pregunta operativa
á
Tres axiomas operativos:
1. Mostrar el dato, no la decoración.
2. La proporción visual debe respetar la proporción numérica.
3. La comparación se diseña, no se delega al lector.

---

<!-- slide 19 -->
### Data-ink ratio
Tufte define:
á
Buenas decisiones aumentan el numerador y reducen el denominador.
Tinta que no es dato:
bordes pesados, sombras y 3D
cuadrículas densas
fondos coloreados
leyendas redundantes
texturas y degradados decorativos

---

<!-- slide 20 -->
### Data-ink: mismo dato, dos relaciones
Ene
Feb
Mar
Abr
May
Jun
Mes
Ventas (miles)
Mucha tinta, poca información
Ene
Feb
Mar
Abr
May
Jun
Ventas mensuales, en miles
Tinta dedicada al dato
Mismo dato, dos relaciones de tinta
A la derecha, eliminar bordes, fondo y cuadrícula no pierde información; concentra atención en la diferencia entre
barras.

---

<!-- slide 21 -->
### Chartjunk
Tufte llama chartjunk a cualquier elemento gráfico que:
no aporta a la lectura del dato,
compite con el dato por la atención,
o introduce distorsión perceptual.
Sospechosos habituales:
gráficos 3D que no representan tres dimensiones reales
íconos decorativos que escalan diferente al dato
sombras, biseles, gradientes
texturas tipo moiré
Regla práctica: si lo borras y la historia no cambia, sobraba.

---

<!-- slide 22 -->
### Lie factor
Para un gráfico:
ñ
á
ñ
Idealmente:
Cuando el lie factor crece, el lector "ve" un efecto mayor que el real. Cuando se acerca a cero, ve menos del que
hay.

---

<!-- slide 23 -->
### Lie factor: el eje truncado
Antes
Después
Índice
lie factor ≫ 1
Eje truncado: +3% parece +300%
Antes
Después
Índice
lie factor ≈ 1
Eje desde cero: cambio real visible
El mismo aumento de 3 puntos contado dos veces
Una diferencia de 3 puntos se ve como un salto enorme si el eje no parte de cero sin avisar.
Aceptable solo cuando el dominio del dato exige zoom (señales casi constantes, intervalos), declarando la
decisión en el título o anotación.

---

<!-- slide 24 -->
### Pequeños múltiplos
Tufte: small multiples son la respuesta a "muchas series, un solo eje".
mismo tipo de gráfico
misma escala
misma codificación
repetido para cada subgrupo
El ojo escanea diferencias entre paneles, no entre colores.

---

<!-- slide 25 -->
### Pequeños múltiplos en acción
Perú
Colombia
Chile
México
Argentina
Ecuador
Brasil
Uruguay
Bolivia
Pequeños múltiplos: misma escala, mismo eje, ojo escanea diferencias
Reemplazan al spaghetti chart cuando hay más de 5 a 7 series.

---

<!-- slide 26 -->
### Sparklines
Sparkline: gráfico del tamaño de una palabra, sin ejes ni leyenda, embebido junto al número.
entrega contexto temporal al lado del valor
no compite con el dashboard, lo enriquece
ideal en tablas, KPIs y reportes ejecutivos

---

<!-- slide 27 -->
### Sparklines integrados a una tabla
NPS
+98% vs. año anterior
Churn mensual
+91% vs. año anterior
Usuarios activos
+112% vs. año anterior
Ingresos
+104% vs. año anterior
Sparklines: gráﬁcos del tamaño de una palabra dentro de la tabla
El sparkline contesta "¿qué pasó antes?" sin pedir un slide aparte.

---

<!-- slide 28 -->
## Parte 4 · Codificaciones visuales
Cleveland & McGill / Mackinlay
No todas las codificaciones son igualmente legibles. Cleveland y McGill (1984) demostraron experimentalmente
que el ojo humano lee con distinta precisión cada codificación visual cuantitativa.
Mackinlay (1986) sistematizó la jerarquía para diseño automático de gráficos.
La regla que de allí se deriva:
Para comparar magnitudes numéricas, usar la codificación más alta de la jerarquía que la pregunta permita.

---

<!-- slide 29 -->
### Jerarquía de precisión perceptual
Posición en escala común
→
barras alineadas, dot plots
más preciso
Posición en escalas no alineadas
→
small multiples no alineados
Longitud
→
barras apiladas, tree rectangles
Ángulo / pendiente
→
pie chart, slope graph
Área
→
burbujas, treemap
Volumen / curvatura
→
gráﬁcos 3D
Saturación / sombreado
→
heatmap monocromo
Tono (hue) de color
→
categorías cualitativas
menos preciso
#### precisión perceptual
Cleveland & McGill (1984), Mackinlay (1986): qué codiﬁcaciones lee mejor el ojo humano
Consecuencia operativa:
Barras (longitud + posición) baten al pie (ángulo).
Dot plots baten a treemaps cuando hay que comparar valores cercanos.
Color solo se usa dentro de un eje de posición, no como sustituto.

---

<!-- slide 30 -->
### Codificaciones por tipo de dato
Tipo de variable
Codificación más precisa
Codificación aceptable
A evitar
Cuantitativa
posición, longitud
ángulo (slope), área (gran escala)
color hue, volumen, 3D
Ordinal
posición, saturación
longitud, ángulo
color hue puro
Nominal (categórica)
color hue, forma
textura
longitud, posición sin orden
Lección: el dato cuantitativo merece longitud o posición. El dato nominal puede usar color. Mezclar codificaciones
invierte la lectura.

---

<!-- slide 31 -->
## Parte 5 · Errores frecuentes en gráficos
Catálogo de errores que vamos a evitar
1. Eje y truncado sin avisar.
2. Gráficos 3D sin necesidad.
3. Dual axis invitando a inferir causalidad.
4. Escala de color rainbow (jet).
5. Pie chart con muchas categorías.
6. Spaghetti chart con > 7 series.
7. Diámetro en lugar de área para burbujas.
8. Series temporales largas con barras.
9. Demasiadas decoraciones, sombras y biseles.
10. Etiquetar todo y no resaltar nada.

---

<!-- slide 32 -->
### Error · Dual axis
2010
2012
2014
2016
2018
2020
2022
17.5
20.0
22.5
25.0
27.5
30.0
32.5
35.0
37.5
Películas de Nicolas Cage
Dual axis: invita a inferir causalidad espuria
12.5
15.0
17.5
20.0
22.5
25.0
27.5
30.0
Ahogamientos en piscinas
Dos ejes con escalas diferentes invitan al lector a inferir correlación o causalidad donde no necesariamente las
hay. Alternativas: pequeños múltiplos, ratio explícito o un único eje normalizado.

---

<!-- slide 33 -->
### Error · Rainbow color scale
Rainbow (jet): saltos perceptuales
Viridis: perceptualmente uniforme
−10.0
−7.5
−5.0
−2.5
0.0
2.5
5.0
7.5
−10.0
−7.5
−5.0
−2.5
0.0
2.5
5.0
7.5
La escala de color es una decisión analítica
jet  introduce bandas perceptuales que no existen en el dato. Para variables continuas, usar paletas
perceptualmente uniformes ( viridis , cividis , magma ). Para datos divergentes, usar paletas simétricas
( RdBu , BrBG ) con centro en cero.

---

<!-- slide 34 -->
### Error · Spaghetti chart
12 series en un solo eje: el ojo se pierde
S1
S2
S3
S4
S5
S6
S7
S8
S9
S10
S11
S12
Mismas series como pequeños múltiplos
Más de 5 a 7 líneas en un mismo eje vencen al ojo. Solución: pequeños múltiplos, o destacar 1 serie de interés y
dejar las demás como contexto en gris.

---

<!-- slide 35 -->
### Error · Área vs diámetro en burbujas
Diámetro escalado al valor: 4× se ve 16×
Área escalada al valor: 4× se ve 4×
Burbujas: el cerebro lee el área, no el diámetro
El cerebro lee área. Si la herramienta escala diámetro, una proporción de 4× se ve como 16×. Verificar siempre
que la codificación de tamaño esté en términos de área.

---

<!-- slide 36 -->
### Tabla de antídotos
Error
Síntoma
Antídoto
Eje y truncado
un cambio del 2% parece del 200%
iniciar en 0 o anotar el truncamiento
Gráfico 3D
barras o pies en perspectiva
versión 2D directa
Dual axis
dos eje y con escalas distintas
pequeños múltiplos o ratio
Rainbow
jet/hsv para variable continua
viridis , cividis , magma
Pie con > 5 slices
imposible comparar slices similares
barra horizontal ordenada
Spaghetti
> 7 series en un eje
pequeños múltiplos o resaltar 1
Diámetro burbuja
proporción visual incorrecta
área proporcional al valor
Barras para tiempo
24 barras anuales en fila
línea o sparkline
Chartjunk
sombras, biseles, gradientes
retirar y volver a leer

---

<!-- slide 37 -->
## Parte 6 · Accesibilidad y chartjunk real
¿Por qué este bloque tiene su propia parte?
Color y chartjunk no son "errores cosméticos". Son fallas de accesibilidad y de honestidad analítica que
excluyen lectores o tergiversan resultados.
Esta parte agrupa:
accesibilidad para personas con daltonismo
paletas seguras
ejemplos reales de chartjunk publicados
casos famosos que vale la pena estudiar

---

<!-- slide 38 -->
### Accesibilidad: el color también es semántica
Aproximadamente 8% de los hombres y 0.5% de las mujeres tienen alguna forma de daltonismo. Las dos más
frecuentes son deuteranopia y protanopia, ambas en el eje rojo–verde.
Implicaciones para tus dashboards:
Evitar rojo y verde como única distinción entre "bueno" y "malo".
Acompañar el color con otra codificación: forma, textura, etiqueta directa.
Probar la paleta en escala de grises y con un simulador de daltonismo.

---

<!-- slide 39 -->
### Paletas seguras
A
B
C
D
Rojo–verde (riesgoso)
Visión típica
A
B
C
D
Deuteranopia (~6% hombres)
A
B
C
D
Protanopia (~1%)
A
B
C
D
Okabe–Ito (segura)
A
B
C
D
A
B
C
D
El mismo gráﬁco, percibido por tres ojos distintos
Paletas probadas para daltonismo:
Okabe & Ito (2008): 8 colores diseñados para deuteranopia/protanopia.
Wong (2011, Nature Methods): 7 colores para series científicas.
En Tableau: usar "Color Blind 10".
En matplotlib/seaborn: colorblind  palette.
Regla: el color no debe ser nunca el único portador de información crítica.

---

<!-- slide 40 -->
### Chartjunk en estado salvaje
2019
2020
2021
2022
2023
$40M
$38M
$55M
$70M
$92M
★ Best year ever ★
PROFITS ROCKETING UP!!!
2019
2020
2021
2022
2023
Eje desde cero, sin chartjunk, conclusión en el título
$40M
$38M
$55M
$70M
$92M
In g re s o s  a n u a le s
9 2 M e n  2 0 2 3
— 40
2019
Me n
#### a
#### Chartjunk en estado salvaje vs. rediseño Tufte
Defectos identificables en el original:
fondo coloreado sin función analítica
3D / sombras que distorsionan la lectura
título emocional que dicta la conclusión antes del dato
adornos ("★ Best year ever ★") tipográficos
eje y truncado para amplificar el crecimiento
C d
l li f
l h
#### j
k El
di
ñ
#### l
i
i f
ió
i
i
#### d
ió

---

<!-- slide 41 -->
### Casos famosos de chartjunk
#### Caso
Error principal
Lección
Fox News "Bush tax cut" (2012)
barras alineadas que omiten la base 0
el eje truncado es la trampa más usada en medios
USA Today "hammer charts"
íconos 3D con escala incierta
si el ícono cambia de tamaño, su área debe cumplir la
regla
Pie 3D de Microsoft Excel
ángulo + perspectiva
los slices del frente parecen más grandes
Mapas coropléticos por estado USA
Alaska domina visualmente con 0.7M
habitantes
mapas requieren cartograma o normalización
The Economist mismas-escalas
(2019)
dual axis con tendencias opuestas
la correlación visual no es estadística
Todos estos casos están disponibles online. Pedirles a los estudiantes que los busquen y diagnostiquen es buen
ejercicio.

---

<!-- slide 42 -->
## Parte 7 · Marco práctico
Checklist de revisión pre-publicación
1. ¿La pregunta que responde el gráfico está escrita en el título?
2. ¿La codificación principal es posición o longitud (lo más preciso) y no área o ángulo?
3. ¿El eje y empieza en cero? Si no, ¿está anotado?
4. ¿El color codifica algo, o es decoración?
5. ¿Las etiquetas están directamente sobre los datos, no en una leyenda lejana?
6. ¿Se puede leer en blanco y negro sin perder la historia?
7. Si se borran los elementos decorativos, ¿queda intacto el dato?
Si fallan dos o más, rediseñar, no maquillar.

---

<!-- slide 43 -->
### Heurísticas tipo Tufte
"Mostrar el dato" suele ser un boceto antes del software.
Cada decisión gráfica es una hipótesis sobre cómo el lector va a comparar.
Un buen gráfico resiste el zoom: lo importante se ve a 5 metros, el detalle al acercarse.
El gráfico más útil rara vez es el más nuevo.
"Graphical excellence is that which gives to the viewer the greatest number of ideas in the shortest time with
the least ink in the smallest space." — Tufte

---

<!-- slide 44 -->
## Parte 8 · Ejemplos icónicos
Cuando la visualización resolvió un problema real
Tres láminas que cualquier curso serio de visualización vuelve a mostrar:
Minard: la economía de información de toda una campaña militar en una sola figura.
Snow: visualización al servicio de una hipótesis verificable.
Challenger: cómo un gráfico mal ordenado ocultó una correlación crítica.
Los tres están disponibles online en alta resolución.

---

<!-- slide 45 -->
### Ejemplos icónicos · Minard
Charles Joseph Minard, 1869 — Marcha de Napoleón a Moscú.
Una sola lámina codifica: tamaño del ejército, dirección, latitud, longitud, tiempo y temperatura. Tufte la
considera "the best statistical graphic ever drawn".

---

<!-- slide 46 -->
### Ejemplos icónicos · Snow
John Snow, 1854 — Mapa del brote de cólera en Soho, Londres.

---

<!-- slide 47 -->
### Ejemplos icónicos · Challenger
28 de enero de 1986, Challenger. Tufte argumenta que los gráficos enviados a Thiokol/NASA la noche anterior
escondieron la relación entre temperatura del O-ring y daños:
Los gráficos disponibles ordenaban los vuelos por fecha, no por temperatura.
No mostraban los vuelos sin falla, generando una correlación invisible.
Un simple scatter temperatura → daño  para todos los vuelos lo habría hecho evidente.
Referencia: Tufte, Visual Explanations, capítulo 2, "Visual and Statistical Thinking".

---

<!-- slide 48 -->
## Parte 9 · Cómo se implementa esto en Tableau
El default de Tableau no es Tufte
Tableau (y Power BI) traen defaults pensados para exploración rápida, no para publicación rigurosa. Convertir
un gráfico exploratorio en uno explicativo requiere ajustes manuales.
Norte
Sur
Centro
Este
Oeste
Sum of Sales
Defaults de Tableau
Sum of Sales
Norte
Sur
Centro
Este
Oeste
Norte concentra 2.4× lo de Oeste
Ventas 2024 por región (USD miles)
Mismo dato en Tableau: cinco ajustes que cambian la lectura

---

<!-- slide 49 -->
### Cinco ajustes que casi siempre aplican
Default de Tableau
Ajuste Tufte
Cómo en Tableau
Gridlines horizontales
quitarlas o muy tenues
Format → Lines → Grid Lines → None
Bordes en las marcas
sin borde, salvo destacar
Marks card → Color → Border = None
Leyenda al lado
etiquetas directas
Marks card → Label → ON , ocultar leyenda
Eje y con título "Sum of Sales"
título analítico en el chart
Format axis → Title = blank , escribir en el chart title
Orden alfabético de categorías
ordenar por valor
clic derecho dimensión → Sort → By field

---

<!-- slide 50 -->
### Pequeños múltiplos en Tableau
Tableau no tiene "small multiples" como objeto, pero los logras con la estructura de filas y columnas:
1. Arrastra la dimensión que define los paneles a Columns  o Rows .
2. Arrastra la métrica al eje opuesto.
3. Ajusta Size , Fit , y desactiva títulos individuales.
4. Comparte la misma escala entre paneles ( Edit Axis → Range = Uniform across panes ).
5. Aplica el mismo formato de Tufte a una vista; copia formato al resto con Format → Copy formatting .
Para grids más complejos: dimensión en Columns , segunda dimensión en Rows . Eso da un trellis completo.

---

<!-- slide 51 -->
### Color Blind 10 y paletas custom
Worksheet → Color → Edit Colors → Select Palette: Color Blind
Para paletas custom (Okabe–Ito) en Tableau:
<preferences>
<color-palette name="Okabe-Ito" type="regular">
<color>#000000</color>
<color>#E69F00</color>
<color>#56B4E9</color>
<color>#009E73</color>
<color>#F0E442</color>
<color>#0072B2</color>
<color>#D55E00</color>
<color>#CC79A7</color>
</color-palette>
</preferences>
Se guarda en Documents/My Tableau Repository/Preferences.tps .

---

<!-- slide 52 -->
### Calculated fields al servicio del gráfico
A veces el problema no es visual, es de dato. Si tu gráfico necesita:
agrupar 8 categorías largas en "top 5 + otros" → calculated field con IF RANK() <= 5 THEN [Cat] ELSE
'Otros' END
anotar el valor del último periodo en la línea → LAST() = 0  como filtro de label
normalizar a base 100 → SUM([Sales]) / WINDOW_MIN(...) * 100
destacar una serie sobre el resto → calculated field booleano usado en color
La Semana 7 del temario ( semana-07-calculos-analiticos.md ) profundiza estos cálculos. Aquí el principio es:
El gráfico correcto a veces empieza con el cálculo correcto.

---

<!-- slide 53 -->
### Bloque B · Cálculos analíticos
De la elección visual al cálculo de la métrica
El gráfico correcto a veces empieza con el cálculo correcto.
A continuación: cómo Tableau ejecuta cálculos, dónde están los errores sutiles y cómo blindar la lógica de
negocio dentro del workbook.

---

<!-- slide 54 -->
## Parte 10 · Fundamento conceptual
Pregunta directriz
é
ó
El error más común no es el operador, es la granularidad.
Tres preguntas que todo cálculo debe responder:
1. ¿A qué nivel se calcula? (fila, vista, grupo fijo)
2. ¿Cuándo se evalúa en el orden de operaciones?
3. ¿Cómo se compone con filtros y agregaciones que ya están en la vista?

---

<!-- slide 55 -->
### Row-level vs aggregate
order_id
qty
unit_price
line_total
1001
1002
1003
[Quantity] * [Unit Price]
→ se calcula en cada ﬁla antes de agregar
Tableau: granularidad = ﬁla del dataset
Cálculo a nivel de ﬁla
region
SUM(sales)
SUM(cost)
margen
Norte
8 000
5 500
31.3%
Sur
6 200
4 100
33.9%
Centro
4 500
3 200
28.9%
(SUM([Sales]) - SUM([Cost])) / SUM([Sales])
→ se calcula sobre el agregado de la vista
Tableau: granularidad = grupos de la hoja
Cálculo a nivel agregado
Dos niveles, dos fórmulas — confundirlos es el error más común
Row-level: la fórmula se evalúa en cada fila del dataset antes de cualquier agregación.
Aggregate: la fórmula se evalúa sobre el resultado agregado de la vista.

---

<!-- slide 56 -->
### ¿Cuál usar? Regla operativa
Pregunta
Nivel correcto
Ejemplo
¿Cuál es el total que paga este cliente?
row-level
[Quantity] * [Unit Price]
¿Cuál es el margen del segmento?
aggregate
(SUM([Sales]) - SUM([Cost])) / SUM([Sales])
¿Cuál es el ticket promedio?
aggregate
SUM([Sales]) / COUNTD([Order ID])
¿El cliente es premium (true/false)?
row-level
[Total Spent] > 10000
¿Cuál es la tasa de conversión global?
aggregate
SUM([Conversions]) / SUM([Visits])
Regla: si la respuesta cambia al cambiar el agrupamiento de la hoja, casi siempre va a nivel agregado.

---

<!-- slide 57 -->
### Error clásico: la "media de medias"
Datos de tres tiendas:
Tienda
Ventas
Visitas
Conversión por tienda
A
1000
10.0%
B
40.0%
C
100.0%
¿Cuál es la conversión total?
Promedio de las tres:
Sobre agregado:
La primera operación es row-level con AVG , la segunda es aggregate. Producen respuestas distintas; solo una
responde la pregunta.

---

<!-- slide 58 -->
## Parte 11 · Campos calculados
Sintaxis general
[Nombre del campo nuevo]
=  expresión válida en términos de campos existentes
Operadores y funciones que se combinan:
Numéricas: + , - , * , / , ABS , ROUND , LOG , POWER
Lógicas: IF ... THEN ... ELSE ... END , IIF , CASE
Fecha: DATEDIFF , DATEPART , DATETRUNC , TODAY
Texto: LEFT , RIGHT , MID , CONTAINS , SPLIT , TRIM
Tableau valida sintaxis al crear el campo, pero no valida semántica: una fórmula puede compilar y aun así
responder otra pregunta.

---

<!-- slide 59 -->
### Métricas derivadas: el catálogo mínimo
#### Métrica
Definición
Nivel
Fórmula típica
Margen
(ingreso − costo) / ingreso
aggregate
(SUM([Sales]) - SUM([Cost])) / SUM([Sales])
Ticket promedio
ventas / órdenes únicas
aggregate
SUM([Sales]) / COUNTD([Order ID])
Tasa de conversión
conversiones / visitas
aggregate
SUM([Conversions]) / SUM([Visits])
Ratio variable
dos medidas correlacionadas
aggregate
SUM([A]) / SUM([B])
% participación
parte / total visible
table calc
SUM([Sales]) / TOTAL(SUM([Sales]))
Indicador booleano
umbral aplicado por fila
row-level
[Sales] > [Quota]
Categoría derivada
bucketing por regla
row-level
IF [Sales]>1000 THEN 'A' ELSE 'B' END
Cada métrica nueva debe documentarse con definición, nivel y uso previsto.

---

<!-- slide 60 -->
### Buenas prácticas de naming
Prefijo m_  para measures derivadas, d_  para dimensiones derivadas.
Sufijo _pct , _usd , _dias  cuando la unidad importa.
Mayúscula inicial en el nombre visible, comentario en la fórmula.
[m_margen_pct]
=  // margen agregado: requiere agregaciones de la vista
(SUM([Sales]) - SUM([Cost])) / SUM([Sales])
Un nombre claro reduce la probabilidad de que otro analista lo combine con la métrica equivocada.

---

<!-- slide 61 -->
## Parte 12 · Parámetros
¿Qué es un parámetro?
Un parámetro es una variable de un solo valor, definida por el autor del workbook, controlable por el usuario y
consumida por una o varias fórmulas.
A diferencia de un filtro, no opera sobre el dataset: opera sobre expresiones.
Usos típicos:
Cambiar la métrica que se muestra en una hoja.
Cambiar un umbral (objetivo, target, threshold).
Cambiar un escenario temporal (último año, último trimestre).
Cambiar la dimensión por la que se segmenta.

---

<!-- slide 62 -->
### Patrón parameter swap
Parameter
[Métrica]
Calculated Field
CASE [Métrica]
WHEN 'Ventas' THEN [Sales]
WHEN 'Margen' THEN [Margin]
END
Hoja / Dashboard
muestra la métrica activa
Un solo dashboard, n métricas — sin duplicar hojas.
#### Patrón parameter swap: una hoja que cambia de métrica con el control
[Métrica activa]
=  CASE [Parámetro Métrica]
WHEN 'Ventas'  THEN SUM([Sales])
WHEN 'Margen'  THEN (SUM([Sales]) - SUM([Cost])) / SUM([Sales])
WHEN 'Ticket'  THEN SUM([Sales]) / COUNTD([Order ID])
END
Un solo dashboard ofrece n métricas sin duplicar hojas.

---

<!-- slide 63 -->
### Parámetros + filtros: cuándo combinar
Necesidad
Herramienta
El usuario escoge una categoría entre las del dataset
#### filtro
El usuario escoge una métrica entre fórmulas definidas por ti
parámetro
El usuario fija un umbral numérico arbitrario
parámetro
El usuario cambia el rango temporal mostrado
#### filtro
El usuario cambia la definición de "cliente premium"
parámetro
Regla: si la opción del usuario modifica una fórmula, es parámetro. Si restringe filas, es filtro.

---

<!-- slide 64 -->
## Parte 13 · Table calculations
Qué son y qué no son
Una table calculation se aplica sobre el resultado agregado que ya está en la vista, no sobre las filas del dataset.
Eso significa que:
Depende del arreglo de pills en Rows , Columns  y Marks .
Cambia de resultado si cambias la dirección de cálculo ( Compute Using ).
No existe fuera de su vista. Si copias el campo a otra hoja con distinta estructura, el resultado cambia.
Es el cálculo más expresivo de Tableau y también el más fácil de leer mal.

---

<!-- slide 65 -->
### Catálogo principal
Función
Qué calcula
Ejemplo de uso
RUNNING_SUM(expr)
acumulado en la dirección de la vista
venta acumulada del año
WINDOW_AVG(expr)
promedio móvil dentro de una ventana
media móvil de 3 meses
WINDOW_SUM(expr)
suma dentro de una ventana
total de los últimos N períodos
INDEX()
índice posicional dentro de la partición
top N, "primer mes del año"
RANK(expr)
ranking dentro de la partición
top 10 productos por región
DIFFERENCE(expr)
diferencia con el período anterior
crecimiento mes a mes
PERCENT_DIFFERENCE(expr)
diferencia porcentual
YoY simple
TOTAL(expr)
total de la partición
porcentaje del total visible

---

<!-- slide 66 -->
### Ejemplo: running total
#### E
F
M
A
J
S
O
N
D
Ventas mensuales
RUNNING_SUM(SUM([Sales])): el acumulado depende del orden de la vista
1000
1200
1400
Acumulado anual
1095
1230
1380
[m_ventas_acumulado]
=  RUNNING_SUM(SUM([Sales]))
El acumulado depende del orden de los meses en la vista. Cambiar el sort cambia la métrica.

---

<!-- slide 67 -->
### Partition y addressing
Cada table calc tiene dos ejes:
1. Partition (partición): el conjunto en el que se calcula. Reinicia cuando cambia esta dimensión.
2. Addressing (dirección): el orden en el que recorre la partición.
Por defecto Tableau adivina, pero conviene fijarlos manualmente:
Click derecho en la table calc → Compute Using → Specific Dimensions
Síntoma de mala configuración: el número cambia cuando rotas las pills de la vista sin haber cambiado el dato.

---

<!-- slide 68 -->
### % del total con TOTAL
[m_pct_total]
=  SUM([Sales]) / TOTAL(SUM([Sales]))
Lectura: la partición define respecto a qué total se calcula el porcentaje.
Partition definida sobre...
El % se calcula sobre...
toda la tabla
el total de la vista
[Region]
el total dentro de cada región
[Year], [Region]
el total de cada combinación año-región
El mismo campo puede ser "porcentaje del país" o "porcentaje de la región" sin cambiar la fórmula, solo la
partición.

---

<!-- slide 69 -->
## Parte 14 · LOD: Level of Detail
El problema que resuelven
Una vista en Tableau fija una granularidad: la combinación de dimensiones en Rows , Columns  y Marks . Las
agregaciones ( SUM , AVG , etc.) trabajan sobre ese nivel.
Pregunta clásica:
¿Cuál es la venta total de cada región aunque la vista esté agrupada por categoría?
Con una agregación normal no se puede: la vista ya está al nivel de categoría. Para "subir un nivel" o "bajar un
nivel" sin cambiar la vista, Tableau ofrece expresiones LOD.

---

<!-- slide 70 -->
### Sintaxis
{ FIXED   [dim1], [dim2], ... : expresión_agregada }
{ INCLUDE [dim1], [dim2], ... : expresión_agregada }
{ EXCLUDE [dim1], [dim2], ... : expresión_agregada }
Tres palabras clave, tres relaciones con la granularidad de la vista.

---

<!-- slide 71 -->
### FIXED, INCLUDE, EXCLUDE
A
B
#### C
Norte
Sur
Centro
{ FIXED [Region] : SUM([Sales]) }
agrupa por región sin importar la vista
FIXED [Region]
A
B
#### C
Norte
Sur
Centro
{ INCLUDE [Category] : SUM(...) }
agrega categoría a la vista actual
INCLUDE [Category]
A
B
#### C
Norte
Sur
Centro
{ EXCLUDE [Region] : SUM(...) }
omite la región del agrupamiento
EXCLUDE [Region]
LOD: tres formas de modiﬁcar la granularidad de un cálculo
FIXED : ignora la vista. Calcula a la granularidad declarada.
INCLUDE : parte de la vista y agrega la dimensión declarada como detalle.
EXCLUDE : parte de la vista y quita la dimensión declarada del agrupamiento.

---

<!-- slide 72 -->
### Ejemplo comparado
Dataset: ventas por Order ID , Region , Category .
{ FIXED [Region] : SUM([Sales]) }
→ total por región, sin importar lo que muestre la hoja.
{ INCLUDE [Customer] : SUM([Sales]) }
→ total por cliente como detalle adicional. Útil para AVG  por cliente dentro de un agregado regional.
{ EXCLUDE [Category] : SUM([Sales]) }
→ total por región (la categoría desaparece del agrupamiento). Útil para calcular % de categoría dentro de su
región.

---

<!-- slide 73 -->
### Patrón: porcentaje dentro de su grupo
[m_pct_categoria_en_region]
=  SUM([Sales]) / SUM({ EXCLUDE [Category] : SUM([Sales]) })
Lectura: la venta de cada categoría dividida entre la venta total de su región (independiente de las demás
dimensiones de la vista).
Equivalente con FIXED :
[m_pct_categoria_en_region_v2]
=  SUM([Sales]) / SUM({ FIXED [Region] : SUM([Sales]) })
Las dos respuestas suelen coincidir, pero interactúan distinto con los filtros de dimensión. La diferencia se
vuelve crítica al combinar con filtros.

---

<!-- slide 74 -->
## Parte 15 · Reference y trend lines
Reference lines: declaración
Reference line: un umbral conocido
promedio
p90
y ≈ 0.52x + 9.6
Trend line: hipótesis estadística
Reference vs trend line: una declara, la otra inﬁere
Una reference line declara un valor conocido:
promedio o mediana
umbral, target, quota
percentil específico

---

<!-- slide 75 -->
### Trend lines: inferencia
Una trend line ajusta un modelo a los puntos:
lineal, exponencial, logarítmico, polinómico
requiere mínimo de puntos y supuestos para ser confiable
Tableau reporta R² , p-valor  y banda de confianza
Lectura responsable:
1. Mirar R²  antes de citar la línea.
2. Comprobar que la forma del modelo se parezca a los puntos.
3. Recordar que correlación visual ≠ causalidad ni siquiera dentro de la muestra.

---

<!-- slide 76 -->
### Bands y distributions
Reference band: una franja entre dos valores (rangos aceptables, IC).
Reference distribution: cuartiles, deciles o desviaciones estándar.
Útiles para mostrar dispersión sin tener que dibujar cada punto.
Trampa: si la banda implica una distribución ( ±1σ ), el lector asume normalidad. Si los datos no son normales, la
banda miente. Mostrar boxplot en su lugar si la distribución es asimétrica.

---

<!-- slide 77 -->
## Parte 16 · Orden de operaciones
Por qué importa
El mismo cálculo puede dar resultados distintos según cuándo Tableau lo evalúa. La interacción con filtros es la
fuente más común de bugs sutiles.
Regla general: cuanto más arriba en el orden, menos lo afectan los filtros y agregaciones de la vista.

---

<!-- slide 78 -->
### El orden completo
1.
Extract / Data source ﬁlters
2.
Context ﬁlters
3.
FIXED LOD
4.
Dimension ﬁlters
5.
INCLUDE / EXCLUDE LOD
6.
Measure ﬁlters
7.
Forecasts
8.
Table calculations
9.
Table calc ﬁlters
10.
Trend lines / reference lines
antes de la vista
se aplica
agregación
depende de
la vista
Orden de operaciones en Tableau — por qué importa para tus cálculos
Consecuencia operativa:
FIXED  se calcula antes de los dimension filters, salvo que los hagas Context Filters .
INCLUDE  y EXCLUDE sí respetan los dimension filters.
Table calcs operan al final, sobre datos ya agregados y filtrados.

---

<!-- slide 79 -->
### Tres ejemplos prácticos
1. Quieres que un FIXED [Region]  respete tu filtro de país. Solución: marcar el filtro de país como Add to
Context .
2. El total de un RUNNING_SUM  no coincide con el SUM  agregado. Probablemente la partición está mal definida.
3. Una hoja muestra valores distintos al duplicarla porque la table calc depende del orden de pills, que cambia
al duplicar la vista. Fijar Compute Using → Specific Dimensions .

---

<!-- slide 80 -->
## Parte 17 · Errores frecuentes en cálculos
Catálogo de errores
Síntoma
Causa probable
Antídoto
Promedio de promedios incorrecto
row-level con AVG  cuando debe ser aggregate
reescribir como SUM / SUM
Margen "raro" en totales
calculado por fila y luego promediado
aggregate (SUM(Sales)-SUM(Cost))/SUM(Sales)
FIXED no respeta el filtro
filtro es dimension filter, no context
Add to Context
Running total da valores extraños
partición / addressing mal configurados
Compute Using → Specific Dimensions
% del total = 100% en todas las filas
partición es la fila misma
redefinir partition
Cifra cambia al duplicar la hoja
table calc dependiente del orden de pills
fijar dirección explícita
Trend line con R² bajísimo
modelo equivocado o datos sin estructura
retirar la línea o cambiar de modelo

---

<!-- slide 81 -->
### Errores conceptuales (no de fórmula)
Mezclar agregados y no agregados en una sola expresión: Tableau lo prohíbe explícitamente para forzar
disciplina.
Usar LOD como parche cuando bastaba con un filtro de contexto.
Calcular percent of total en una partición mal definida y comunicarlo como "porcentaje del país".
Mostrar demasiadas métricas derivadas que el usuario no puede interpretar; el dashboard parece poderoso
y nadie sabe leerlo.

---

<!-- slide 82 -->
## Parte 18 · Laboratorio guiado
Producto esperado
Sobre tu dashboard exploratorio de las semanas 5–6, agregar:
1. Cuatro métricas derivadas documentadas (definición, nivel, uso).
2. Una table calculation (running total, percent of total o moving average).
3. Un parámetro que cambie métrica o umbral.
4. Una expresión LOD que responda una pregunta de granularidad explícita.
5. Una reference line (objetivo) y opcionalmente una trend line con discusión de R² .
Cada cálculo debe venir con un comentario dentro del field que explique su nivel y uso.

---

<!-- slide 83 -->
### Checklist antes de publicar
¿Cada métrica derivada tiene nombre, definición y nivel documentados?
¿La hoja se sigue leyendo si quitas el parámetro?
¿La table calc da el mismo resultado al rotar las pills de la vista? (si no, fijar partition/addressing)
¿El LOD interactúa correctamente con los filtros activos?
¿La reference line declara un umbral conocido y no una inferencia disfrazada?
¿Existe alguna trend line cuya R²  no justifique reportarla?

---

<!-- slide 84 -->
## Parte 19 · Ejercicios integrados
Ejercicio 1 · Identificar el error visual
Un gerente comparte el siguiente gráfico:
Barras 3D, eje y de 95 a 105, dos categorías ("Antes" y "Después") con valores 99 y 102.
Título: "Crecimiento del trimestre".
1. ¿Cuántos errores de Tufte ves?
2. ¿Cuál distorsiona más al lector?
3. ¿Cómo lo rediseñarías para una presentación directiva?

---

<!-- slide 85 -->
### Solución 1
Errores presentes:
3D innecesario: chartjunk puro.
Eje truncado (95–105): lie factor alto.
Sin contexto temporal: dos puntos no son una tendencia.
Título normativo: "Crecimiento" implica conclusión antes de mostrar dato.
Rediseño defendible:
Slope graph o barras 2D con eje desde 0.
Anotación explícita del cambio ( +3.0% ).
Título descriptivo: "Índice de ventas pasa de 99 a 102 entre T2 y T3 (n=412 órdenes)".

---

<!-- slide 86 -->
### Ejercicio 2 · Elegir el gráfico
Tienes un dataset con:
1 dimensión categórica (10 productos),
1 medida (ventas por mes),
3 años de historia mensual.
El stakeholder pregunta: "¿qué productos están creciendo, cuáles cayendo, y cuáles se estancaron?"
¿Qué gráfico eliges? ¿Por qué?

---

<!-- slide 87 -->
### Solución 2
Opciones por orden de preferencia:
1. Pequeños múltiplos de líneas, una por producto, misma escala. Permite leer 10 trayectorias sin spaghetti.
2. Slope graph entre el primer y último año, anotando la pendiente. Funciona si la dinámica intermedia no
importa.
3. Heatmap producto × mes con paleta divergente centrada en 0% de cambio. Útil si interesa estacionalidad.
Evitar: 10 líneas en un eje, pie chart del último año, barras 3D apiladas.

---

<!-- slide 88 -->
### Ejercicio 3 · Rediseñar un dual axis
Te muestran un gráfico con dos ejes:
eje izquierdo: número de leads (escala 0–2000)
eje derecho: tasa de conversión % (escala 0–10%)
mismo eje x, 24 meses
Las dos líneas suben juntas y el autor concluye: "más leads, más conversión".
¿Qué problemas hay y cómo lo rediseñas?

---

<!-- slide 89 -->
### Solución 3
Problemas:
Escalas arbitrarias: la pendiente visual es decisión del diseñador, no del dato.
Insinúa causalidad sin controlar nada.
La conversión no escala con leads; es un ratio cuyo numerador y denominador se mueven.
Rediseño:
Pequeños múltiplos: panel A = leads en el tiempo; panel B = conversión en el tiempo.
O un scatter leads vs conversión , un punto por mes, anotando dirección temporal.
O reportar el producto leads × conversión = ventas  como una sola serie y dejar las otras dos como
diagnóstico.

---

<!-- slide 90 -->
### Ejercicio 4 · Promedio de promedios
Una hoja muestra "conversión promedio por región" como:
AVG( [Conversiones] / [Visitas] )
El resultado del total país no coincide con el cálculo manual que hace finanzas.
1. ¿Por qué?
2. Reescribe la métrica correctamente.

---

<!-- slide 91 -->
### Solución 4
AVG([Conversiones] / [Visitas])  se calcula fila por fila y luego promedia. Las filas con pocas visitas pesan
igual que las filas con muchas.
Métrica correcta a nivel agregado:
[m_conversion_global]
=  SUM([Conversiones]) / SUM([Visitas])
Esta versión da la tasa real del país: total conversiones sobre total visitas.

---

<!-- slide 92 -->
### Ejercicio 5 · LOD vs filtro
Un analista quiere mostrar el promedio de ventas por cliente, dentro de una vista agrupada por mes y categoría.
1. ¿Qué fórmula usar?
2. ¿Cambia algo si el dashboard tiene un filtro por país?

---

<!-- slide 93 -->
### Solución 5
[m_avg_por_cliente]
=  AVG({ INCLUDE [Customer ID] : SUM([Sales]) })
INCLUDE [Customer ID]  agrega el detalle de cliente a la vista solo para este cálculo. Luego AVG  se aplica sobre
esos sub-agregados.
Sobre el filtro de país: como INCLUDE  se evalúa después de los dimension filters, el resultado se restringirá al
país seleccionado automáticamente. No hace falta Add to Context .
Si usáramos { FIXED [Customer ID] : SUM([Sales]) } , sí tendríamos que marcar el filtro de país como
context para que respete el alcance.

---

<!-- slide 94 -->
### Ejercicio 6 · Table calc inestable
Una table calc WINDOW_AVG(SUM([Sales]), -2, 0)  muestra "media móvil de 3 meses". Al duplicar la hoja y
poner los meses en Columns  en vez de en Rows , los valores cambian.
1. ¿Qué pasó?
2. ¿Cómo blindar el cálculo?

---

<!-- slide 95 -->
### Solución 6
La table calc usa la dirección de la vista para definir su ventana. Al rotar las pills, Tableau cambia de "compute
along table down" a "compute along table across" y la ventana se recalcula en otra dirección.
Solución:
Click derecho en la table calc → Edit Table Calculation →
Compute Using → Specific Dimensions → seleccionar [Order Date (Month)]
Así la dirección queda anclada a la dimensión temporal, no a la orientación visual.

---

<!-- slide 96 -->
### Ejercicio 7 · Integrador (visual + cálculo)
El stakeholder quiere ver "qué tan bien performó cada vendedor respecto a su objetivo, segmentado por región y
trimestre".
Diseña la respuesta completa:
1. ¿Qué métrica derivada necesitas y a qué nivel?
2. ¿Qué tipo de gráfico la muestra?
3. ¿Necesitas LOD, table calc o ambos?
4. ¿Qué errores visuales debes evitar al implementarla?

---

<!-- slide 97 -->
### Solución 7 (sugerida)
Métrica: [m_pct_objetivo] = SUM([Sales]) / SUM([Quota])  a nivel agregado, para que se recalcule por
cada celda de la vista.
Gráfico: pequeños múltiplos de dot plots por región (filas) y trimestre (columnas). Cada panel muestra
vendedores ordenados por % objetivo, con una reference line vertical en 100%.
Cálculos auxiliares:
[d_alcanza_objetivo] = [m_pct_objetivo] >= 1  → color binario (azul / gris), no rojo–verde.
LOD opcional { FIXED [Vendedor], [Trimestre] : SUM([Sales]) }  si necesitas comparar el mismo
vendedor entre regiones sin perder la granularidad temporal.
Errores a evitar:
pie chart o gauge por vendedor
spaghetti chart con 30 líneas en un eje
color rojo–verde como única codificación
eje truncado para amplificar diferencias

---

<!-- slide 98 -->
### Cierre
Lo que se llevan los estudiantes
Sobre selección visual
La pregunta elige el gráfico, no la herramienta.
Data-ink y lie factor son linternas, no normas dogmáticas.
Pequeños múltiplos y slope graphs resuelven la mayoría de los spaghetti charts.
Sobre cálculos analíticos
Una métrica se define por su nivel, no por su nombre.
Parámetros cambian fórmulas; filtros cambian filas.
Table calcs dependen de la vista; declarar partition y addressing.
LOD modifica la granularidad sin romper la vista.
Reference line declara; trend line infiere.

---

<!-- slide 99 -->
### Puente con la Semana 8
Esta semana respondió:
¿
é
á
é
La Semana 8 responde:
¿
ó
á
Pasamos de un gráfico defensible con un cálculo defensible a una narrativa visual completa.

---

<!-- slide 100 -->
### Referencias
Visualización y diseño
Tufte, E. R. The Visual Display of Quantitative Information. Graphics Press, 1983.
Tufte, E. R. Envisioning Information. Graphics Press, 1990.
Tufte, E. R. Visual Explanations. Graphics Press, 1997.
Cleveland, W. S., & McGill, R. (1984). "Graphical Perception". JASA, 79(387), 531–554.
Mackinlay, J. (1986). "Automating the Design of Graphical Presentations". ACM TOG, 5(2), 110–141.
Wong, B. (2011). "Color blindness". Nature Methods, 8(6), 441.
Okabe, M., & Ito, K. (2008). Color Universal Design. jfly.uni-koeln.de/color/ .
Cairo, A. The Truthful Art. New Riders, 2016.
Few, S. Show Me the Numbers. Analytics Press, 2012.
Wilke, C. Fundamentals of Data Visualization. O'Reilly, 2019. clauswilke.com/dataviz .
Anscombe, F. J. (1973). "Graphs in Statistical Analysis". The American Statistician, 27(1), 17–21.
Cálculo analítico en Tableau
