"""Genera el entregable del caso H&M (examen final):
  docs/Caso_HM.docx y .pdf          contexto, que se desea saber, propuesta, datos, reglas de calidad, indicadores,
                                    los 5 dashboards (con su prototipo en hoja horizontal) y como se actualiza.
  docs/HM_Modelos_Dashboards.pptx   los 5 prototipos (wireframes); sus imagenes van dentro del Word.
SIN CIFRAS: la data cambia en cada carga (el profesor envia datos nuevos), asi que el documento describe que
muestra cada indicador y como se lee; los valores se ven en Power BI despues de ejecutar Job_HM.
Uso (con Word y PowerPoint cerrados): python generar_caso_hm.py
"""
import os
import subprocess
import docx
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.shared import Pt, RGBColor, Cm
from pptx import Presentation
from pptx.util import Emu, Pt as PPt
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

DIR = os.path.dirname(os.path.abspath(__file__))
NAVY, BG, CARD, LINE = "1F3A5F", "F2F4F7", "FFFFFF", "D5DAE1"
VERDE, AMBAR, ROJO, AZUL, GRIS, TXT, TXT2, CLARO = ("1E8449", "B9770E", "B03A2E", "2E6DA4", "8A94A3", "1F2933", "5B6573",
                                                    "C9D3E0")

# ------------------------------------------------------------------ contenido
ARCHIVOS = [
    ("transaction.csv", "Una fila por artículo vendido: fecha, cliente, artículo, precio y canal.", "FactVentas"),
    ("customers.csv", "Clientes: club, noticias de moda, edad y código postal.", "DimCliente"),
    ("articles.csv", "Catálogo: producto, tipo, grupo, color, departamento, sección y línea.", "DimArticulo, DimDepartamento"),
    ("DimFecha.csv", "Calendario con los atributos de cada día.", "DimFecha"),
    ("Temporada.csv", "Las temporadas con su fecha de inicio y de fin.", "DimTemporada"),
    ("GoalsHyM.xlsx", "Metas de venta por escenario, departamento, sección, temporada y año-mes.", "FactMetas"),
]

REGLAS = [
    ("Stage", "Copia fiel de los archivos, todo como texto y sin valores por defecto: si un archivo viene sucio, la carga no se cae."),
    ("Duplicados", "Si la fila completa se repite, se conserva una (indicación del profesor). En ventas, LineasOrigen "
                   "guarda cuántas veces venía; en las tablas maestras, la copia queda en la tabla de error con su motivo."),
    ("Precio", "price × 40 000 con 4 decimales, en el ETL del DWH (después del Stage). La coma se lee como separador "
               "decimal. Un precio vacío o con letras no se rellena: va a la tabla de error. Un precio 0 o negativo se "
               "carga tal cual (puede ser oferta o devolución)."),
    ("Fechas", "Formatos del caso: yyyymmdd y yyyy-mm-dd. Con “/” se lee día/mes/año, como en el Perú; si el segundo "
               "número es mayor que 12 solo puede ser mes/día. Una fecha imposible va a la tabla de error."),
    ("Campos calculados", "No se confía en los calculados del archivo: Fin_Semana, día, semana, mes, trimestre, etc. "
                          "se recalculan desde la fecha."),
    ("Temporada de cada venta", "Se deduce de la fecha de la venta con los rangos de Temporada.csv (el día en que se "
                                "cruzan dos temporadas pertenece a la que termina)."),
    ("Textos", "“Unknown”, “undefined” y vacíos se unifican como “Sin Datos”; “NONE”/“None” como un solo valor; "
               "una edad fuera de 16–100 queda como “Sin dato” sin perder al cliente."),
    ("Metas", "Se cargan tal como vienen (por escenario, sección, temporada y mes), sin repartirlas ni multiplicarlas."),
    ("Nada de supuestos", "Lo que se puede recalcular desde su origen se corrige; lo que no, se separa con su motivo y "
                          "su valor original para validarlo con el negocio. Nada se pierde sin explicación."),
]

