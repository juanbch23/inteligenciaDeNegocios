"""Ajustes de formato del informe H&M que el MCP no cubre (mismos patrones PBIR que
LABORATORIO-TABULARES\\PowerBI\\ajustes_pbir.py, verificados en Power BI Desktop). Idempotente.
Ejecutar con Power BI Desktop cerrado:  python ajustes_pbir_hm.py"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(ROOT, "HM_Dashboard.Report", "definition")
PAGES = os.path.join(REPORT, "pages")
P1, P2, P3, TIP = "a09bd4023024d8abccf9", "a701aeaebab801b0c5b5", "e3bef6c891cf87e42497", "d04ce7b52687a84bc5df"

VERDE, CELESTE, AZUL_OSCURO, AZUL, NARANJA = "#9CCB86", "#A6C8E6", "#12239E", "#118DFF", "#E66C37"
ROJO_IND, VERDE_IND, GRIS = "#E3485A", "#7DC67E", "#6B7280"

# ------------------------------------------------------------------ helpers PBIR
def lit(v):
    if isinstance(v, bool): v = "true" if v else "false"
    elif isinstance(v, (int, float)): v = f"{v}D"
    else: v = f"'{v}'"
    return {"expr": {"Literal": {"Value": v}}}

def mref(entity, prop): return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
def solid(c): return {"solid": {"color": c if isinstance(c, dict) else lit(c)}}
def cmp(kind, left, value): return {"Comparison": {"ComparisonKind": kind, "Left": left, "Right": {"Literal": {"Value": f"{value}D"}}}}
def conditional(cases): return {"expr": {"Conditional": {"Cases": [{"Condition": c, "Value": {"Literal": {"Value": f"'{col}'"}}} for c, col in cases]}}}
GE, GT, LT, LE = 2, 1, 3, 4
WILDCARD = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}

def path(page, vid): return os.path.join(PAGES, page, "visuals", vid, "visual.json")

def edit(page, vid):
    def deco(fn):
        p = path(page, vid)
        with open(p, encoding="utf-8") as f: d = json.load(f)
        fn(d["visual"])
        with open(p, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
        print("ok", fn.__name__, vid)
        return fn
    return deco

def props(v, tree, cat, values, selector=None):
    lst = v.setdefault(tree, {}).setdefault(cat, [])
    entry = next((e for e in lst if e.get("selector") == selector), None)
    if entry is None:
        entry = {"properties": {}}
        if selector is not None: entry["selector"] = selector
        lst.append(entry)
    entry["properties"].update(values)

def obj(v, cat, values, selector=None): props(v, "objects", cat, values, selector)
def box(v, cat, values): props(v, "visualContainerObjects", cat, values)
def reset(v, tree, *cats):
    for c in cats: v.get(tree, {}).pop(c, None)

def title(v, text=None, measure=None, size=11):
    t = {"show": lit(True), "alignment": lit("center"), "fontSize": lit(size), "bold": lit(True)}
    if text is not None: t["text"] = lit(text)
    if measure is not None: t["text"] = {"expr": mref(*measure)}
    box(v, "title", t)

def alias(v, bucket, names):
    for p, n in zip(v["query"]["queryState"][bucket]["projections"], names):
        if n: p["displayName"] = n; p["nativeQueryRef"] = n

def slicer(v, name, single=False, between=False):
    alias(v, "Values", [name])
    obj(v, "header", {"show": lit(True), "text": lit(name)})
    if between:
        obj(v, "data", {"mode": lit("Between")})
    obj(v, "selection", {"strictSingleSelect": lit(single), "selectAllCheckboxEnabled": lit(not single)})

def card(v, name, size=20, units=None):
    alias(v, "Values", [name])
    obj(v, "labels", {"fontSize": lit(size)})
    if units is not None: obj(v, "labels", {"labelDisplayUnits": lit(units)})   # 1 = ninguna (cifra completa)
    obj(v, "categoryLabels", {"show": lit(True), "fontSize": lit(10)})

def color_rule(v, measure, cases):
    reset(v, "objects", "dataPoint")
    obj(v, "dataPoint", {"fill": {"solid": {"color": conditional(cases)}}}, WILDCARD)

def signo(m): return [(cmp(LT, m, 0), ROJO_IND), (cmp(GE, m, 0), VERDE_IND)]

# ================================================================== Página 1: Resumen de Ventas
for vid, name, between in [("156941df6d0548a32d8c", "Fecha", True), ("f71d8c653f109f049422", "Canal", False),
                           ("f05dd0e0f7d695cd1e5e", "Grupo índice", False), ("bdeebde6d996bf1c582d", "Temporada", False),
                           ("674ebd35a173a749dc01", "Rango de edad", False),
                           ("55560c71d05b63f144ac", "Grupo índice (solo Pareto)", False)]:
    @edit(P1, vid)
    def slicer_p1(v, name=name, between=between):
        slicer(v, name, between=between)
        if name.endswith("(solo Pareto)"): obj(v, "data", {"mode": lit("Basic")})   # lista con casillas, como la guía

for vid, name in [("2e14852cee13f0621fb5", "Ventas"), ("a47042751b51f25561f4", "Artículos vendidos"),
                  ("26d64accbc6273412c5a", "Clientes únicos"), ("9d7e61058b42d6eb7a28", "Ticket promedio"),
                  ("4b81c1d53c15a20c579e", "Ventas por cliente"), ("8fb275eb6327675c6254", "Acumulado anual (YTD)"),
                  ("80f98746fe4e7ea13427", "% Ventas online")]:
    @edit(P1, vid)
    def card_p1(v, name=name): card(v, name, units=1 if name in ("Artículos vendidos", "Clientes únicos") else None)

@edit(P1, "b04bf593e2f6029df332")
def pie(v):
    title(v, "Ventas por grupo índice")
    obj(v, "labels", {"show": lit(True), "labelStyle": lit("Percent of total")})

@edit(P1, "95816e83ced83c6f9cb9")
def barras_prenda(v):
    title(v, "Ventas por grupo de prenda")
    m = mref("FactVentas", ".Ventas")
    # misma idea que la guía: barras sobre el promedio en verde, el resto celeste
    reset(v, "objects", "dataPoint")
    avg = {"ScopedEval": {"Expression": {"Aggregation": {"Expression": {"ScopedEval": {
        "Expression": m, "Scope": [{"AllRolesRef": {}}]}}, "Function": 1}}, "Scope": []}}
    obj(v, "dataPoint", {"fill": {"solid": {"color": conditional([
        ({"Comparison": {"ComparisonKind": GE, "Left": m, "Right": avg}}, VERDE),
        ({"Comparison": {"ComparisonKind": LT, "Left": m, "Right": avg}}, CELESTE)])}}}, WILDCARD)
    obj(v, "labels", {"show": lit(True)})

@edit(P1, "c21bb36743db4bfc17a8")
def gauge(v):
    title(v, "Ventas vs Meta")
    alias(v, "Y", ["Ventas"]); alias(v, "TargetValue", ["Meta"])

@edit(P1, "9f85f5ac74e86452b598")
def pareto(v):
    title(v, measure=("DimArticulo", ".Titulo_Dinamico_GrupoIndice"))
    alias(v, "Y", ["Ventas"]); alias(v, "Y2", ["% Pareto"])
    reset(v, "objects", "dataPoint", "labels")
    p = mref("FactVentas", ".%Pareto_Ventas_Seccion")
    # columnas: verde hasta el 80 % acumulado (las secciones "vitales"), celeste el resto
    obj(v, "dataPoint", {"fill": {"solid": {"color": conditional([
        (cmp(LE, p, 0.8), VERDE), (cmp(GT, p, 0.8), CELESTE)])}}}, WILDCARD)
    obj(v, "dataPoint", {"fill": solid(AZUL_OSCURO)}, {"metadata": "FactVentas..%Pareto_Ventas_Seccion"})
    obj(v, "labels", {"show": lit(True), "fontSize": lit(7)})
    obj(v, "labels", {"show": lit(False)}, {"metadata": "FactVentas..Ventas"})
    obj(v, "lineStyles", {"showMarker": lit(True)})
    obj(v, "legend", {"show": lit(False)})

# ================================================================== Página 2: Comparación Anual
for vid, name, single in [("3ee16a5950bdffac7710", "Año", True), ("564f417a0880c79cf098", "Mes", False),
                          ("54a59a5a5be0a46ad7f3", "Grupo índice", False), ("24fc3a306786107ec463", "Canal", False)]:
    @edit(P2, vid)
    def slicer_p2(v, name=name, single=single): slicer(v, name, single=single)

@edit(P2, "ff5d67278bf2a6de4f40")
def gauge2(v):
    title(v, "Avance vs año previo")
    alias(v, "Y", ["Año actual"]); alias(v, "TargetValue", ["Año previo"])

@edit(P2, "1ea589e03ced0ce30fa8")
def montos_previos(v):
    title(v, "Montos totales previos")
    alias(v, "Values", ["Total previo -1", "Total previo -2"])
    obj(v, "dataLabels", {"fontSize": lit(16)})
    obj(v, "categoryLabels", {"show": lit(True), "fontSize": lit(10)})

for vid, tit, var in [("32d3408b3a393c2c2ee3", ".Titulo_Varianza", ".%var_Ventas"),
                      ("b2a7d85326111eba65a2", ".Titulo_Varianza1", ".%var_Ventas1")]:
    @edit(P2, vid)
    def indicador(v, tit=tit, var=var):
        title(v, measure=("FactVentas", tit), size=10)
        obj(v, "labels", {"fontSize": lit(25), "fontFamily": lit("DIN"),
                          "color": {"solid": {"color": conditional(signo(mref("FactVentas", var)))}}})
        obj(v, "categoryLabels", {"show": lit(False)})

@edit(P2, "aa4f9d6b2ea89e3972df")
def comparacion_grupo(v):
    title(v, "Comparación por grupo índice")
    alias(v, "Y", ["Actual", "Previo -1", "Previo -2"])
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})
    obj(v, "labels", {"show": lit(True), "fontSize": lit(7)})

@edit(P2, "82a96890f7171232eafd")
def comparacion_anual(v):
    title(v, measure=("FactVentas", ".Titulo_Comparacion_anual"))
    alias(v, "Y", ["Actual", "Previo -1", "Previo -2"])
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})
    obj(v, "lineStyles", {"showMarker": lit(True)})

@edit(P2, "3abfa3bca3fe6e2cf145")
def evolucion_global(v):
    title(v, "Evolución global")
    cats = v["query"]["queryState"]["Category"]["projections"]
    for p in cats: p["active"] = True                       # expandir todos los niveles (Año > Mes)
    v["query"]["sortDefinition"] = {"sort": [{"field": p["field"], "direction": "Ascending"} for p in cats],
                                    "isDefaultSort": True}
    obj(v, "categoryAxis", {"concatenateLabels": lit(False)})
    obj(v, "lineStyles", {"lineStyle": lit("dashed"), "showMarker": lit(True)})

@edit(P2, "4a1da73a87347e15c0f3")
def crecimiento(v):
    title(v, "Crecimiento interanual por mes (mismo periodo año anterior)")
    color_rule(v, None, signo(mref("FactVentas", ".%Crecimiento_Interanual")))
    obj(v, "labels", {"show": lit(True), "fontSize": lit(7)})

# ================================================================== Página 3: Ventas vs Metas y Clientes
for vid, name, single in [("480778072575d431ec42", "Escenario de meta", True), ("9673f7b2436ee4ac7985", "Temporada", False),
                          ("9ffa28624fd9249f42f2", "Sección", False), ("cd58fa28b3c2005c3c38", "Canal", False)]:
    @edit(P3, vid)
    def slicer_p3(v, name=name, single=single): slicer(v, name, single=single)

for vid, name in [("2ea122f6dba7c9bdee8e", "Ventas"), ("ba66aa2c39dbf758b4a3", "Meta"),
                  ("1a5917a12a5b79e73b57", "Brecha vs meta")]:
    @edit(P3, vid)
    def card_p3(v, name=name): card(v, name)

@edit(P3, "6bb6b1a5512a7e684ed6")
def cumplimiento(v):
    card(v, "% Cumplimiento de meta", size=22)
    # color por valor de campo: la medida devuelve el color (verde / ámbar / rojo)
    obj(v, "labels", {"color": {"solid": {"color": {"expr": mref("FactMetas", ".Color_Cumplimiento")}}}})

@edit(P3, "63d6485d1c7d194746fd")
def ventas_vs_meta(v):
    title(v, measure=("FactMetas", ".Titulo_Ventas_vs_Meta"))
    alias(v, "Y", ["Ventas"]); alias(v, "Y2", ["Meta"])
    reset(v, "objects", "dataPoint")
    obj(v, "dataPoint", {"fill": solid(AZUL)}, {"metadata": "FactVentas..Ventas"})
    obj(v, "dataPoint", {"fill": solid(NARANJA)}, {"metadata": "FactMetas..Meta"})
    obj(v, "lineStyles", {"showMarker": lit(True)})
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})

@edit(P3, "d5851debb5c20ed896d4")
def temporada(v):
    title(v, "Ventas vs meta por temporada")
    alias(v, "Y", ["Ventas", "Meta"])
    reset(v, "objects", "dataPoint")
    obj(v, "dataPoint", {"fill": solid(AZUL)}, {"metadata": "FactVentas..Ventas"})
    obj(v, "dataPoint", {"fill": solid(NARANJA)}, {"metadata": "FactMetas..Meta"})
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})

@edit(P3, "0519dc8734ec79897799")
def tabla(v):
    title(v, "Cumplimiento por sección")
    alias(v, "Values", ["Sección", "Ventas", "Meta", "% Cumplimiento", "Brecha"])
    reset(v, "objects", "columnFormatting", "values")
    obj(v, "values", {"backColorSecondary": solid("#CCE0F3")})                      # filas alternas, como la guía
    obj(v, "columnHeaders", {"alignment": lit("Center")})
    obj(v, "values", {"fontColor": {"solid": {"color": {"expr": mref("FactMetas", ".Color_Cumplimiento")}}}},
        {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "FactMetas..%Cumplimiento_Meta"})
    bars = {"positiveColor": solid(VERDE_IND), "negativeColor": solid(ROJO_IND), "axisColor": solid("#000000"),
            "reverseDirection": lit(False), "hideText": lit(False)}
    obj(v, "columnFormatting", {"dataBars": bars}, {"metadata": "FactMetas..Brecha_Meta"})
    obj(v, "columnFormatting", {"dataBars": {**bars, "positiveColor": solid(AZUL)}}, {"metadata": "FactVentas..Ventas"})

@edit(P3, "e945a758cf1ad978c8e8")
def canal(v):
    title(v, "Ventas por canal")
    obj(v, "labels", {"show": lit(True), "labelStyle": lit("Category, percent of total")})

@edit(P3, "a7618215aef11c5fa3f1")
def embudo(v):
    v["visualType"] = "funnel"
    title(v, "Ventas por rango de edad")
    obj(v, "labels", {"show": lit(True)})
    box(v, "visualTooltip", {"show": lit(True), "type": lit("Canvas"), "section": lit(TIP)})

# ================================================================== Tooltip
@edit(TIP, "9ae960fd759bfd7ad08f")
def tooltip_linea(v):
    title(v, "Promedio diario de ventas (últimos 7 días)", size=9)
    v["query"]["sortDefinition"] = {"sort": [{"field": v["query"]["queryState"]["Category"]["projections"][0]["field"],
                                              "direction": "Ascending"}], "isDefaultSort": True}

tp = os.path.join(PAGES, TIP, "page.json")
with open(tp, encoding="utf-8") as f: pg = json.load(f)
pg.pop("config", None)
pg["type"] = "Tooltip"
pg["visibility"] = "HiddenInViewMode"
pg["width"], pg["height"] = 320, 240
pg["pageBinding"] = {"name": "b7c1d2e3f4a5b6c7d8e9", "type": "Tooltip", "parameters": []}
with open(tp, "w", encoding="utf-8") as f: json.dump(pg, f, ensure_ascii=False, indent=2)
print("ok pagina tooltip")

# ================================================================== Global
for page in os.listdir(PAGES):
    vdir = os.path.join(PAGES, page, "visuals")
    if not os.path.isdir(vdir): continue
    for vid in os.listdir(vdir):
        p = os.path.join(vdir, vid, "visual.json")
        with open(p, encoding="utf-8") as f: d = json.load(f)
        if "visual" in d:
            box(d["visual"], "subTitle", {"show": lit(False)})     # quita el subtítulo automático ".X por Y"
        fc = d.get("filterConfig", {}).get("filters")
        if fc:
            d["filterConfig"]["filters"] = [x for x in fc if "Measure" not in x["field"]]
            if not d["filterConfig"]["filters"]: d.pop("filterConfig")
        with open(p, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
print("ok subtitulos y filtros")

ext_path = os.path.join(REPORT, "reportExtensions.json")
if os.path.exists(ext_path): os.remove(ext_path)
