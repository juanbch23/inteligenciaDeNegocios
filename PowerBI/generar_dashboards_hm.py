"""Construye las 5 paginas del reporte HM_Dashboard (PBIR) que pide el examen final:
  1 · Clientes                       ¿Quiénes compran y cómo?
  2 · Artículos                      ¿Qué artículos y secciones mueven la venta?
  3 · Transacciones                  ¿Cómo evolucionan las ventas y por qué canal?
  4 · Temporadas y fechas            ¿Cómo se comparan las temporadas y los años?
  5 · Metas por temporada y fechas   ¿Qué temporadas y secciones están fuera de meta?
Conexion en vivo al cubo Tabular_HM (medidas de la carpeta "7. Dashboards" de gen_bim_hm.py).
Escalable: ningun año fijo. Sin filtros se ve todo el periodo; los filtros Año, Comparar con (tabla AnioComparacion),
Mes, Canal, etc. toman sus valores del cubo, asi que si llegan años nuevos aparecen solos.
Ninguna cifra esta escrita a mano: todo sale de las medidas del cubo (la data puede cambiar).
Reemplaza los visuales de las paginas (respaldo de la version de 3 paginas en _respaldo_dashboards_v2).
Ejecutar con Power BI Desktop cerrado:  python generar_dashboards_hm.py
"""
import hashlib, json, os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(ROOT, "HM_Dashboard.Report", "definition", "pages")
D1, D2, D3, TIP = "b51b70af0c57afacc5cf", "26d4053f99dd718e5508", "29f3171285671fc539e1", "d04ce7b52687a84bc5df"
D4, D5 = "4c7e1b2a9d3f5a6b8c01", "7f2d9e4b1a6c3d5e8f02"
SCHEMA_V = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json"
SCHEMA_P = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

# paleta de los prototipos
NAVY, BG, CARD, LINE = "#1F3A5F", "#F2F4F7", "#FFFFFF", "#D5DAE1"
VERDE, AMBAR, ROJO, AZUL, GRIS, TXT, TXT2, CLARO = ("#1E8449", "#B9770E", "#B03A2E", "#2E6DA4", "#8A94A3",
                                                    "#1F2933", "#5B6573", "#E3E7EC")
FONT = "Segoe UI"


def S(v):  # coordenadas del prototipo (1920x1080) -> lienzo de Power BI (1280x720)
    return round(v * 2 / 3, 1)


# ------------------------------------------------------------------ expresiones PBIR
def lit(v):
    if isinstance(v, bool): v = "true" if v else "false"
    elif isinstance(v, (int, float)): v = f"{v}D"
    else: v = f"'{v}'"
    return {"expr": {"Literal": {"Value": v}}}


def solid(c): return {"solid": {"color": lit(c)}}
def mref(e, p): return {"Measure": {"Expression": {"SourceRef": {"Entity": e}}, "Property": p}}
def cref(e, p): return {"Column": {"Expression": {"SourceRef": {"Entity": e}}, "Property": p}}
def color_medida(e, p): return {"solid": {"color": {"expr": mref(e, p)}}}
def props(d): return [{"properties": d}]


def proj(campo, nombre=None):
    """campo = 'Tabla[Columna]' o 'Tabla[.Medida]' (las medidas del cubo empiezan con punto)."""
    e, p = campo[:-1].split("[")
    f = mref(e, p) if p.startswith(".") else cref(e, p)
    n = nombre or p.lstrip(".")
    return {"field": f, "queryRef": f"{e}.{p}", "nativeQueryRef": n, "displayName": n}


def qref(campo):
    e, p = campo[:-1].split("[")
    return f"{e}.{p}"


