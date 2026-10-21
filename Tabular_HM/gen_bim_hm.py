"""Genera Model.bim (compatibilidad 1200, como pide 'Cubos Tabulares y Pbi.pdf') del cubo H&M.

Origen : LAPTOP-IO596P6A\\DEV -> DWH_HM (modelo estrella cargado por SSIS)
Uso    : python gen_bim_hm.py Model.bim
"""
import json, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "Model.bim"
SERVER = r"LAPTOP-IO596P6A\DEV"
DS = "DWH_HM"

MONEY = "#,0.00"
INT = "#,0"
PCT = "0.00 %;-0.00 %;0.00 %"

# ------------------------------------------------------------------ tablas
# (columna, tipo, opciones)  opciones: hidden, sort, fmt, key
def col(name, dtype, **o):
    c = {"name": name, "dataType": dtype, "sourceColumn": name}
    if o.get("hidden"): c["isHidden"] = True
    if o.get("sort"): c["sortByColumn"] = o["sort"]
    if o.get("fmt"): c["formatString"] = o["fmt"]
    if o.get("key"): c["isKey"] = True
    if o.get("desc"): c["description"] = o["desc"]
    return c

MESES = ("CASE [Mes_Anio] WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo' WHEN 4 THEN 'Abril' "
         "WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio' WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre' "
         "WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' ELSE 'Diciembre' END")
DIAS = ("CASE [Dia_Semana] WHEN 1 THEN 'Domingo' WHEN 2 THEN 'Lunes' WHEN 3 THEN 'Martes' WHEN 4 THEN 'Miércoles' "
        "WHEN 5 THEN 'Jueves' WHEN 6 THEN 'Viernes' ELSE 'Sábado' END")

TABLES = [
    ("DimFecha",
     f"""SELECT [FechaKey], CAST([Fecha] AS DATETIME) AS [Fecha], [Dia_Semana], {DIAS} AS [Nombre_Dia_Semana],
       [Dia_Mes], [Dia_Anio], {MESES} AS [Nombre_Mes], [Mes_Anio], [Semana_Anio], [Anio], [Bimestre],
       [Trimestre], [Cuatrimestre], [Semestre], [Fin_Semana], [AnioMes],
       LEFT({MESES}, 3) + '-' + CAST([Anio] AS VARCHAR(4)) AS [Periodo]
  FROM [GENERICO].[DimFecha] WHERE [FechaKey] > 0""",
     [col("FechaKey", "int64", hidden=True), col("Fecha", "dateTime", key=True, fmt="dd/MM/yyyy"),
      col("Dia_Semana", "int64", hidden=True), col("Nombre_Dia_Semana", "string", sort="Dia_Semana"),
      col("Dia_Mes", "int64"), col("Dia_Anio", "int64"), col("Nombre_Mes", "string", sort="Mes_Anio"),
      col("Mes_Anio", "int64"), col("Semana_Anio", "int64"), col("Anio", "int64", fmt="0"),
      col("Bimestre", "int64"), col("Trimestre", "int64"), col("Cuatrimestre", "int64"), col("Semestre", "int64"),
      col("Fin_Semana", "int64", desc="1 = sábado o domingo"), col("AnioMes", "int64", fmt="0", hidden=True),
      col("Periodo", "string", sort="AnioMes", desc="Mes-Año (Sep-2018); se ordena cronológicamente")]),
    ("DimTemporada",
     """SELECT [TemporadaKey], [TemporadaID], [Temporada], [Estacion], [Anio], CAST([FechaInicio] AS DATETIME) AS [FechaInicio],
       CAST([FechaFin] AS DATETIME) AS [FechaFin]
  FROM [Ventas].[DimTemporada] WHERE [TemporadaKey] > 0""",
     [col("TemporadaKey", "int64", hidden=True), col("TemporadaID", "int64", hidden=True),
      col("Temporada", "string", sort="TemporadaID"), col("Estacion", "string"), col("Anio", "int64", fmt="0"),
      col("FechaInicio", "dateTime", fmt="dd/MM/yyyy"), col("FechaFin", "dateTime", fmt="dd/MM/yyyy")]),
    ("DimCanal",
     "SELECT [CanalKey], [CanalID], [NombreCanal] FROM [Ventas].[DimCanal] WHERE [CanalKey] > 0",
     [col("CanalKey", "int64", hidden=True), col("CanalID", "int64", hidden=True), col("NombreCanal", "string")]),
    ("DimDepartamento",
     """SELECT [DepartamentoKey], [department_name] AS [Departamento], [section_name] AS [Seccion]
  FROM [Ventas].[DimDepartamento] WHERE [DepartamentoKey] > 0""",
     [col("DepartamentoKey", "int64", hidden=True), col("Departamento", "string"), col("Seccion", "string")]),
    ("DimArticulo",
     """SELECT [ArticuloKey], [ArticleID], [ProdName] AS [Producto], [ProductTypeName] AS [TipoProducto],
       [ProductGroupName] AS [GrupoProducto], [GraphicalAppearanceName] AS [Apariencia],
       [ColourGroupName] AS [Color], [PerceivedColourMasterName] AS [ColorMaestro],
       [IndexName] AS [Indice], [IndexGroupName] AS [GrupoIndice], [GarmentGroupName] AS [GrupoPrenda]
  FROM [Ventas].[DimArticulo] WHERE [ArticuloKey] > 0""",
     [col("ArticuloKey", "int64", hidden=True), col("ArticleID", "int64", fmt="0"), col("Producto", "string"),
      col("TipoProducto", "string"), col("GrupoProducto", "string"), col("Apariencia", "string"),
      col("Color", "string"), col("ColorMaestro", "string"), col("Indice", "string"),
      col("GrupoIndice", "string"), col("GrupoPrenda", "string")]),
    ("DimCliente",
     """SELECT [ClienteKey], [FN], [Active], [ClubMemberStatus] AS [EstadoClub],
       [FashionNewsFrequency] AS [FrecuenciaNoticias], [Edad], [RangoEdad]
  FROM [Ventas].[DimCliente] WHERE [ClienteKey] > 0""",
     [col("ClienteKey", "int64", hidden=True), col("FN", "boolean"), col("Active", "boolean"),
      col("EstadoClub", "string"), col("FrecuenciaNoticias", "string"), col("Edad", "int64"),
      col("RangoEdad", "string")]),
    ("FactVentas",
     """SELECT [FechaKey], [ClienteKey], [ArticuloKey], [DepartamentoKey], [CanalKey], [TemporadaKey], [Precio]
  FROM [Ventas].[FactVentas]""",
     [col("FechaKey", "int64", hidden=True), col("ClienteKey", "int64", hidden=True),
      col("ArticuloKey", "int64", hidden=True), col("DepartamentoKey", "int64", hidden=True),
      col("CanalKey", "int64", hidden=True), col("TemporadaKey", "int64", hidden=True),
      col("Precio", "decimal", fmt=MONEY, hidden=True)]),
    ("FactMetas",
     """SELECT [Escenario], [FechaKey], [DepartamentoKey], [TemporadaKey], [MetaDiaria]
  FROM [Ventas].[vw_FactMetasDiaria]""",
     [col("Escenario", "string"), col("FechaKey", "int64", hidden=True),
      col("DepartamentoKey", "int64", hidden=True), col("TemporadaKey", "int64", hidden=True),
      col("MetaDiaria", "decimal", fmt=MONEY, hidden=True,
          desc="Meta diaria de GoalsHyM.xlsx (Monto), expandida a cada dia de su mes y temporada")]),
]