IND = [  # (indicador, formula, fuente, dashboard)
    ("Ventas", "Σ precio (price × 40 000)", "FactVentas", "3, 4"),
    ("Crecimiento interanual", "ventas del periodo / ventas de los mismos días del año de comparación − 1", "FactVentas", "3, 4"),
    ("Participación online", "ventas online (canal 2) / ventas", "FactVentas + DimCanal", "3"),
    ("Líneas de venta y cestas", "cesta = mismo cliente, día y canal (el archivo no trae número de ticket)", "FactVentas", "3"),
    ("Ticket por cesta", "ventas / cestas", "FactVentas", "3"),
    ("Clientes que compran", "clientes distintos con venta en el filtro", "FactVentas", "1"),
    ("Clientes nuevos", "clientes cuya primera compra cae en el periodo", "FactVentas + DimCliente", "1"),
    ("Retención", "clientes del año de comparación que vuelven a comprar / clientes del año de comparación", "FactVentas", "1"),
    ("Clientes omnicanal", "clientes que compran en tienda y online / clientes", "FactVentas", "1"),
    ("Penetración del club", "clientes con Active = 1 / clientes", "FactVentas + DimCliente", "1"),
    ("Concentración", "participación en la venta del 20 % de clientes que más compra", "FactVentas", "1"),
    ("Artículos vendidos y por cesta", "artículos distintos; líneas / cestas", "FactVentas", "2"),
    ("Descuento implícito", "1 − Σ precio cobrado / Σ precio más alto observado del mismo artículo", "FactVentas", "2"),
    ("Cumplimiento de meta", "ventas / meta de GoalsHyM (escenario elegido; por defecto el Escenario 2)", "FactVentas + FactMetas", "5"),
    ("Secciones que cumplen / bajo 50 %", "secciones con cumplimiento ≥ 100 % / < 50 %", "FactVentas + FactMetas", "5"),
]

FILTROS_COMP = ("Sin filtros se ve todo el periodo. “Año” y “Comparar con” comparan los mismos días de dos años "
                "(si no se elige con qué comparar, se usa el año anterior). Los valores de los filtros salen del cubo: "
                "si llegan años nuevos, aparecen solos.")