class Pagina:
    def __init__(self, pid, nombre):
        self.pid, self.nombre, self.visuales, self.interacciones, self.z = pid, nombre, [], [], 1000

    def add(self, clave, tipo, x, y, w, h, query=None, objects=None, vco=None, extra=None):
        vid = hashlib.md5(f"{self.pid}:{clave}".encode()).hexdigest()[:20]
        self.z += 100
        v = {"visualType": tipo}
        if query: v["query"] = query
        if objects: v["objects"] = objects
        v["visualContainerObjects"] = vco or {}
        v["drillFilterOtherVisuals"] = True
        d = {"$schema": SCHEMA_V, "name": vid,
             "position": {"x": S(x), "y": S(y), "z": self.z, "width": S(w), "height": S(h), "tabOrder": self.z},
             "visual": v}
        if extra: d.update(extra)
        self.visuales.append(d)
        return vid

    def sin_filtro(self, origen, destino):
        self.interacciones.append({"source": origen, "target": destino, "type": "NoFilter"})

    def guardar(self):
        pdir = os.path.join(PAGES, self.pid)
        vdir = os.path.join(pdir, "visuals")
        shutil.rmtree(vdir, ignore_errors=True)
        os.makedirs(vdir)
        for d in self.visuales:
            os.makedirs(os.path.join(vdir, d["name"]))
            with open(os.path.join(vdir, d["name"], "visual.json"), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        page = {"$schema": SCHEMA_P, "name": self.pid, "displayName": self.nombre, "displayOption": "FitToPage",
                "height": 720, "width": 1280,
                "objects": {"background": props({"color": solid(BG), "transparency": lit(0)})}}
        if self.interacciones:
            page["visualInteractions"] = self.interacciones
        with open(os.path.join(pdir, "page.json"), "w", encoding="utf-8") as f:
            json.dump(page, f, ensure_ascii=False, indent=2)
        print("ok", self.nombre, len(self.visuales), "visuales")


# ------------------------------------------------------------------ contenedores
def vco_vacio():
    return {"title": props({"show": lit(False)}), "subTitle": props({"show": lit(False)}),
            "background": props({"show": lit(False)}), "border": props({"show": lit(False)}),
            "dropShadow": props({"show": lit(False)}), "visualHeader": props({"show": lit(False)})}


def vco_titulo(texto, size=11):
    v = vco_vacio()
    v["title"] = props({"show": lit(True), "text": lit(texto), "fontSize": lit(size), "bold": lit(True),
                        "fontColor": solid(NAVY), "fontFamily": lit(FONT), "alignment": lit("left")})
    return v


def caja(pg, clave, x, y, w, h, color=CARD, borde=LINE, radio=6):
    obj = {"shape": props({"tileShape": lit("rectangle")}),
           "fill": [{"properties": {"fillColor": solid(color), "transparency": lit(0)}, "selector": {"id": "default"}}],
           "outline": props({"show": lit(bool(borde)), **({"lineColor": solid(borde), "weight": lit(1)} if borde else {})})}
    if radio:
        obj["shape"] = props({"tileShape": lit("rectangle"), "roundEdge": lit(radio)})
    return pg.add(clave, "shape", x, y, w, h, objects=obj, vco=vco_vacio())


def texto(pg, clave, x, y, w, h, lineas, size=10, color=TXT, bold=False):
    """Cuadro de texto: lineas = texto o lista de (texto, size, color, bold)."""
    if isinstance(lineas, str):
        lineas = [(lineas, size, color, bold)]
    parrafos = [{"textRuns": [{"value": t, "textStyle": {"fontFamily": FONT, "fontSize": f"{s}pt", "color": c,
                                                         **({"fontWeight": "bold"} if b else {})}}]}
                for t, s, c, b in lineas]
    return pg.add(clave, "textbox", x, y, w, h, objects={"general": props({"paragraphs": parrafos})}, vco=vco_vacio())


def tarjeta(pg, clave, x, y, w, h, campo, size=20, color=TXT, color_campo=None, precision=None, titulo=None, alinear="left",
            unidades=1):
    labels = {"fontSize": lit(size), "fontFamily": lit(FONT), "labelDisplayUnits": lit(unidades),
              "color": color_medida(*color_campo) if color_campo else solid(color)}
    if precision is not None: labels["labelPrecision"] = lit(precision)
    obj = {"labels": props(labels), "categoryLabels": props({"show": lit(False)}), "wordWrap": props({"show": lit(True)})}
    vco = vco_vacio()
    if titulo:
        vco["title"] = props({"show": lit(True), "text": lit(titulo), "fontSize": lit(9), "fontColor": solid(TXT2),
                              "fontFamily": lit(FONT), "alignment": lit(alinear)})
    return pg.add(clave, "card", x, y, w, h, query={"queryState": {"Values": {"projections": [proj(campo)]}}},
                  objects=obj, vco=vco)


def anillo(pg, clave, x, y, d, tabla, nombre, color_fijo=None):
    """Anillo de avance frente a la meta (0 a 100 %): medio anillo nativo de Power BI, color del semaforo."""
    a = f"{tabla}[.Anillo_{nombre}]"
    color = solid(color_fijo) if color_fijo else color_medida(tabla, f".Color_Anillo_{nombre}")
    q = {"queryState": {"Y": {"projections": [proj(a, "Avance")]},
                        "MaxValue": {"projections": [proj("FactMetas[.Gauge_Uno]", "Máximo")]}}}
    obj = {"dataPoint": props({"fill": color}), "labels": props({"show": lit(False)}),
           "calloutValue": props({"show": lit(False)}), "target": props({"show": lit(False)})}
    v = vco_vacio(); v["visualTooltip"] = props({"show": lit(False)})
    return pg.add(clave, "gauge", x, y, d, d * 0.8, query=q, objects=obj, vco=v)


def kpi(pg, clave, x, y, w, nombre, valor, detalle=None, tabla_anillo=None, anillo_nombre=None, color_valor=None,
        color_fijo=None, precision=None, size=17, unidades=1):
    """Tarjeta KPI del prototipo: caja blanca + anillo (o sin anillo) + nombre + valor + detalle."""
    caja(pg, clave + "_caja", x, y, w, 140)
    tx = x + 128
    if anillo_nombre:
        anillo(pg, clave + "_anillo", x + 4, y + 22, 120, tabla_anillo, anillo_nombre, color_fijo)
    else:
        tx = x + 24
    texto(pg, clave + "_nombre", tx, y + 12, w - (tx - x) - 10, 34, nombre, 9, TXT2)
    tarjeta(pg, clave + "_valor", tx - 6, y + 30, w - (tx - x) - 4, 82, valor, size=size,
            color_campo=color_valor, color=color_fijo or TXT, precision=precision, unidades=unidades)
    if detalle:
        tarjeta(pg, clave + "_detalle", tx - 6, y + 96, w - (tx - x) - 4, 42, detalle, size=8, color=TXT2)


def panel(pg, clave, x, y, w, h, titulo, nota):
    caja(pg, clave + "_panel", x, y, w, h)
    texto(pg, clave + "_titulo", x + 14, y + 10, w - 28, 40, titulo, 11, NAVY, True)
    texto(pg, clave + "_nota", x + 14, y + h - 46, w - 28, 40, nota, 8, TXT2)


def encabezado(pg, pregunta, problema_medida, linea):
    caja(pg, "hdr", 40, 30, 1840, 150, NAVY, None, 0)
    texto(pg, "hdr_preg", 60, 38, 1100, 62, pregunta, 20, "#FFFFFF", True)
    if "[" in problema_medida:   # narrativa calculada por el cubo
        tarjeta(pg, "hdr_problema", 54, 90, 1810, 60, problema_medida, size=9, color="#FFFFFF")
    else:                        # texto fijo, sin cifras
        texto(pg, "hdr_problema", 60, 96, 1100, 48, problema_medida, 9, "#FFFFFF")
    texto(pg, "hdr_linea", 60, 146, 1800, 32, linea, 7, "#C9D3E0")


def acciones(pg, titulo, items):
    caja(pg, "acc", 40, 920, 1840, 118, "#E8EEF6", "#C9D3E0")
    texto(pg, "acc_tit", 60, 928, 600, 36, titulo, 11, NAVY, True)
    for i, t in enumerate(items):
        texto(pg, f"acc_{i}", 60 + i * 455, 966, 440, 68, f"{i + 1}. {t}", 9, TXT)


def pie(pg, extra=""):
    texto(pg, "pie", 40, 1040, 1840, 36,
          "Semáforo: verde cumple la meta, ámbar a menos de 10 % de la meta, rojo más lejos. El anillo muestra el avance "
          "frente a la meta. Cubo Tabular_HM (datos limpios del DWH_HM); venta = price × 40 000; MM = miles de millones. " + extra,
          7, TXT2)


# ------------------------------------------------------------------ segmentadores (filtros)
def filtro_default(campo, valor):
    e, p = campo[:-1].split("[")
    v = f"{valor}L" if isinstance(valor, int) else f"'{valor}'"
    return {"filter": {"Version": 2, "From": [{"Name": "t", "Entity": e, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}},
                                                                                   "Property": p}}],
                                                       "Values": [[{"Literal": {"Value": v}}]]}}}]}}