# ------------------------------------------------------------------ medidas
M = []
def m(table, name, expr, fmt=None, folder=None, desc=None):
    d = {"name": name, "expression": expr.strip()}
    if fmt: d["formatString"] = fmt
    if folder: d["displayFolder"] = folder
    if desc: d["description"] = desc
    M.append((table, d))

L7 = "DATESINPERIOD ( DimFecha[Fecha], MAX ( DimFecha[Fecha] ), -7, DAY )"

# 1. Basicas
F = "1. Ventas"
m("FactVentas", ".Ventas", "SUM(FactVentas[Precio])", MONEY, F, "Suma del precio de cada artículo vendido")
m("FactVentas", ".Ticket_Promedio", "AVERAGE(FactVentas[Precio])", MONEY, F, "Precio promedio por artículo vendido")
m("FactVentas", ".Transacciones", "COUNTROWS(FactVentas)", INT, F, "Artículos vendidos (una fila por artículo)")
m("FactVentas", ".Clientes_Unicos", "DISTINCTCOUNT(FactVentas[ClienteKey])", INT, F)
m("FactVentas", ".Articulos_Distintos", "DISTINCTCOUNT(FactVentas[ArticuloKey])", INT, F)
m("FactVentas", ".Ventas_por_Cliente", "DIVIDE([.Ventas], [.Clientes_Unicos])", MONEY, F)
m("FactVentas", ".Articulos_por_Cliente", "DIVIDE([.Transacciones], [.Clientes_Unicos])", "#,0.00", F)
m("FactVentas", ".Ventas_Online", 'CALCULATE([.Ventas], DimCanal[NombreCanal] = "Online")', MONEY, F)
m("FactVentas", ".Ventas_Tienda", 'CALCULATE([.Ventas], DimCanal[NombreCanal] = "Tienda fisica")', MONEY, F)
m("FactVentas", ".%Ventas_Online", "DIVIDE([.Ventas_Online], [.Ventas])", PCT, F)
m("FactVentas", ".%Participacion", "DIVIDE([.Ventas], CALCULATE([.Ventas], ALLSELECTED()))", PCT, F,
  "Participación sobre el total visible")

