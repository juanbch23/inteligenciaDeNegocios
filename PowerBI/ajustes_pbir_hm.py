"""Formato de los 3 dashboards del caso H&M (Estratégico, Táctico, Analítico) que el MCP no cubre.
Patrones PBIR verificados en Power BI Desktop (ver LABORATORIO-TABULARES). Idempotente.
Ejecutar con Power BI Desktop cerrado:  python ajustes_pbir_hm.py
(La versión anterior, estilo laboratorio, está en _respaldo_estilo_laboratorio\\)"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(ROOT, "HM_Dashboard.Report", "definition")
PAGES = os.path.join(REPORT, "pages")
D1, D2, D3, TIP = "b51b70af0c57afacc5cf", "26d4053f99dd718e5508", "29f3171285671fc539e1", "d04ce7b52687a84bc5df"

ROJO_HM, OSCURO, GRIS, GRIS_CLARO, FONDO = "#CC071E", "#111827", "#9CA3AF", "#E5E7EB", "#F3F4F6"
VERDE, ROJO = "#2E7D32", "#C62828"

# ------------------------------------------------------------------ helpers PBIR
def lit(v):
    if isinstance(v, bool): v = "true" if v else "false"
    elif isinstance(v, (int, float)): v = f"{v}D"
    else: v = f"'{v}'"
    return {"expr": {"Literal": {"Value": v}}}

def mref(entity, prop): return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
def cref(entity, prop): return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
def solid(c): return {"solid": {"color": c if isinstance(c, dict) else lit(c)}}
def campo(entity, prop): return {"solid": {"color": {"expr": mref(entity, prop)}}}   # color por valor de campo
WILDCARD = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}

def path(page, vid): return os.path.join(PAGES, page, "visuals", vid, "visual.json")

def edit(page, vid):
    def deco(fn):
        p = path(page, vid)
        with open(p, encoding="utf-8") as f: d = json.load(f)
        fn(d)
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

def title(v, text, size=11):
    box(v, "title", {"show": lit(True), "text": lit(text), "fontSize": lit(size), "bold": lit(True),
                     "fontColor": solid(OSCURO), "alignment": lit("left")})

def alias(v, bucket, names):
    for p, n in zip(v["query"]["queryState"][bucket]["projections"], names):
        if n: p["displayName"] = n; p["nativeQueryRef"] = n

def slicer(d, name, single=False, default=None):
    v = d["visual"]
    alias(v, "Values", [name])
    obj(v, "header", {"show": lit(True), "text": lit(name)})
    obj(v, "selection", {"strictSingleSelect": lit(single), "selectAllCheckboxEnabled": lit(not single)})
    if default is not None:   # selección inicial: Power BI la guarda en objects.general.filter del segmentador
        field = v["query"]["queryState"]["Values"]["projections"][0]["field"]
        ent, prop = field["Column"]["Expression"]["SourceRef"]["Entity"], field["Column"]["Property"]
        value = f"{default}L" if isinstance(default, int) else f"'{default}'"
        obj(v, "general", {"filter": {"filter": {"Version": 2, "From": [{"Name": "t", "Entity": ent, "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}},
                                                                        "Property": prop}}],
                                            "Values": [[{"Literal": {"Value": value}}]]}}}]}}})
        d.pop("filterConfig", None)

def vid_of(d): return d["name"]

def card(d, name, color=None, size=22):
    v = d["visual"]
    alias(v, "Values", [name])
    obj(v, "labels", {"fontSize": lit(size), "color": campo(*color) if color else solid(OSCURO)})
    obj(v, "categoryLabels", {"show": lit(True), "fontSize": lit(10), "color": solid("#4B5563")})

def narrativa(d):
    v = d["visual"]
    obj(v, "labels", {"fontSize": lit(11), "color": solid(OSCURO), "fontFamily": lit("Segoe UI")})
    obj(v, "categoryLabels", {"show": lit(False)})
    obj(v, "wordWrap", {"show": lit(True)})
    box(v, "background", {"show": lit(True), "color": solid("#FEF2F2")})
    box(v, "border", {"show": lit(True), "color": solid(ROJO_HM), "radius": lit(6)})

def color_categoria(v, entity, prop, mapping):
    for value, color in mapping.items():
        obj(v, "dataPoint", {"fill": solid(color)}, {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": cref(entity, prop), "Right": {"Literal": {"Value": f"'{value}'"}}}}}]})

def color_serie(v, metadata, color): obj(v, "dataPoint", {"fill": solid(color)}, {"metadata": metadata})

CANAL = {"Online": ROJO_HM, "Tienda fisica": GRIS}

# ================================================================== D1 Estratégico
@edit(D1, "ffeb1e14ff717aa1a074")
def d1_anio(d): slicer(d, "Año", single=True, default=2020)
@edit(D1, "0375280e426adf109635")
def d1_escenario(d): slicer(d, "Escenario de meta", single=True, default="Escenario 2")

for vid, name, color in [("125e46d6aa12385a4757", "Ventas", None),
                         ("5d493a0395771f8d6443", "Vs. año anterior", ("FactVentas", ".Color_Interanual")),
                         ("d0c9d48a082389b31173", "Cumplimiento meta", ("FactMetas", ".Color_Cumplimiento")),
                         ("c3bcbb8b4f5aa9b34784", "Participación online", None),
                         ("fe6afa8b4e0360ee1532", "Retención 2019→2020", ("DimCliente", ".Color_Retencion")),
                         ("d8cfbf40c10163f5a920", "Descuento implícito", ("FactVentas", ".Color_Descuento"))]:
    @edit(D1, vid)
    def d1_kpi(d, name=name, color=color): card(d, name, color, size=16)

@edit(D1, "59e894b71eddcbfb419d")
def d1_narrativa(d): narrativa(d)

@edit(D1, "09a2ea4b144510ac187f")
def d1_lineas(d):
    v = d["visual"]
    title(v, "Ventas mes a mes por año: el cierre de tiendas de marzo-abril 2020")
    reset(v, "objects", "dataPoint")
    color_categoria(v, "DimFecha", "Anio", {})
    for anio, c in (("2018", GRIS_CLARO), ("2019", GRIS), ("2020", ROJO_HM)):
        obj(v, "dataPoint", {"fill": solid(c)}, {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": cref("DimFecha", "Anio"), "Right": {"Literal": {"Value": f"{anio}L"}}}}}]})
    obj(v, "lineStyles", {"showMarker": lit(True), "strokeWidth": lit(3)})
    obj(v, "legend", {"show": lit(True), "position": lit("TopRight")})
    box(v, "visualTooltip", {"show": lit(True), "type": lit("Canvas"), "section": lit(TIP)})

@edit(D1, "61f2c7e4cadb502385b2")
def d1_cascada(d):
    v = d["visual"]
    title(v, "¿Dónde se perdió la venta? Diferencia vs. mismo periodo del año anterior")
    alias(v, "Y", ["Diferencia"])
    obj(v, "sentimentColors", {"increaseFill": solid(VERDE), "decreaseFill": solid(ROJO_HM), "totalFill": solid(OSCURO)})
    obj(v, "labels", {"show": lit(True), "fontSize": lit(8)})

@edit(D1, "946e977d852d02b601fb")
def d1_mezcla(d):
    v = d["visual"]
    title(v, "Mezcla de canal por mes (abril 2020: 100 % online)")
    reset(v, "objects", "dataPoint")
    color_categoria(v, "DimCanal", "NombreCanal", CANAL)
    obj(v, "legend", {"show": lit(True), "position": lit("TopRight")})

@edit(D1, "93a537e18c775cac244c")
def d1_nuevos(d):
    v = d["visual"]
    title(v, "Captación: clientes nuevos por mes")
    alias(v, "Y", ["Clientes nuevos"])
    reset(v, "objects", "dataPoint")
    obj(v, "dataPoint", {"fill": solid(OSCURO)})

# ================================================================== D2 Táctico
@edit(D2, "e25b97125f754d49474f")
def d2_escenario(d): slicer(d, "Escenario de meta", single=True, default="Escenario 2")
for vid, name in [("1dfc99ec5c66ff3bcac9", "Temporada"), ("1e994960b0ccd685ce23", "Sección"), ("af60ad090e568207d2c5", "Canal")]:
    @edit(D2, vid)
    def d2_slicer(d, name=name): slicer(d, name)

for vid, name, color in [("fe83fab521cc7edb67a5", "Ventas", None), ("caee8d1ca248a5a5c976", "Meta (diaria acumulada)", None),
                         ("4ec5de320e92374b129f", "Cumplimiento de meta", ("FactMetas", ".Color_Cumplimiento")),
                         ("00ec86d6ba0d491391a0", "Secciones que cumplen", None),
                         ("73009d2f5f154745e0a3", "Secciones bajo el 50 %", None)]:
    @edit(D2, vid)
    def d2_kpi(d, name=name, color=color): card(d, name, color, size=18)

@edit(D2, "73009d2f5f154745e0a3")
def d2_bajo50_rojo(d): obj(d["visual"], "labels", {"color": solid(ROJO)})

@edit(D2, "6646e5b076fb67fccb9b")
def d2_narrativa(d): narrativa(d)

@edit(D2, "514a1ee51fdb0fb9170b")
def d2_calor(d):
    v = d["visual"]
    title(v, "Mapa de calor: % de cumplimiento por sección y temporada")
    alias(v, "Values", ["% Cumplimiento"])
    reset(v, "objects", "values")
    obj(v, "values", {"backColor": campo("FactMetas", ".Color_Cumplimiento"), "fontColor": solid("#FFFFFF")},
        {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "FactMetas..%Cumplimiento_Meta"})
    obj(v, "columnHeaders", {"alignment": lit("Center")})
    obj(v, "subTotals", {"rowSubtotals": lit(True), "columnSubtotals": lit(True)})

@edit(D2, "c711e91b23588593fd34")
def d2_dispersion(d):
    v = d["visual"]
    title(v, "Meta vs. venta por sección (tamaño = clientes, color = cumplimiento)")
    reset(v, "objects", "dataPoint")
    obj(v, "dataPoint", {"fill": campo("FactMetas", ".Color_Cumplimiento")}, WILDCARD)
    obj(v, "categoryLabels", {"show": lit(False)})

@edit(D2, "a32d13b282929b3a3401")
def d2_top5(d):
    v = d["visual"]
    title(v, "Top 5 secciones por cumplimiento")
    alias(v, "Y", ["% Cumplimiento"])
    obj(v, "dataPoint", {"fill": solid(VERDE)})
    obj(v, "labels", {"show": lit(True)})

@edit(D2, "3779520644a7484c89f4")
def d2_bottom5(d):
    v = d["visual"]
    title(v, "Bottom 5: secciones con meta mal asignada")
    alias(v, "Y", ["% Cumplimiento"])
    obj(v, "dataPoint", {"fill": solid(ROJO)})
    obj(v, "labels", {"show": lit(True)})

@edit(D2, "d5a843844abe868cdb11")
def d2_acumulado(d):
    v = d["visual"]
    title(v, "Venta acumulada vs. meta acumulada (filtra una temporada para seguirla día a día)")
    alias(v, "Y", ["Venta acumulada", "Meta acumulada"])
    reset(v, "objects", "dataPoint")
    color_serie(v, "FactVentas..Ventas_Acumuladas", ROJO_HM)
    color_serie(v, "FactMetas..Meta_Acumulada", GRIS)
    obj(v, "lineStyles", {"strokeWidth": lit(3)})
    obj(v, "lineStyles", {"lineStyle": lit("dashed")}, {"metadata": "FactMetas..Meta_Acumulada"})
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})

# ================================================================== D3 Analítico
for vid, name in [("d00c0ca8d3288e0086c0", "Año"), ("5f4945d08b8a8049d136", "Canal"), ("bbdcd1ea28cc9017a16e", "Rango de edad"),
                  ("a688d56eba9decba7daf", "Grupo índice"), ("74fbc2b0d68a707152ce", "Tipo de cliente"),
                  ("2c426d4de7ad224a56e9", "Club")]:
    @edit(D3, vid)
    def d3_slicer(d, name=name): slicer(d, name)

for vid, name in [("1cc21cd7fd6f5bf8d4fb", "Ticket por cesta"), ("13c2fc97516b8fafc4b0", "Artículos por cesta"),
                  ("128dd8468820ec2a35c7", "Recompra"), ("7f5e55f29d8595d6dd35", "Clientes omnicanal"),
                  ("844e9fc362dccbbbe269", "Omnicanal vs. un canal"), ("26991162cca81c1d3e83", "Venta top 20 % clientes")]:
    @edit(D3, vid)
    def d3_kpi(d, name=name): card(d, name, size=18)

@edit(D3, "844e9fc362dccbbbe269")
def d3_multiplicador_rojo(d): obj(d["visual"], "labels", {"color": solid(ROJO_HM)})

@edit(D3, "69391376fd8bf6fcba37")
def d3_narrativa(d): narrativa(d)

@edit(D3, "7b9a7fd453a126756ea0")
def d3_arbol(d): title(d["visual"], "¿De dónde sale la venta? Árbol de descomposición (haz clic en + para abrir)")

@edit(D3, "340ecf9251b874786d1b")
def d3_tipo_canal(d):
    v = d["visual"]
    title(v, "Venta por cliente según tipo de cliente")
    alias(v, "Y", ["Venta por cliente"])
    reset(v, "objects", "dataPoint")
    color_categoria(v, "DimCliente", "TipoCanal", {"Omnicanal": ROJO_HM, "Solo online": GRIS, "Solo tienda": GRIS_CLARO})
    obj(v, "labels", {"show": lit(True)})

@edit(D3, "a5c2a4fae3203bd50c44")
def d3_club(d):
    v = d["visual"]
    title(v, "Venta por cliente por edad: club activo vs. no activo")
    alias(v, "Y", ["Venta por cliente"])
    reset(v, "objects", "dataPoint")
    color_categoria(v, "DimCliente", "ClubActivo", {"Club activo": ROJO_HM, "No activo": GRIS})
    obj(v, "legend", {"show": lit(True), "position": lit("TopRight")})

@edit(D3, "3c68fb516a815e730045")
def d3_descuento(d):
    v = d["visual"]
    title(v, "Descuento implícito por canal (meta ≤ 17 %)")
    alias(v, "Y", ["Descuento implícito"])
    reset(v, "objects", "dataPoint")
    color_categoria(v, "DimCanal", "NombreCanal", CANAL)
    obj(v, "lineStyles", {"showMarker": lit(True), "strokeWidth": lit(3)})
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})

@edit(D3, "311df68c2dd608c34b30")
def d3_bandas(d):
    v = d["visual"]
    title(v, "Líneas por banda de descuento")
    alias(v, "Y", ["Líneas"])
    reset(v, "objects", "dataPoint")
    color_categoria(v, "FactVentas", "BandaDescuento", {"1. Sin descuento": GRIS_CLARO, "2. Hasta 10 %": "#FCA5A5",
                                                        "3. 10 % a 30 %": "#F87171", "4. Más de 30 %": "#991B1B"})
    obj(v, "legend", {"show": lit(True), "position": lit("Bottom")})

@edit(D3, "c4d7f2c62496f9dfbf26")
def d3_cesta(d):
    v = d["visual"]
    title(v, "Ticket (columnas) y artículos por cesta (línea)")
    alias(v, "Y", ["Ticket por cesta"]); alias(v, "Y2", ["Artículos por cesta"])
    reset(v, "objects", "dataPoint")
    obj(v, "dataPoint", {"fill": solid(GRIS)})                     # columnas (serie principal)
    color_serie(v, "FactVentas..Ticket_Cesta", GRIS)
    color_serie(v, "FactVentas..Articulos_por_Cesta", ROJO_HM)
    obj(v, "legend", {"show": lit(True), "position": lit("TopLeft")})

@edit(D3, "7b556e1933f0df196ca3")
def d3_segmento(d):
    v = d["visual"]
    title(v, "Pareto de clientes: venta por segmento de valor")
    reset(v, "objects", "dataPoint")
    color_categoria(v, "DimCliente", "SegmentoValor", {"1. Top 20 %": ROJO_HM, "2. Siguiente 30 %": GRIS, "3. Resto 50 %": GRIS_CLARO})
    obj(v, "labels", {"show": lit(True), "labelStyle": lit("Percent of total")})
    obj(v, "legend", {"show": lit(True), "position": lit("Bottom")})

# ================================================================== Tooltip
@edit(TIP, "9ae960fd759bfd7ad08f")
def tooltip_linea(d):
    v = d["visual"]
    title(v, "Promedio diario de ventas (últimos 7 días)", size=9)
    obj(v, "dataPoint", {"fill": solid(ROJO_HM)})

# ================================================================== Global: estilo de tarjetas y fondo
for page in os.listdir(PAGES):
    pdir = os.path.join(PAGES, page)
    if not os.path.isdir(pdir): continue
    pj = os.path.join(pdir, "page.json")
    with open(pj, encoding="utf-8") as f: pg = json.load(f)
    if page != TIP:
        pg.setdefault("objects", {})["background"] = [{"properties": {"color": solid(FONDO), "transparency": lit(0)}}]
    with open(pj, "w", encoding="utf-8") as f: json.dump(pg, f, ensure_ascii=False, indent=2)
    vdir = os.path.join(pdir, "visuals")
    if not os.path.isdir(vdir): continue
    for vid in os.listdir(vdir):
        p = os.path.join(vdir, vid, "visual.json")
        with open(p, encoding="utf-8") as f: d = json.load(f)
        v = d.get("visual")
        if v and v.get("visualType") not in ("shape", "basicShape"):
            box(v, "subTitle", {"show": lit(False)})
            box(v, "background", {"show": lit(True)})
            if "color" not in next((e["properties"] for e in v["visualContainerObjects"]["background"] if "selector" not in e), {}):
                box(v, "background", {"color": solid("#FFFFFF")})
            box(v, "border", {"show": lit(True)})
            b = next(e["properties"] for e in v["visualContainerObjects"]["border"] if "selector" not in e)
            b.setdefault("color", solid(GRIS_CLARO)); b.setdefault("radius", lit(8))
        fc = d.get("filterConfig", {}).get("filters")
        if fc:
            d["filterConfig"]["filters"] = [x for x in fc if "Measure" not in x["field"]]
            if not d["filterConfig"]["filters"]: d.pop("filterConfig")
        with open(p, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
print("ok estilo global")

tp = os.path.join(PAGES, TIP, "page.json")
with open(tp, encoding="utf-8") as f: pg = json.load(f)
pg.update({"type": "Tooltip", "visibility": "HiddenInViewMode", "width": 320, "height": 240,
           "pageBinding": {"name": "b7c1d2e3f4a5b6c7d8e9", "type": "Tooltip", "parameters": []}})
with open(tp, "w", encoding="utf-8") as f: json.dump(pg, f, ensure_ascii=False, indent=2)

pj = os.path.join(PAGES, "pages.json")
with open(pj, encoding="utf-8") as f: pp = json.load(f)
pp["activePageName"] = D1
with open(pj, "w", encoding="utf-8") as f: json.dump(pp, f, ensure_ascii=False, indent=2)
print("ok tooltip y pagina activa")