def segmentador(pg, clave, x, y, w, h, campo, nombre, botones=False, defecto=None):
    general = {"orientation": lit(1)} if botones else {}
    if defecto is not None:
        general["filter"] = filtro_default(campo, defecto)
    obj = {"data": props({"mode": lit("Basic" if botones else "Dropdown")}),
           "selection": props({"singleSelect": lit(True), "strictSingleSelect": lit(bool(botones)),
                               "selectAllCheckboxEnabled": lit(False)}),
           "items": props({"textSize": lit(10), "fontFamily": lit(FONT), "fontColor": solid(NAVY),
                           "background": solid("#FFFFFF"), "outline": lit("Frame")}),
           "header": props({"show": lit(not botones), "text": lit(nombre), "textSize": lit(8),
                            "fontColor": solid("#FFFFFF"), "fontFamily": lit(FONT)})}
    if general:
        obj["general"] = props(general)
    q = {"queryState": {"Values": {"projections": [dict(proj(campo, nombre), active=True)]}},
         "sortDefinition": {"sort": [{"field": proj(campo)["field"], "direction": "Ascending"}]}}
    return pg.add(clave, "slicer", x, y, w, h, query=q, objects=obj, vco=vco_vacio())


# ------------------------------------------------------------------ graficos
def ejes(size=9):
    return {"categoryAxis": props({"show": lit(True), "fontSize": lit(size), "fontFamily": lit(FONT), "labelColor": solid(TXT2),
                                   "showAxisTitle": lit(False)}),
            "valueAxis": props({"show": lit(False), "gridlineShow": lit(False), "showAxisTitle": lit(False)})}