# 2. Tiempo (patrones de la guía)
F = "2. Tiempo"
m("DimFecha", ".Anio_Actual", "MAX(DimFecha[Anio])", "0", F)
m("FactVentas", ".Acumulado_Anual", "TOTALYTD([.Ventas], DimFecha[Fecha])", MONEY, F)
m("FactVentas", ".Ventas_Ultimos_Dias_7", f"CALCULATE ( [.Ventas], {L7} )", MONEY, F)
m("FactVentas", ".Ventas_Ultimos_Dias_7_avg", f"AVERAGEX ( {L7}, [.Ventas] )", MONEY, F,
  "Promedio diario de ventas de los últimos 7 días (media móvil)")
m("FactVentas", ".Ventas_Mismo_Periodo_AA", "CALCULATE([.Ventas], SAMEPERIODLASTYEAR(DimFecha[Fecha]))", MONEY, F,
  "Ventas del mismo periodo del año anterior")
m("FactVentas", ".%Crecimiento_Interanual",
  "DIVIDE([.Ventas] - [.Ventas_Mismo_Periodo_AA], [.Ventas_Mismo_Periodo_AA])", PCT, F)
for i, suf in enumerate(["Actual", "prev-1", "prev-2"]):
    off = f" - {i}" if i else ""
    m("FactVentas", f".Ventas_Anio_{suf}",
      f"VAR anio = [.Anio_Actual]{off}\nRETURN\n    CALCULATE([.Ventas], ALL(DimFecha[Anio]), DimFecha[Anio] = anio)", MONEY, F)
for n, k in [("", 1), ("1", 2)]:
    m("FactVentas", f".%var_Ventas{n}",
      f"DIVIDE([.Ventas_Anio_Actual] - [.Ventas_Anio_prev-{k}], [.Ventas_Anio_prev-{k}])", PCT, F)
    m("FactVentas", f".%Var_Ventas{n}_I",
      f'VAR si = IF([.%var_Ventas{n}] < 0, "▼", "▲")\nRETURN\n    IF(ISBLANK([.%var_Ventas{n}]), BLANK(), '
      f'FORMAT([.%var_Ventas{n}], "0.00 %") & "  " & si)', None, F)
    m("FactVentas", f".Titulo_Varianza{n}", f'"Año " & [.Anio_Actual] & " vs " & ([.Anio_Actual] - {k})', None, F)
m("FactVentas", ".Titulo_Comparacion_anual",
  '"Comparación anual " & [.Anio_Actual] & " - " & ([.Anio_Actual] - 1) & " - " & ([.Anio_Actual] - 2)', None, F)

# 3. Pareto (patron de la guía, por departamento)
F = "3. Pareto"
m("FactVentas", ".%Pareto_Ventas_Departamento", """
VAR A = [.Ventas]
VAR B = CALCULATE([.Ventas], ALLSELECTED(DimDepartamento[Departamento]))
VAR TOTAL =
    DIVIDE(
        SUMX(
            FILTER(
                SUMMARIZE(ALLSELECTED(DimDepartamento[Departamento]), DimDepartamento[Departamento], "PORC", [.Ventas]),
                [PORC] >= A),
            [PORC]),
        B)
RETURN
    TOTAL""", PCT, F, "Porcentaje acumulado de ventas (departamentos ordenados de mayor a menor)")
m("FactVentas", ".%Pareto_Ventas_Seccion", """
VAR A = [.Ventas]
VAR B = CALCULATE([.Ventas], ALLSELECTED(DimDepartamento[Seccion]))
VAR TOTAL =
    DIVIDE(
        SUMX(
            FILTER(
                SUMMARIZE(ALLSELECTED(DimDepartamento[Seccion]), DimDepartamento[Seccion], "PORC", [.Ventas]),
                [PORC] >= A),
            [PORC]),
        B)
RETURN
    TOTAL""", PCT, F, "Porcentaje acumulado de ventas (secciones ordenadas de mayor a menor)")
m("DimArticulo", ".Titulo_Dinamico_GrupoIndice", """
VAR grupo = DISTINCT(DimArticulo[GrupoIndice])
VAR grupo_S = CONCATENATEX(grupo, DimArticulo[GrupoIndice], " - ")
VAR CANTIDAD = COUNTROWS(grupo)
VAR TITULO = IF(CANTIDAD > 4, "Pareto de ventas por sección (todos los grupos)", "Pareto de ventas por sección: " & grupo_S)
RETURN
    TITULO""", None, F)