DASH = [
    dict(n="1 · Clientes", t="Análisis de clientes", preg="¿Quiénes compran y cómo?",
         aud="marketing y CRM", frec="mensual",
         filtros=["Año", "Comparar con", "Mes", "Canal", "Edad"],
         kpis=[("Clientes que compran", None), ("Clientes nuevos", "anillo"), ("Retención", "anillo"),
               ("Clientes omnicanal", "anillo"), ("Penetración club activo", "anillo")],
         paneles=[("¿Quién genera la venta?", "dona", "Dona: es una relación parte-todo (el 20 % de clientes que más compra frente al resto)."),
                  ("Clientes por rango de edad", "barras", "Barras: comparan grupos de edad en la misma escala; “Sin dato” muestra a quienes no traen edad."),
                  ("Venta por cliente según cómo compra", "barras", "Barras: comparan cuánto vale el cliente omnicanal frente al de un solo canal."),
                  ("Clientes nuevos por año", "barras", "Barras por año: muestran si la captación sube o baja; los años nuevos aparecen solos.")],
         leer=["Arriba: cuántos clientes compran y cómo están la captación, la retención, el omnicanal y el club.",
               "La dona dice cuánto depende la venta de los mejores clientes.",
               "Las barras de edad y de forma de compra dicen a quién dirigir cada campaña.",
               "Con Año y Comparar con, cada indicador se compara con los mismos días del otro año."],
         dec=["Campañas por rango de edad.", "Convertir clientes de un canal en omnicanal.",
              "Activar socios del club en la primera compra.", "Cuidar al 20 % que concentra la venta."]),
    dict(n="2 · Artículos", t="Análisis de artículos", preg="¿Qué artículos y secciones mueven la venta?",
         aud="compras, producto y pricing", frec="mensual",
         filtros=["Año", "Comparar con", "Mes", "Canal", "Línea"],
         kpis=[("Artículos vendidos", None), ("Ventas (MM)", None), ("Artículos por cesta", None),
               ("Descuento implícito", None), ("Líneas con más de 30 % de descuento", None)],
         paneles=[("Venta por línea", "dona", "Dona: participación de cada línea (Ladieswear, Divided, Menswear…) en la venta."),
                  ("Venta por grupo de producto", "barrasH", "Barras horizontales ordenadas: los nombres largos se leen y se ve el ranking."),
                  ("Secciones que más venden", "barrasH", "Barras ordenadas de mayor a menor, con desplazamiento para ver todas las secciones."),
                  ("Venta por banda de descuento", "barras", "Barras: cuánto se vende sin descuento, hasta 10 %, 10–30 % y más de 30 %.")],
         leer=["Arriba: cuántos artículos distintos se venden, cuántos por cesta y cuánto descuento se da.",
               "La dona y los rankings dicen qué líneas, grupos y secciones explican la venta.",
               "La banda de descuento dice cuánto de la venta depende de rebajas fuertes."],
         dec=["Asegurar stock de lo que más vende.", "Revisar las secciones con poca venta.",
              "Controlar las rebajas de más de 30 %.", "Venta cruzada para subir los artículos por cesta."]),
    dict(n="3 · Transacciones", t="Análisis de las transacciones", preg="¿Cómo evolucionan las ventas y por qué canal?",
         aud="gerencia comercial y finanzas", frec="mensual",
         filtros=["Año", "Comparar con", "Mes", "Canal", "Temporada"],
         kpis=[("Ventas (MM)", None), ("Líneas de venta", None), ("Cestas", None), ("Ticket por cesta", None),
               ("Participación online", "anillo")],
         paneles=[("Ventas mes a mes", "linea", "Línea: la venta es una serie en el tiempo; la línea gris es el mismo mes del año de comparación."),
                  ("Mezcla de canal", "dona", "Dona: tienda frente a online, con la variación de cada canal contra el año de comparación."),
                  ("Ventas por día de la semana", "barras", "Barras: en qué días se concentra la venta.")],
         leer=["Arriba: cuánto se vende, cuántas líneas y cestas, el ticket por cesta y el peso del online.",
               "La línea muestra en qué meses se gana o se pierde frente al año de comparación.",
               "La dona dice qué canal sostiene la venta y cuál crece."],
         dec=["Explicar la variación de cada mes.", "Reforzar el canal que pierde participación.",
              "Planificar personal y stock por día de la semana.", "Seguir el ticket por cesta."]),
    dict(n="4 · Temporadas y fechas", t="Análisis comparativo entre temporadas y fechas",
         preg="¿Cómo se comparan las temporadas y los años?", aud="gerencia comercial", frec="por temporada",
         filtros=["Año", "Comparar con", "Canal", "Estación", "Temporada"],
         kpis=[("Ventas (MM)", None), ("Mismo periodo del año de comparación", None), ("Crecimiento interanual", None),
               ("Crecimiento en tienda", None), ("Crecimiento online", None)],
         paneles=[("Ventas de cada año", "barras", "Barras por año: cuánto se vendió cada año."),
                  ("Ventas por estación y año", "barras2", "Barras agrupadas: cada estación junto a la misma estación de los otros años."),
                  ("Ventas por mes y año", "lineas2", "Una línea por año: compara el mismo mes entre años."),
                  ("Ventas por temporada", "barras", "Barras en orden de temporada; el filtro Temporada permite ver una sola.")],
         leer=["Sin filtros se ven todos los años; con Año y Comparar con, los indicadores comparan los mismos días.",
               "Los gráficos de año, estación y mes muestran siempre todos los años para comparar.",
               "El filtro Temporada (por ejemplo, invierno-2019) o Año + Estación muestran una temporada de un año."],
         dec=["Comparar cada temporada con la misma del año anterior.", "Planificar compras según la estación que crece.",
              "Revisar los meses que caen.", "Separar el efecto de canal en cada temporada."]),
    dict(n="5 · Metas por temporada y fechas", t="Análisis con las metas por temporada y fechas",
         preg="¿Qué temporadas y secciones están fuera de meta?", aud="jefes de sección y de temporada",
         frec="por temporada y mes",
         filtros=["Escenario", "Año", "Mes", "Temporada", "Sección"],
         kpis=[("Cumplimiento de meta", "anillo"), ("Peor temporada", "anillo"), ("Secciones que cumplen", "anillo"),
               ("Secciones bajo 50 %", "anillo")],
         paneles=[("Velocímetro de meta", "gauge", "Velocímetro: muestra el avance frente a la meta (100 %) y abajo los 3 escenarios."),
                  ("Cumplimiento por temporada", "barras", "Barras con semáforo: en qué temporada se pierde la meta."),
                  ("Cumplimiento por mes", "barras", "Barras por mes: la meta viene por mes y se compara con la venta del mismo mes."),
                  ("Extremos de cumplimiento", "barrasH", "Las 5 secciones con mayor y menor cumplimiento: una lista para actuar.")],
         leer=["Por defecto se ve el Escenario 2 (meta oficial); el filtro Escenario cambia la meta.",
               "Cada venta se asigna a su temporada por su fecha; la meta trae su temporada y su mes.",
               "Verde cumple la meta, ámbar está a menos de 10 %, rojo más lejos.",
               "Si el cumplimiento sale muy lejos de 100 %, la meta no está en la escala de la venta: se valida con el negocio."],
         dec=["Validar la escala y el periodo de la meta.", "Seguimiento mensual de venta vs meta.",
              "Plan para la temporada más lejos de la meta.", "Revisar las secciones bajo 50 %."]),
]