def columnas(pg, clave, x, y, w, h, categoria, medidas, nombres, colores=None, color_campo=None, serie=None,
             serie_colores=None, etiquetas_fmt=None, leyenda=False, tipo="clusteredColumnChart", precision=None, gap=None,
             orden_medida=False):
    qs = {"Y": {"projections": [proj(m, n) for m, n in zip(medidas, nombres)]}}
    if categoria: qs["Category"] = {"projections": [proj(categoria)]}
    if serie: qs["Series"] = {"projections": [proj(serie)]}
    q = {"queryState": qs}
    if orden_medida:   # de mayor a menor
        q["sortDefinition"] = {"sort": [{"field": proj(medidas[0])["field"], "direction": "Descending"}]}
    elif categoria:
        q["sortDefinition"] = {"sort": [{"field": proj(categoria)["field"], "direction": "Ascending"}]}
    lab = {"show": lit(True), "fontSize": lit(10), "color": solid(TXT), "fontFamily": lit(FONT), "labelDisplayUnits": lit(1)}
    if precision is not None: lab["labelPrecision"] = lit(precision)
    obj = {**ejes(), "labels": props(lab), "legend": props({"show": lit(leyenda), "position": lit("Top"), "fontSize": lit(9)})}
    dp = []
    if color_campo:
        dp.append({"properties": {"fill": color_medida(*color_campo)},
                   "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}})
    if colores and len(medidas) == 1:
        dp.append({"properties": {"fill": solid(colores[0])}})          # color de la unica serie
    for m, c in zip(medidas, colores or []):
        dp.append({"properties": {"fill": solid(c)}, "selector": {"metadata": qref(m)}})
    for valor, c in (serie_colores or {}).items():
        e, p = serie[:-1].split("[")
        dp.append({"properties": {"fill": solid(c)}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": cref(e, p), "Right": {"Literal": {"Value": valor}}}}}]}})
    if dp: obj["dataPoint"] = dp
    if gap is not None: obj["layout"] = props({"interSeriesGap": lit(gap)})
    return pg.add(clave, tipo, x, y, w, h, query=q, objects=obj, vco=vco_vacio())


# ================================================================== filtros comunes (nada fijo: los valores salen del cubo)
def filtros_cabecera(pg, lista):
    """Segmentadores desplegables a la derecha del encabezado. lista = [(campo, nombre, defecto)].
    Sin valor por defecto se ve TODO el periodo; el usuario elige año, año a comparar, mes, etc."""
    ids = {}
    x = 1880 - len(lista) * 150
    for campo, nombre, defecto in lista:
        ids[nombre] = segmentador(pg, "f_" + nombre, x, 36, 144, 84, campo, nombre, defecto=defecto)
        x += 150
    return ids


ANIO = ("DimFecha[Anio]", "Año", None)
COMPARAR = ("AnioComparacion[Comparar con]", "Comparar con", None)
MES = ("DimFecha[Nombre_Mes]", "Mes", None)
CANAL = ("DimCanal[NombreCanal]", "Canal", None)
LINEA_FILTROS = ("sin filtros se ve todo el periodo; elige Año y Comparar con para comparar los mismos días "
                 "(si no eliges con qué comparar, se usa el año anterior)")


def centro_dona(pg, clave, cx, cy, campo, color=NAVY, precision=1):
    """Tarjeta blanca en el centro de una dona (tapa la etiqueta central automática de Power BI)."""
    c = tarjeta(pg, clave, cx - 70, cy - 34, 140, 68, campo, size=14, color=color, precision=precision)
    pg.visuales[-1]["visual"]["visualContainerObjects"]["background"] = props({"show": lit(True), "color": solid(CARD),
                                                                                "transparency": lit(0)})
    return c


# ================================================================== piezas reutilizables
TEMPORADA = ("DimTemporada[Temporada]", "Temporada", None)


def dona(pg, clave, x, y, w, h, categoria, medida, colores=None):
    """Dona con % del total; colores = {valor: color} (sin colores fijos usa la paleta del tema)."""
    e, p = categoria[:-1].split("[")
    q = {"queryState": {"Category": {"projections": [proj(categoria)]}, "Y": {"projections": [proj(medida)]}}}
    obj = {"legend": props({"show": lit(True), "position": lit("Bottom"), "fontSize": lit(9)}),
           "labels": props({"show": lit(True), "labelStyle": lit("Percent of total"), "fontSize": lit(10),
                            "color": solid(TXT), "percentageLabelPrecision": lit(1)}),
           "slices": props({"innerRadiusRatio": lit(62)})}
    if colores:
        obj["dataPoint"] = [{"properties": {"fill": solid(c)}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": cref(e, p), "Right": {"Literal": {"Value": f"'{v}'"}}}}}]}}
            for v, c in colores.items()]
    return pg.add(clave, "donutChart", x, y, w, h, query=q, objects=obj, vco=vco_vacio())


def linea(pg, clave, x, y, w, h, categoria, medidas, nombres, colores=None, serie=None):
    """Linea por categoria (meses, periodos). Con serie = una linea por valor (p. ej. una por año)."""
    qs = {"Category": {"projections": [proj(categoria)]},
          "Y": {"projections": [proj(m, n) for m, n in zip(medidas, nombres)]}}
    if serie: qs["Series"] = {"projections": [proj(serie)]}
    q = {"queryState": qs, "sortDefinition": {"sort": [{"field": proj(categoria)["field"], "direction": "Ascending"}]}}
    obj = {**ejes(8), "valueAxis": props({"show": lit(True), "gridlineShow": lit(True), "gridlineColor": solid("#EEF1F4"),
                                          "fontSize": lit(8), "labelColor": solid(TXT2), "labelDisplayUnits": lit(1)}),
           "legend": props({"show": lit(True), "position": lit("Top"), "fontSize": lit(9)}),
           "lineStyles": props({"strokeWidth": lit(3), "showMarker": lit(True), "lineChartType": lit("smooth")})}
    if colores:
        obj["dataPoint"] = [{"properties": {"fill": solid(c)}, "selector": {"metadata": qref(m)}}
                            for m, c in zip(medidas, colores)]
    return pg.add(clave, "lineChart", x, y, w, h, query=q, objects=obj, vco=vco_vacio())


def mezcla_canal(pg, x):
    """Dona tienda/online + variacion de cada canal contra el año de comparacion."""
    panel(pg, "p_mezcla", x, 360, 520, 540, "Mezcla de canal",
          "Participación de cada canal y su variación contra el año de comparación (elige un año).")
    dona(pg, "g_mezcla", x + 15, 420, 330, 430, "DimCanal[NombreCanal]", "FactVentas[.Ventas]",
         {"Online": AZUL, "Tienda fisica": ROJO})
    centro_dona(pg, "c_mezcla", x + 180, 612, "FactVentas[.%Ventas_Online]", AZUL)
    texto(pg, "t_inter", x + 355, 450, 160, 30, "Variación", 9, TXT2)
    tarjeta(pg, "c_tienda", x + 348, 470, 170, 78, "FactVentas[.Interanual_Tienda_I]", size=17,
            color_campo=("FactVentas", ".Color_Interanual_Tienda"))
    texto(pg, "t_tienda", x + 355, 540, 160, 30, "tienda", 9, TXT2)
    tarjeta(pg, "c_online", x + 348, 580, 170, 78, "FactVentas[.Interanual_Online_I]", size=17,
            color_campo=("FactVentas", ".Color_Interanual_Online"))
    texto(pg, "t_online", x + 355, 650, 160, 30, "online", 9, TXT2)
    tarjeta(pg, "c_vs", x + 348, 690, 170, 70, "DimFecha[.Txt_Comparacion_Tarjeta]", size=8, color=TXT2)


# ================================================================== Dashboard 1: Clientes
def dashboard_clientes():
    pg = Pagina(D1, "1 · Clientes")
    encabezado(pg, "¿Quiénes compran y cómo?", "FactVentas[.Narrativa_Cliente]",
               "Dashboard 1 · Análisis de clientes · marketing y CRM · mensual · " + LINEA_FILTROS)
    filtros_cabecera(pg, [ANIO, COMPARAR, MES, CANAL, ("DimCliente[RangoEdad]", "Edad", None)])

    kpi(pg, "k1", 40, 200, 352, "Clientes que compran", "FactVentas[.Clientes_Unicos]", color_fijo=NAVY)
    kpi(pg, "k2", 412, 200, 352, "Clientes nuevos", "DimCliente[.Clientes_Nuevos]", "DimCliente[.Det_Nuevos]",
        "DimCliente", "Nuevos", ("DimCliente", ".Color_Anillo_Nuevos"))
    kpi(pg, "k3", 784, 200, 352, "Retención de clientes", "FactVentas[.Retencion_I]", "FactVentas[.Det_Retencion]",
        "FactVentas", "Retencion", ("FactVentas", ".Color_Anillo_Retencion"))
    kpi(pg, "k4", 1156, 200, 352, "Clientes omnicanal", "FactVentas[.%Clientes_Omnicanal]", "FactVentas[.Det_Omnicanal]",
        "FactVentas", "Omnicanal", ("FactVentas", ".Color_Anillo_Omnicanal"), precision=1)
    kpi(pg, "k5", 1528, 200, 352, "Penetración club activo", "FactVentas[.%Penetracion_Club]", "FactVentas[.Det_Club]",
        "FactVentas", "Club", ("FactVentas", ".Color_Anillo_Club"), precision=1)

    panel(pg, "p1", 40, 360, 445, 540, "¿Quién genera la venta?",
          "Clientes ordenados por lo que compran: el 20 % que más compra frente al resto.")
    dona(pg, "g_conc", 55, 410, 415, 445, "DimCliente[SegmentoValor]", "FactVentas[.Ventas]",
         {"1. Top 20 %": NAVY, "2. Siguiente 30 %": GRIS, "3. Resto 50 %": "#C9D3E0"})
    centro_dona(pg, "c_conc", 262, 610, "FactVentas[.%Ventas_Top20_Clientes]")

    panel(pg, "p2", 505, 360, 445, 540, "Clientes por rango de edad",
          "Clientes que compraron en el filtro. \"Sin dato\": el archivo no trae su edad.")
    columnas(pg, "g_edad", 520, 420, 415, 430, "DimCliente[RangoEdad]", ["FactVentas[.Clientes_Unicos]"],
             ["Clientes"], colores=[NAVY])

    panel(pg, "p3", 970, 360, 445, 540, "Venta por cliente según cómo compra (M)",
          "Omnicanal: compra en tienda y online. Un canal: solo en uno de los dos.")
    columnas(pg, "g_vpc", 985, 420, 415, 430, "DimCliente[TipoCanal]", ["FactVentas[.Ventas_por_Cliente_M]"],
             ["Venta por cliente"], colores=[GRIS])
    pg.visuales[-1]["visual"]["objects"]["dataPoint"].append(
        {"properties": {"fill": solid(VERDE)}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": cref("DimCliente", "TipoCanal"), "Right": {"Literal": {"Value": "'Omnicanal'"}}}}}]}})

    panel(pg, "p4", 1435, 360, 445, 540, "Clientes nuevos por año",
          "Primera compra en cada año. El primer año con datos cuenta como nuevos a todos sus clientes.")
    columnas(pg, "g_nuevos", 1450, 420, 415, 430, "DimFecha[Anio]", ["DimCliente[.Clientes_Nuevos]"],
             ["Clientes nuevos"], colores=[NAVY])

    acciones(pg, "Palancas", ["Campañas por rango de edad según su participación en la venta.",
                              "Llevar al cliente de un canal a comprar en los dos (omnicanal).",
                              "Activar socios del club en su primera compra.",
                              "Cuidar al 20 % de clientes que concentra la venta."])
    pie(pg)
    pg.guardar()


# ================================================================== Dashboard 2: Articulos
def dashboard_articulos():
    pg = Pagina(D2, "2 · Artículos")
    encabezado(pg, "¿Qué artículos y secciones mueven la venta?",
               "Qué líneas, grupos de producto y secciones explican la venta, y cuánto se vende con descuento.",
               "Dashboard 2 · Análisis de artículos · compras, producto y pricing · mensual · " + LINEA_FILTROS)
    filtros_cabecera(pg, [ANIO, COMPARAR, MES, CANAL, ("DimArticulo[GrupoIndice]", "Línea", None)])

    kpi(pg, "k1", 40, 200, 352, "Artículos vendidos", "FactVentas[.Articulos_Distintos]", color_fijo=NAVY)
    kpi(pg, "k2", 412, 200, 352, "Ventas (MM)", "FactVentas[.Ventas_MM]", "FactVentas[.Det_Ventas]", color_fijo=NAVY)
    kpi(pg, "k3", 784, 200, 352, "Artículos por cesta", "FactVentas[.Articulos_por_Cesta]", color_fijo=NAVY, precision=2)
    kpi(pg, "k4", 1156, 200, 352, "Descuento implícito", "FactVentas[.%Descuento_Implicito]",
        color_valor=("FactVentas", ".Color_Descuento"), precision=1)
    kpi(pg, "k5", 1528, 200, 352, "Líneas con más de 30 % de descuento", "FactVentas[.%Lineas_Descuento_30]",
        color_fijo=ROJO, precision=1)

    panel(pg, "p1", 40, 360, 445, 540, "Venta por línea",
          "Línea de H&M (índice del catálogo): participación en la venta del filtro.")
    dona(pg, "g_linea", 55, 410, 415, 445, "DimArticulo[GrupoIndice]", "FactVentas[.Ventas]")
    centro_dona(pg, "c_linea", 262, 610, "FactVentas[.Ventas_MM]", precision=0)

    panel(pg, "p2", 505, 360, 445, 540, "Venta por grupo de producto (MM)",
          "De mayor a menor venta en el filtro.")
    columnas(pg, "g_grupo", 520, 420, 415, 430, "DimArticulo[GrupoProducto]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
             colores=[NAVY], tipo="clusteredBarChart", orden_medida=True, precision=0)

    panel(pg, "p3", 970, 360, 445, 540, "Secciones que más venden (MM)",
          "De mayor a menor; desliza para ver todas las secciones.")
    columnas(pg, "g_seccion", 985, 420, 415, 430, "DimDepartamento[Seccion]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
             colores=[AZUL], tipo="clusteredBarChart", orden_medida=True, precision=0)

    panel(pg, "p4", 1435, 360, 445, 540, "Venta por banda de descuento (MM)",
          "Descuento de cada venta frente al precio más alto del mismo artículo (precio de lista).")
    columnas(pg, "g_banda", 1450, 420, 415, 430, "FactVentas[BandaDescuento]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
             colores=[GRIS], precision=0)

    acciones(pg, "Decisiones", ["Asegurar stock de los grupos y secciones que más venden.",
                                "Revisar las secciones con poca venta antes de la próxima temporada.",
                                "Controlar las rebajas de más de 30 %.",
                                "Venta cruzada para subir los artículos por cesta."])
    pie(pg)
    pg.guardar()


# ================================================================== Dashboard 3: Transacciones
def dashboard_transacciones():
    pg = Pagina(D3, "3 · Transacciones")
    encabezado(pg, "¿Cómo evolucionan las ventas y por qué canal?", "FactVentas[.Narrativa_Estrategica]",
               "Dashboard 3 · Análisis de las transacciones · gerencia comercial y finanzas · mensual · " + LINEA_FILTROS)
    filtros_cabecera(pg, [ANIO, COMPARAR, MES, CANAL, TEMPORADA])

    kpi(pg, "k1", 40, 200, 352, "Ventas (MM)", "FactVentas[.Ventas_MM]", "FactVentas[.Det_Ventas]", color_fijo=NAVY)
    kpi(pg, "k2", 412, 200, 352, "Líneas de venta", "FactVentas[.Transacciones]", color_fijo=NAVY)
    kpi(pg, "k3", 784, 200, 352, "Cestas (cliente, día y canal)", "FactVentas[.Cestas]", color_fijo=NAVY)
    kpi(pg, "k4", 1156, 200, 352, "Ticket por cesta (M)", "FactVentas[.Ticket_Cesta]", color_fijo=NAVY,
        precision=1, unidades=1000000)
    kpi(pg, "k5", 1528, 200, 352, "Participación online", "FactVentas[.%Ventas_Online]", "FactVentas[.Det_Online]",
        "FactVentas", "Online", color_fijo=AZUL, precision=1)

    panel(pg, "p1", 40, 360, 760, 540, "Ventas mes a mes (MM)",
          "Línea oscura: venta de cada mes. Línea gris: el mismo mes del año de comparación (por defecto, el anterior).")
    linea(pg, "g_linea", 55, 420, 730, 430, "DimFecha[Periodo]", ["FactVentas[.Ventas_MM]", "FactVentas[.Ventas_AA_MM]"],
          ["Ventas", "Mismo mes del año de comparación"], [NAVY, GRIS])

    mezcla_canal(pg, 820)

    panel(pg, "p3", 1360, 360, 520, 540, "Ventas por día de la semana (MM)",
          "En qué días se concentra la venta del filtro.")
    columnas(pg, "g_dia", 1375, 420, 490, 430, "DimFecha[Nombre_Dia_Semana]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
             colores=[NAVY], precision=0)

    acciones(pg, "Decisiones", ["Explicar la variación de cada mes frente al año de comparación.",
                                "Reforzar el canal que pierde participación.",
                                "Planificar personal y stock según los días de más venta.",
                                "Seguir el ticket por cesta junto con la venta."])
    pie(pg)
    pg.guardar()


# ================================================================== Dashboard 4: Temporadas y fechas
def dashboard_temporadas():
    pg = Pagina(D4, "4 · Temporadas y fechas")
    encabezado(pg, "¿Cómo se comparan las temporadas y los años?",
               "Cada estación frente a la misma estación de otros años, y cada mes frente al mismo mes de otros años.",
               "Dashboard 4 · Análisis comparativo entre temporadas y fechas · gerencia comercial · por temporada · "
               + LINEA_FILTROS)
    ids = filtros_cabecera(pg, [ANIO, COMPARAR, CANAL, ("DimTemporada[Estacion]", "Estación", None), TEMPORADA])

    kpi(pg, "k1", 40, 200, 352, "Ventas (MM)", "FactVentas[.Ventas_MM]", "FactVentas[.Det_Ventas]", color_fijo=NAVY)
    kpi(pg, "k2", 412, 200, 352, "Mismo periodo del año de comparación (MM)", "FactVentas[.Ventas_AA_MM_Txt]",
        "DimFecha[.Txt_Comparacion_Tarjeta]", color_fijo=GRIS)
    kpi(pg, "k3", 784, 200, 352, "Crecimiento interanual", "FactVentas[.Interanual_Total_I]",
        color_valor=("FactVentas", ".Color_Interanual"))
    kpi(pg, "k4", 1156, 200, 352, "Crecimiento en tienda", "FactVentas[.Interanual_Tienda_I]",
        color_valor=("FactVentas", ".Color_Interanual_Tienda"))
    kpi(pg, "k5", 1528, 200, 352, "Crecimiento online", "FactVentas[.Interanual_Online_I]",
        color_valor=("FactVentas", ".Color_Interanual_Online"))

    panel(pg, "p0", 40, 360, 390, 540, "Ventas de cada año (MM)",
          "Cuánto se vendió en cada año. Un año con pocos meses de datos sale más bajo.")
    g0 = columnas(pg, "g_anio", 55, 420, 360, 430, "DimFecha[Anio]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
                  colores=[NAVY], precision=0)

    panel(pg, "p1", 450, 360, 470, 540, "Ventas por estación y año (MM)",
          "Cada estación junto a la misma estación de los otros años. Una temporada con pocos días de datos sale más baja.")
    g1 = columnas(pg, "g_estacion", 465, 420, 440, 430, "DimTemporada[Estacion]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
                  serie="DimTemporada[Anio]", leyenda=True, precision=0)

    panel(pg, "p2", 940, 360, 500, 540, "Ventas por mes y año (MM)",
          "Una línea por año: compara el mismo mes entre años.")
    g2 = linea(pg, "g_mes_anio", 955, 420, 470, 430, "DimFecha[Nombre_Mes]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
               serie="DimFecha[Anio]")

    panel(pg, "p3", 1460, 360, 420, 540, "Ventas por temporada (MM)",
          "Cada venta va a su temporada por su fecha. Elige una en el filtro Temporada para verla sola.")
    columnas(pg, "g_temporada", 1475, 420, 390, 430, "DimTemporada[Temporada]", ["FactVentas[.Ventas_MM]"], ["Ventas"],
             colores=[NAVY], precision=0)

    for f in ("Año", "Comparar con"):   # las comparaciones muestran todos los años
        for g in (g0, g1, g2):
            pg.sin_filtro(ids[f], g)

    acciones(pg, "Decisiones", ["Comparar cada temporada con la misma del año anterior antes de fijar metas.",
                                "Planificar compras según la estación que más crece.",
                                "Revisar los meses que caen frente al año anterior.",
                                "Separar el efecto de canal (tienda / online) en cada temporada."])
    pie(pg)
    pg.guardar()


# ================================================================== Dashboard 5: Metas por temporada y fechas
def dashboard_metas():
    pg = Pagina(D5, "5 · Metas por temporada y fechas")
    encabezado(pg, "¿Qué temporadas y secciones están fuera de meta?", "FactMetas[.Narrativa_Metas]",
               "Dashboard 5 · Análisis con las metas por temporada y fechas · jefes de sección y de temporada · "
               "meta de GoalsHyM tal como viene (por escenario, sección, temporada y mes) · escenario oficial por defecto: "
               "Escenario 2")
    ids = filtros_cabecera(pg, [("FactMetas[Escenario]", "Escenario", "Escenario 2"), ANIO, MES, TEMPORADA,
                                ("DimDepartamento[Seccion]", "Sección", None)])

    kpi(pg, "k1", 40, 200, 445, "Cumplimiento de meta", "FactMetas[.%Cumplimiento_Meta]", "FactMetas[.Det_Cumplimiento]",
        "FactMetas", "Cumplimiento", ("FactMetas", ".Color_Anillo_Cumplimiento"), precision=1)
    kpi(pg, "k2", 505, 200, 445, "Peor temporada", "FactMetas[.Cumpl_Peor_Temporada]", "FactMetas[.Peor_Temporada]",
        "FactMetas", "Peor_Temporada", ("FactMetas", ".Color_Anillo_Peor_Temporada"), precision=1)
    kpi(pg, "k3", 970, 200, 445, "Secciones que cumplen", "FactMetas[.Secciones_Cumplen_Txt]", "FactMetas[.Det_Secciones]",
        "FactMetas", "Secciones", ("FactMetas", ".Color_Anillo_Secciones"))
    kpi(pg, "k4", 1435, 200, 445, "Secciones bajo 50 %", "FactMetas[.Secciones_Bajo_50_Txt]", "FactMetas[.Det_Bajo_50]",
        "FactMetas", "Bajo_50", color_fijo=ROJO)

    panel(pg, "p1", 40, 360, 440, 540, "Velocímetro de meta",
          "Línea = meta 100 %. Abajo, el cumplimiento con cada escenario de GoalsHyM.")
    q = {"queryState": {"Y": {"projections": [proj("FactMetas[.%Cumplimiento_Meta]", "Cumplimiento")]},
                        "MaxValue": {"projections": [proj("FactMetas[.Gauge_Max]", "Máximo")]},
                        "TargetValue": {"projections": [proj("FactMetas[.Gauge_Meta]", "Meta")]}}}
    obj = {"dataPoint": props({"fill": color_medida("FactMetas", ".Color_Cumplimiento"), "target": solid(TXT)}),
           "calloutValue": props({"fontSize": lit(20), "color": color_medida("FactMetas", ".Color_Cumplimiento"),
                                  "labelPrecision": lit(1)}),
           "labels": props({"show": lit(True), "fontSize": lit(8)}), "target": props({"show": lit(True)})}
    pg.add("g_gauge", "gauge", 55, 405, 410, 250, query=q, objects=obj, vco=vco_vacio())
    esc = columnas(pg, "g_esc", 55, 655, 410, 205, "FactMetas[Escenario]", ["FactMetas[.%Cumplimiento_Meta]"],
                   ["Cumplimiento"], color_campo=("FactMetas", ".Color_Cumplimiento"), precision=1,
                   tipo="clusteredBarChart")
    pg.sin_filtro(ids["Escenario"], esc)     # siempre se ven todos los escenarios

    panel(pg, "p2", 500, 360, 520, 540, "Cumplimiento por temporada (%)",
          "Meta 100 %. Cada venta va a su temporada por su fecha; la meta trae su temporada.")
    columnas(pg, "g_temp", 515, 420, 490, 430, "DimTemporada[Temporada]", ["FactMetas[.%Cumplimiento_Meta]"],
             ["Cumplimiento"], color_campo=("FactMetas", ".Color_Cumplimiento"), precision=0)

    panel(pg, "p3", 1040, 360, 440, 540, "Cumplimiento por mes (%)",
          "La meta viene por mes: se compara con la venta del mismo mes.")
    columnas(pg, "g_mes", 1055, 420, 410, 430, "DimFecha[Periodo]", ["FactMetas[.%Cumplimiento_Meta]"],
             ["Cumplimiento"], color_campo=("FactMetas", ".Color_Cumplimiento"), precision=0)

    panel(pg, "p4", 1500, 360, 380, 540, "Extremos de cumplimiento",
          "Las 5 secciones con mayor y menor cumplimiento en el filtro.")
    texto(pg, "t_top", 1515, 405, 350, 28, "▲ Mayor cumplimiento", 9, VERDE, True)
    columnas(pg, "g_top", 1505, 430, 370, 205, "DimDepartamento[Seccion]", ["FactMetas[.Cumplimiento_Top5]"],
             ["Cumplimiento"], colores=[VERDE], tipo="clusteredBarChart", precision=0)
    texto(pg, "t_bot", 1515, 640, 350, 28, "▼ Menor cumplimiento", 9, ROJO, True)
    columnas(pg, "g_bot", 1505, 665, 370, 190, "DimDepartamento[Seccion]", ["FactMetas[.Cumplimiento_Bottom5]"],
             ["Cumplimiento"], colores=[ROJO], tipo="clusteredBarChart", precision=1)

    acciones(pg, "Atender", ["Validar con el negocio la escala y el periodo de la meta de GoalsHyM.",
                             "Seguimiento mensual de venta vs meta por temporada.",
                             "Plan de recuperación para la temporada más lejos de la meta.",
                             "Revisar con comercial las secciones bajo 50 %."])
    pie(pg)
    pg.guardar()


if __name__ == "__main__":
    dashboard_clientes(); dashboard_articulos(); dashboard_transacciones(); dashboard_temporadas(); dashboard_metas()
    pj = os.path.join(PAGES, "pages.json")
    with open(pj, encoding="utf-8") as f: pp = json.load(f)
    activa = {"1": D1, "2": D2, "3": D3, "4": D4, "5": D5}[os.environ.get("HM_PAGINA", "1")]   # pagina que abre Power BI
    pp["pageOrder"] = [D1, D2, D3, D4, D5, TIP]; pp["activePageName"] = activa
    with open(pj, "w", encoding="utf-8") as f: json.dump(pp, f, ensure_ascii=False, indent=2)
    print("listo: abrir HM_Dashboard.pbip en Power BI Desktop")