# 4. Metas (GoalsHyM.xlsx)
F = "4. Metas"
m("FactMetas", ".Escenario_Activo", 'SELECTEDVALUE(FactMetas[Escenario], "Escenario 1")', None, F,
  "Escenario elegido en el segmentador; si no hay uno solo, se usa Escenario 1")
m("FactMetas", ".Meta", """
VAR esc = [.Escenario_Activo]
RETURN
    CALCULATE(SUM(FactMetas[MetaDiaria]), FactMetas[Escenario] = esc)""", MONEY, F)
m("FactMetas", ".%Cumplimiento_Meta", "DIVIDE([.Ventas], [.Meta])", PCT, F)
m("FactMetas", ".Brecha_Meta", "IF(ISBLANK([.Meta]), BLANK(), [.Ventas] - [.Meta])", MONEY, F)
m("FactMetas", ".Cumplimiento_I", """
VAR c = [.%Cumplimiento_Meta]
RETURN
    IF(ISBLANK(c), BLANK(), FORMAT(c, "0.0 %") & IF(c >= 1, "  ▲", "  ▼"))""", None, F)
m("FactMetas", ".Color_Cumplimiento", """
VAR c = [.%Cumplimiento_Meta]
RETURN
    SWITCH(TRUE(), ISBLANK(c), BLANK(), c >= 1, "#2E7D32", c >= 0.9, "#F9A825", "#C62828")""", None, F,
  "Verde >= 100 %, ámbar >= 90 %, rojo < 90 % (formato condicional por valor de campo)")
m("FactMetas", ".Titulo_Ventas_vs_Meta", '"Ventas vs meta diaria acumulada - " & [.Escenario_Activo]', None, F)

# 5. Clientes
F = "5. Clientes"
m("DimCliente", ".Clientes_Registrados", "COUNTROWS(DimCliente)", INT, F)
m("DimCliente", ".Edad_Promedio_Compradores",
  "CALCULATE(AVERAGE(DimCliente[Edad]), CROSSFILTER(FactVentas[ClienteKey], DimCliente[ClienteKey], BOTH))", "0.0", F,
  "Edad promedio de los clientes que compraron en el contexto")
m("DimCliente", ".%Clientes_Compradores", "DIVIDE([.Clientes_Unicos], [.Clientes_Registrados])", PCT, F)

# ------------------------------------------------------------------ ensamblado
tables = []
for name, query, cols in TABLES:
    t = {"name": name, "columns": cols,
         "partitions": [{"name": name, "dataView": "full", "source": {"query": query, "dataSource": DS}}]}
    if name == "DimFecha":
        t["dataCategory"] = "Time"
    ms = [d for tb, d in M if tb == name]
    if ms:
        t["measures"] = ms
    tables.append(t)

def rel(name, ft, fc, tt, tc):
    return {"name": name, "fromTable": ft, "fromColumn": fc, "toTable": tt, "toColumn": tc}

relationships = [
    rel("FV_Fecha", "FactVentas", "FechaKey", "DimFecha", "FechaKey"),
    rel("FV_Cliente", "FactVentas", "ClienteKey", "DimCliente", "ClienteKey"),
    rel("FV_Articulo", "FactVentas", "ArticuloKey", "DimArticulo", "ArticuloKey"),
    rel("FV_Departamento", "FactVentas", "DepartamentoKey", "DimDepartamento", "DepartamentoKey"),
    rel("FV_Canal", "FactVentas", "CanalKey", "DimCanal", "CanalKey"),
    rel("FV_Temporada", "FactVentas", "TemporadaKey", "DimTemporada", "TemporadaKey"),
    rel("FM_Fecha", "FactMetas", "FechaKey", "DimFecha", "FechaKey"),
    rel("FM_Departamento", "FactMetas", "DepartamentoKey", "DimDepartamento", "DepartamentoKey"),
    rel("FM_Temporada", "FactMetas", "TemporadaKey", "DimTemporada", "TemporadaKey"),
]

bim = {
    "name": "SemanticModel",
    "compatibilityLevel": 1200,
    "model": {
        "culture": "es-ES",
        "dataSources": [{
            "name": DS,
            "connectionString": f"Provider=MSOLEDBSQL.1;Data Source={SERVER};Initial Catalog={DS};"
                                "Integrated Security=SSPI;Persist Security Info=false",
            "impersonationMode": "impersonateServiceAccount",
            "annotations": [{"name": "ConnectionEditUISource", "value": "SqlServer"}],
        }],
        "tables": tables,
        "relationships": relationships,
        "annotations": [{"name": "ClientCompatibilityLevel", "value": "400"}],
    },
    "id": "SemanticModel",
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(bim, f, ensure_ascii=False, indent=2)
print("OK", OUT, "tablas:", len(tables), "medidas:", len(M), "relaciones:", len(relationships))