# ------------------------------------------------------------------ prototipos (wireframes sin cifras)
F = 0.6
def E(px): return Emu(int(px * 12192000 / 1920))


def caja(s, x, y, w, h, fill=CARD, line=LINE, forma=MSO_SHAPE.ROUNDED_RECTANGLE):
    sh = s.shapes.add_shape(forma, E(x), E(y), E(w), E(h)); sh.shadow.inherit = False
    sh.fill.solid(); sh.fill.fore_color.rgb = PRGB.from_string(fill)
    if line: sh.line.color.rgb = PRGB.from_string(line); sh.line.width = Emu(9525)
    else: sh.line.fill.background()
    if forma == MSO_SHAPE.ROUNDED_RECTANGLE: sh.adjustments[0] = 0.04
    return sh


def texto(s, x, y, w, h, txt, size=14, color=TXT, bold=False, align=PP_ALIGN.LEFT):
    tb = s.shapes.add_textbox(E(x), E(y), E(w), E(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]; p.alignment = align; r = p.add_run(); r.text = txt
    r.font.size = PPt(size * F); r.font.bold = bold; r.font.color.rgb = PRGB.from_string(color); r.font.name = "Segoe UI"


def icono(s, tipo, x, y, w, h):
    """Dibujo esquematico del tipo de grafico (sin valores)."""
    if tipo in ("dona",):
        d = min(w, h) * 0.8
        sh = s.shapes.add_shape(MSO_SHAPE.DONUT, E(x + (w - d) / 2), E(y + (h - d) / 2), E(d), E(d))
        sh.fill.solid(); sh.fill.fore_color.rgb = PRGB.from_string(AZUL); sh.line.fill.background(); sh.adjustments[0] = 0.2
    elif tipo == "gauge":
        d = min(w, h * 1.6) * 0.8
        sh = s.shapes.add_shape(MSO_SHAPE.BLOCK_ARC, E(x + (w - d) / 2), E(y + 10), E(d), E(d))
        sh.fill.solid(); sh.fill.fore_color.rgb = PRGB.from_string(VERDE); sh.line.fill.background()
        sh.adjustments[0] = 108; sh.adjustments[1] = 0;   # 180° a 0° (python-pptx: grados x 0.6) sh.adjustments[2] = 0.22
    elif tipo in ("barras", "barras2"):
        n = 6; bw = w / (n * 1.6)
        for i, f in enumerate([0.55, 0.8, 0.45, 0.95, 0.65, 0.35]):
            for k, col in enumerate([NAVY] if tipo == "barras" else [CLARO, NAVY]):
                bh = h * f * (0.85 if k == 0 and tipo == "barras2" else 1)
                caja(s, x + i * bw * 1.6 + k * bw / 2, y + h - bh, bw / (1 if tipo == "barras" else 2), bh, col, None,
                     MSO_SHAPE.RECTANGLE)
    elif tipo == "barrasH":
        for i, f in enumerate([0.95, 0.8, 0.62, 0.5, 0.38, 0.25, 0.15]):
            caja(s, x + w * 0.3, y + i * h / 7, w * 0.68 * f, h / 7 * 0.6, AZUL, None, MSO_SHAPE.RECTANGLE)
            caja(s, x, y + i * h / 7 + 4, w * 0.25, h / 7 * 0.35, CLARO, None, MSO_SHAPE.RECTANGLE)
    elif tipo in ("linea", "lineas2"):
        for k, (col, pts) in enumerate([(NAVY, [0.6, 0.4, 0.55, 0.3, 0.45, 0.2]), (GRIS, [0.7, 0.55, 0.6, 0.5, 0.55, 0.4])]):
            for i in range(len(pts) - 1):
                c = s.shapes.add_connector(1, E(x + i * w / 5), E(y + h * pts[i]), E(x + (i + 1) * w / 5), E(y + h * pts[i + 1]))
                c.line.color.rgb = PRGB.from_string(col); c.line.width = Emu(38100)


def prototipo(pr, dsh):
    s = pr.slides.add_slide(pr.slide_layouts[6])
    caja(s, 0, 0, 1920, 1080, BG, None, MSO_SHAPE.RECTANGLE)
    caja(s, 40, 30, 1840, 150, NAVY, None, MSO_SHAPE.RECTANGLE)
    texto(s, 60, 45, 1100, 60, dsh["preg"], 34, "FFFFFF", True)
    texto(s, 60, 110, 1100, 40, f"Dashboard {dsh['n']} · {dsh['t']} · {dsh['aud']} · {dsh['frec']}", 15, CLARO)
    x = 1880 - len(dsh["filtros"]) * 150
    for f in dsh["filtros"]:
        texto(s, x + 4, 40, 140, 22, f, 12, CLARO)
        caja(s, x, 64, 140, 38); texto(s, x + 12, 72, 120, 24, "Todas  ▾", 14, NAVY)
        x += 150
    k = len(dsh["kpis"]); w = (1840 - (k - 1) * 20) / k
    for i, (nombre, anillo) in enumerate(dsh["kpis"]):
        x = 40 + i * (w + 20); caja(s, x, 200, w, 140)
        tx = x + 24
        if anillo:
            sh = s.shapes.add_shape(MSO_SHAPE.BLOCK_ARC, E(x + 18), E(225), E(90), E(90))
            sh.fill.solid(); sh.fill.fore_color.rgb = PRGB.from_string(VERDE); sh.line.fill.background()
            sh.adjustments[0] = 108; sh.adjustments[1] = 0;   # 180° a 0° (python-pptx: grados x 0.6) sh.adjustments[2] = 0.22
            tx = x + 128
        texto(s, tx, 215, w - (tx - x) - 10, 30, nombre, 15, TXT2)
        texto(s, tx, 255, w - (tx - x) - 10, 50, "valor", 30, GRIS)
        texto(s, tx, 305, w - (tx - x) - 10, 26, "vs año de comparación", 12, GRIS)
    p = len(dsh["paneles"]); pw = (1840 - (p - 1) * 20) / p
    for i, (tit, tipo, _) in enumerate(dsh["paneles"]):
        x = 40 + i * (pw + 20); caja(s, x, 360, pw, 540)
        texto(s, x + 16, 375, pw - 32, 40, tit, 18, NAVY, True)
        icono(s, tipo, x + 30, 440, pw - 60, 380)
    caja(s, 40, 920, 1840, 118, "E8EEF6", CLARO)
    texto(s, 60, 930, 600, 30, "Decisiones", 18, NAVY, True)
    for i, t in enumerate(dsh["dec"]):
        texto(s, 60 + i * 455, 970, 440, 60, f"{i + 1}. {t}", 15, TXT)
    texto(s, 40, 1045, 1840, 30, "Prototipo (wireframe): los valores salen del cubo Tabular_HM al actualizar Power BI.",
          12, TXT2)


def ppt():
    pr = Presentation(); pr.slide_width, pr.slide_height = Emu(12192000), Emu(6858000)
    for dsh in DASH:
        prototipo(pr, dsh)
    pr.save(os.path.join(DIR, "HM_Modelos_Dashboards.pptx"))


# ------------------------------------------------------------------ Word
def doc_base():
    d = docx.Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2.2); s.top_margin = s.bottom_margin = Cm(2)
    return d


def hoja(d, horizontal):
    sec = d.add_section(WD_SECTION.NEW_PAGE)
    ancho, alto = Cm(21), Cm(29.7)
    sec.orientation = WD_ORIENT.LANDSCAPE if horizontal else WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = (alto, ancho) if horizontal else (ancho, alto)
    sec.left_margin = sec.right_margin = Cm(2.0) if horizontal else Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(1.5) if horizontal else Cm(2)


def titulo(d, txt, size=14, color=NAVY):
    p = d.add_paragraph(); r = p.add_run(txt); r.bold = True; r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(color)


def vineta(d, k, v=None):
    p = d.add_paragraph(style="List Bullet")
    if v is None: p.add_run(k)
    else: r = p.add_run(k + ": "); r.bold = True; p.add_run(v)


def tabla(d, enc, filas):
    t = d.add_table(rows=1, cols=len(enc)); t.style = "Light Grid Accent 1"
    for i, h in enumerate(enc): t.rows[0].cells[i].text = h
    for f in filas:
        c = t.add_row().cells
        for i, v in enumerate(f): c[i].text = str(v)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs: r.font.size = Pt(9.5)
    d.add_paragraph()


def caso():
    d = doc_base()
    titulo(d, "Caso H&M: Inteligencia de Negocios de punta a punta", 18)
    d.add_paragraph("Modelo Stage, Datamart, ETLs, cubo tabular y 5 dashboards del proceso de ventas de H&M.")

    titulo(d, "1. Contexto del negocio")
    d.add_paragraph("H&M es una cadena de moda que vende por dos canales: tiendas físicas (canal 1) y tienda online "
                    "(canal 2). Su oferta se organiza en líneas, grupos de producto, departamentos y secciones, y su año "
                    "comercial se divide en temporadas (verano, otoño, invierno y primavera). Sus clientes pueden "
                    "pertenecer a un club y recibir noticias de moda. El área comercial fija metas de venta por "
                    "departamento, sección, temporada y mes, en tres escenarios; el Escenario 2 es la meta oficial.")
    d.add_paragraph("Los datos vienen de un concurso público (anonimizados). Por eso el precio viene en una escala muy "
                    "pequeña y, por indicación del profesor, se multiplica por 40 000.")

    titulo(d, "2. ¿Qué se desea saber?")
    for dsh in DASH:
        vineta(d, dsh["t"], dsh["preg"])

    titulo(d, "3. Propuesta y por qué")
    d.add_paragraph("Una solución de punta a punta que se ejecuta con un solo Job de SQL Server Agent: carga los "
                    "archivos al Stage, los limpia y los lleva al Datamart, procesa el cubo y deja los 5 dashboards "
                    "listos en Power BI. Así, cuando llegan datos nuevos, basta con reemplazar los archivos y ejecutar el Job.")
    vineta(d, "Por qué un Stage separado", "para que la carga nunca se caiga por data sucia y siempre se pueda comparar el dato original con el limpio.")
    vineta(d, "Por qué un modelo estrella", "ventas y metas comparten fecha, temporada y sección; así se comparan en cualquier nivel.")
    vineta(d, "Por qué un cubo tabular", "los indicadores se calculan una sola vez (DAX) y todos los dashboards usan la misma definición.")
    vineta(d, "Por qué 5 dashboards", "cada uno responde una pregunta distinta del negocio: clientes, artículos, transacciones, temporadas y metas.")

    titulo(d, "4. Origen de los datos")
    tabla(d, ["Archivo", "Qué trae", "Destino en el Datamart"], ARCHIVOS)

    titulo(d, "5. Proceso de punta a punta")
    for k, v in [("Paso 1 · Stage (SSIS, proyecto stage_H&M)", "copia los 6 archivos a STAGE_HM, tal como vienen."),
                 ("Paso 2 · Datamart (SSIS, proyecto DWH_H&M)", "tablas maestras con MERGE y hechos con búsqueda de llaves; "
                                                                "lo que no sirve va a las tablas de error con su motivo."),
                 ("Paso 3 · Cubo (Analysis Services)", "procesa Tabular_HM con las medidas de los dashboards."),
                 ("Power BI", "conexión en vivo al cubo: Actualizar muestra los datos nuevos."),
                 ("Auditoría", "cada paquete registra en DIM_AUDIT cuándo corrió, filas antes y después, insertadas, "
                               "actualizadas, duplicadas, con error y el mensaje si falla."),
                 ("Calidad de datos", "en cada carga, dbo.CalidadDatos resume por campo los datos que sí entraron pero "
                                      "venían con un problema (ausente, inconsistente, en otro formato o atípico) y qué "
                                      "hizo el ETL con ellos; se une a DIM_AUDIT por AuditKey.")]:
        vineta(d, k, v)

    titulo(d, "6. Reglas de calidad de datos")
    tabla(d, ["Tema", "Regla"], REGLAS)
    d.add_paragraph("El script sql\\03_validaciones.sql muestra, para cada archivo, cuántas filas llegaron, cuántas se "
                    "cargaron, cuántas eran duplicadas y cuántas fueron a error, por columna y motivo. La diferencia debe ser 0.")

    titulo(d, "7. Indicadores")
    tabla(d, ["Indicador", "Cómo se calcula", "Fuente", "Dashboard"], IND)
    d.add_paragraph("Unidades: MM = miles de millones, M = millones (la fuente no declara moneda). No hay costos en los "
                    "datos, por eso se mide venta y no utilidad; el descuento implícito sustituye al margen.")

    titulo(d, "8. Dashboards")
    d.add_paragraph(FILTROS_COMP)
    for dsh in DASH:
        hoja(d, False)
        titulo(d, f"Dashboard {dsh['n']} — {dsh['t']}", 13)
        vineta(d, "Pregunta", dsh["preg"])
        vineta(d, "Audiencia", dsh["aud"]); vineta(d, "Frecuencia", dsh["frec"])
        vineta(d, "Filtros", ", ".join(dsh["filtros"]))
        vineta(d, "Indicadores", ", ".join(k for k, _ in dsh["kpis"]))
        titulo(d, "Visuales y por qué se eligieron", 11)
        for tit, _, por in dsh["paneles"]:
            vineta(d, tit, por)
        titulo(d, "Cómo se lee", 11)
        for t in dsh["leer"]: vineta(d, t)
        titulo(d, "Decisiones que habilita", 11)
        for t in dsh["dec"]: vineta(d, t)
        hoja(d, True)
        titulo(d, f"Prototipo · Dashboard {dsh['n']}", 12)
        img = os.path.join(DIR, "img", f"prototipo_d{DASH.index(dsh) + 1}.png")
        if os.path.exists(img): d.add_picture(img, width=Cm(25.5))

    hoja(d, False)
    titulo(d, "9. Cómo se actualiza con datos nuevos")
    for t in ["Reemplazar los archivos en la carpeta data\\examen_bi (mismos nombres).",
              "SQL Server Agent → Trabajos → Job_HM → Iniciar trabajo en el paso 1 (Stage → Datamart → cubo).",
              "Revisar el historial del Job y la auditoría DIM_AUDIT.",
              "Ejecutar sql\\03_validaciones.sql: el cuadre debe dar diferencia 0.",
              "Abrir HM_Dashboard.pbip y presionar Actualizar."]:
        vineta(d, t)

    titulo(d, "10. Confianza en el dato")
    d.add_paragraph("Cada fila que llega al Stage termina en uno de tres lugares: se carga, se descarta por ser una "
                    "copia idéntica (contada en LineasOrigen) o va a una tabla de error con su motivo y su valor "
                    "original (ErrorFactVentas, ErrorFactMetas, ErrorMaestro). Lo que entra con algún problema queda "
                    "resumido por campo en CalidadDatos, con su tratamiento. El cuadre y la auditoría demuestran que "
                    "no se pierde nada sin explicación. Los valores de este caso se ven en los dashboards: no se "
                    "escriben en el documento porque cambian con cada carga de datos.")

    ruta = os.path.join(DIR, "Caso_HM.docx")
    d.save(ruta)
    return ruta


def ps(cmd):
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)


def laminas_a_png():
    os.makedirs(os.path.join(DIR, "img"), exist_ok=True)
    ps(f'$pp = New-Object -ComObject PowerPoint.Application; '
       f'$p = $pp.Presentations.Open("{os.path.join(DIR, "HM_Modelos_Dashboards.pptx")}", $true, $false, $false); '
       f'$i = 1; foreach ($s in $p.Slides) {{ $s.Export("{os.path.join(DIR, "img")}\\prototipo_d$i.png", "PNG", 1920, 1080); $i++ }}; '
       f'$p.Close()')


def word_a_pdf(ruta):
    ps(f'$w = New-Object -ComObject Word.Application; $d = $w.Documents.Open("{ruta}", $false, $true); '
       f'$d.ExportAsFixedFormat("{ruta[:-5]}.pdf", 17); $d.Close($false); $w.Quit()')


if __name__ == "__main__":
    ppt(); laminas_a_png()
    word_a_pdf(caso())
    print("OK: Caso_HM.docx, Caso_HM.pdf, HM_Modelos_Dashboards.pptx en", DIR)
