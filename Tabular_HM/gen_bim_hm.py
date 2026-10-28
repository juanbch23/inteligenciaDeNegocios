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
       CAST([FechaFin] AS DATETIME) AS [FechaFin],
       CASE [Estacion] WHEN 'verano' THEN 1 WHEN 'otoño' THEN 2 WHEN 'invierno' THEN 3 WHEN 'primavera' THEN 4 ELSE 9 END
           AS [OrdenEstacion]   -- orden del año comercial (hemisferio sur): verano, otoño, invierno, primavera
  FROM [Ventas].[DimTemporada] WHERE [TemporadaKey] > 0""",
     [col("TemporadaKey", "int64", hidden=True), col("TemporadaID", "int64", hidden=True),
      col("Temporada", "string", sort="TemporadaID"), col("Estacion", "string", sort="OrdenEstacion"),
      col("OrdenEstacion", "int64", hidden=True), col("Anio", "int64", fmt="0"),
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
       [FashionNewsFrequency] AS [FrecuenciaNoticias], [Edad], [RangoEdad], [ClubActivo],
       [FechaPrimeraCompra], [MesesConCompra], [TipoCanal], [Compra2019], [Compra2020], [SegmentoValor]
  FROM [Ventas].[vw_ClienteComportamiento]""",
     [col("ClienteKey", "int64", hidden=True), col("FN", "boolean"), col("Active", "boolean"),
      col("EstadoClub", "string"), col("FrecuenciaNoticias", "string"), col("Edad", "int64"),
      col("RangoEdad", "string"), col("ClubActivo", "string"),
      col("FechaPrimeraCompra", "dateTime", fmt="dd/MM/yyyy"), col("MesesConCompra", "int64"),
      col("TipoCanal", "string", desc="Omnicanal / Solo online / Solo tienda (todo el historial)"),
      col("Compra2019", "int64", hidden=True), col("Compra2020", "int64", hidden=True),
      col("SegmentoValor", "string", desc="Top 20 % / Siguiente 30 % / Resto 50 % de compradores por venta total")]),
    ("FactVentas",
     """SELECT [FechaKey], [ClienteKey], [ArticuloKey], [DepartamentoKey], [CanalKey], [TemporadaKey], [Precio],
       [PrecioLista], [BandaDescuento]
  FROM [Ventas].[vw_FactVentasCubo]""",
     [col("FechaKey", "int64", hidden=True), col("ClienteKey", "int64", hidden=True),
      col("ArticuloKey", "int64", hidden=True), col("DepartamentoKey", "int64", hidden=True),
      col("CanalKey", "int64", hidden=True), col("TemporadaKey", "int64", hidden=True),
      col("Precio", "double", fmt=MONEY, hidden=True),
      col("PrecioLista", "double", fmt=MONEY, hidden=True, desc="Precio máximo observado del artículo"),
      col("BandaDescuento", "string", desc="Descuento de la línea frente al precio de lista")]),
    ("FactMetas",
     # la meta TAL COMO VIENE en GoalsHyM.xlsx: una fila por escenario, seccion, temporada y mes (sin repartirla
     # por dias, eso seria un supuesto). FechaKey = primer dia del mes en el calendario.
     """SELECT [Escenario], [FechaKey], [DepartamentoKey], [TemporadaKey], [Monto] AS [Meta]
  FROM [Ventas].[FactMetas]""",
     [col("Escenario", "string"), col("FechaKey", "int64", hidden=True),
      col("DepartamentoKey", "int64", hidden=True), col("TemporadaKey", "int64", hidden=True),
      col("Meta", "double", fmt=MONEY, hidden=True,
          desc="Monto de GoalsHyM.xlsx tal como viene: meta por escenario, seccion, temporada y mes")]),
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
# Comparacion escalable: año elegido (filtro Año) contra el año de la tabla AnioComparacion (filtro "Comparar con");
# si no se elige año de comparacion se usa el anterior. Nada fijo: los años salen de los datos.
m("DimFecha", ".Anio_Elegido", "IF(HASONEVALUE(DimFecha[Anio]), VALUES(DimFecha[Anio]))", "0", F,
  "Año elegido en el filtro (vacío si se ven todos los años)")
m("DimFecha", ".Anio_Comparacion", """
VAR a = [.Anio_Elegido]
VAR c = SELECTEDVALUE(AnioComparacion[Comparar con])
RETURN
    IF(ISBLANK(a), BLANK(), IF(ISBLANK(c), a - 1, c))""", "0", F,
  "Año contra el que se compara: el del filtro Comparar con, o el anterior al elegido")
m("DimFecha", ".Desfase_Meses", "IF(ISBLANK([.Anio_Elegido]), BLANK(), 12 * ([.Anio_Elegido] - [.Anio_Comparacion]))", "0", F)
m("FactVentas", ".Comparacion_Incompleta", """
VAR k = [.Desfase_Meses]
VAR fechas = SELECTCOLUMNS(VALUES(DimFecha[Fecha]), "F", EDATE(DimFecha[Fecha], -k))
VAR dias = DISTINCTCOUNT(FactVentas[FechaKey])
VAR dias_comp = CALCULATE(DISTINCTCOUNT(FactVentas[FechaKey]), ALL(DimFecha), TREATAS(fechas, DimFecha[Fecha]))
RETURN
    IF(NOT ISBLANK(k) && k <> 0, dias_comp < dias * 0.9)""", None, F,
  "Verdadero si el año de comparación tiene menos de 90 % de los días con venta (datos incompletos)")
m("DimFecha", ".Txt_Comparacion", """
IF(ISBLANK([.Anio_Comparacion]), BLANK(),
   "vs " & [.Anio_Comparacion] & IF([.Comparacion_Incompleta], " (año con datos incompletos)"))""", None, F)
m("FactVentas", ".Ventas_Mismo_Periodo_AA", """
VAR k = [.Desfase_Meses]
VAR fechas = SELECTCOLUMNS(VALUES(DimFecha[Fecha]), "F", EDATE(DimFecha[Fecha], -k))
RETURN
    IF(NOT ISBLANK(k) && k <> 0,                        -- solo cuando se elige un año para comparar
       CALCULATE([.Ventas], ALL(DimFecha), TREATAS(fechas, DimFecha[Fecha])))""", MONEY, F,
  "Ventas de exactamente los mismos días (y meses filtrados) del año de comparación")
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
m("FactMetas", ".Escenario_Activo", 'SELECTEDVALUE(FactMetas[Escenario], "Escenario 2")', None, F,
  "Escenario elegido en el segmentador; si no hay uno solo, se usa el Escenario 2 (meta oficial del caso)")
m("FactMetas", ".Meta", """
VAR esc = [.Escenario_Activo]
RETURN
    CALCULATE(SUM(FactMetas[Meta]), FactMetas[Escenario] = esc)""", MONEY, F)
m("FactMetas", ".%Cumplimiento_Meta", "DIVIDE([.Ventas], [.Meta])", PCT, F)
m("FactMetas", ".Brecha_Meta", "IF(ISBLANK([.Meta]), BLANK(), [.Ventas] - [.Meta])", MONEY, F)
m("FactMetas", ".Cumplimiento_I", """
VAR c = [.%Cumplimiento_Meta]
RETURN
    IF(ISBLANK(c), BLANK(), FORMAT(c, "0.0 %") & IF(c >= 1, "  ▲", "  ▼"))""", None, F)
m("FactMetas", ".Color_Cumplimiento", """
VAR c = [.%Cumplimiento_Meta]
RETURN
    SWITCH(TRUE(), ISBLANK(c), BLANK(), c >= 1, "#1E8449", c >= 0.9, "#B9770E", "#B03A2E")""", None, F,
  "Verde >= 100 %, ámbar >= 90 %, rojo < 90 % (formato condicional por valor de campo)")
m("FactMetas", ".Titulo_Ventas_vs_Meta", '"Ventas vs meta - " & [.Escenario_Activo]', None, F)

# 5. Clientes
F = "5. Clientes"
m("DimCliente", ".Clientes_Registrados", "COUNTROWS(DimCliente)", INT, F)
m("DimCliente", ".Edad_Promedio_Compradores",
  "CALCULATE(AVERAGE(DimCliente[Edad]), CROSSFILTER(FactVentas[ClienteKey], DimCliente[ClienteKey], BOTH))", "0.0", F,
  "Edad promedio de los clientes que compraron en el contexto")
m("DimCliente", ".%Clientes_Compradores", "DIVIDE([.Clientes_Unicos], [.Clientes_Registrados])", PCT, F)

# 6. Indicadores del caso (docs\Indicadores_y_Dashboards.md)
VERDE, AMBAR, ROJO = '"#1E8449"', '"#B9770E"', '"#B03A2E"'   # paleta de los prototipos
def semaforo(measure, meta, mayor_es_mejor=True, tolerancia=0.05):
    if mayor_es_mejor:
        return (f"VAR x = [{measure}]\nRETURN\n    SWITCH(TRUE(), ISBLANK(x), BLANK(), x >= {meta}, {VERDE}, "
                f"x >= {meta} - {tolerancia}, {AMBAR}, {ROJO})")
    return (f"VAR x = [{measure}]\nRETURN\n    SWITCH(TRUE(), ISBLANK(x), BLANK(), x <= {meta}, {VERDE}, "
            f"x <= {meta} + {tolerancia}, {AMBAR}, {ROJO})")

F = "6. Indicadores del caso\\Cesta"
m("FactVentas", ".Cestas", "COUNTROWS(SUMMARIZE(FactVentas, FactVentas[ClienteKey], FactVentas[FechaKey], FactVentas[CanalKey]))",
  INT, F, "Cesta = mismo cliente + mismo día + mismo canal (no hay número de pedido)")
m("FactVentas", ".Ticket_Cesta", "DIVIDE([.Ventas], [.Cestas])", MONEY, F, "Ventas / cestas")
m("FactVentas", ".Articulos_por_Cesta", "DIVIDE([.Transacciones], [.Cestas])", "#,0.00", F, "Artículos (líneas) / cestas")

F = "6. Indicadores del caso\\Precio"
m("FactVentas", ".Precio_Lista", "SUM(FactVentas[PrecioLista])", MONEY, F)
m("FactVentas", ".%Descuento_Implicito", "IF([.Precio_Lista] > 0, 1 - DIVIDE([.Ventas], [.Precio_Lista]))", PCT, F,
  "1 - precio cobrado / precio máximo observado del artículo")
m("FactVentas", ".%Lineas_Descuento_30", 'DIVIDE(CALCULATE([.Transacciones], FactVentas[BandaDescuento] = "4. Más de 30 %"), [.Transacciones])',
  PCT, F, "Líneas vendidas con más de 30 % de descuento")
m("FactVentas", ".Color_Descuento", semaforo(".%Descuento_Implicito", 0.17, False, 0.02), None, F, "Meta propuesta <= 17 %")

F = "6. Indicadores del caso\\Crecimiento"
m("FactVentas", ".Delta_Interanual", "IF(ISBLANK([.Ventas_Mismo_Periodo_AA]), BLANK(), [.Ventas] - [.Ventas_Mismo_Periodo_AA])",
  MONEY, F, "Diferencia contra el mismo periodo del año anterior")
m("FactVentas", ".%Interanual_Tienda", 'CALCULATE([.%Crecimiento_Interanual], DimCanal[NombreCanal] = "Tienda fisica")', PCT, F)
m("FactVentas", ".%Interanual_Online", 'CALCULATE([.%Crecimiento_Interanual], DimCanal[NombreCanal] = "Online")', PCT, F)
m("FactVentas", ".Interanual_I", """
VAR x = [.%Crecimiento_Interanual]
RETURN
    IF(ISBLANK(x), BLANK(), FORMAT(x, "+0.0 %;-0.0 %") & IF(x >= 0, "  ▲", "  ▼"))""", None, F)
m("FactVentas", ".Color_Interanual", semaforo(".%Crecimiento_Interanual", 0, True, 0.05), None, F, "Meta propuesta >= 0 %")
m("FactVentas", ".Ventas_Acumuladas", """
CALCULATE([.Ventas], FILTER(ALLSELECTED(DimFecha[Fecha]), DimFecha[Fecha] <= MAX(DimFecha[Fecha])))""", MONEY, F)

F = "6. Indicadores del caso\\Clientes"
m("DimCliente", ".Clientes_Nuevos", """
VAR d1 = MIN(DimFecha[Fecha])
VAR d2 = MAX(DimFecha[Fecha])
RETURN
    CALCULATE(COUNTROWS(DimCliente), DimCliente[FechaPrimeraCompra] >= d1, DimCliente[FechaPrimeraCompra] <= d2)""",
  INT, F, "Clientes cuya primera compra cae en el periodo filtrado")
m("DimCliente", ".%Recompra", """
DIVIDE(CALCULATE(COUNTROWS(DimCliente), DimCliente[MesesConCompra] > 1),
       CALCULATE(COUNTROWS(DimCliente), DimCliente[MesesConCompra] >= 1))""", PCT, F, "Compradores con compra en más de un mes")
m("DimCliente", ".%Retencion_2019_2020", """
DIVIDE(CALCULATE(COUNTROWS(DimCliente), DimCliente[Compra2019] = 1, DimCliente[Compra2020] = 1),
       CALCULATE(COUNTROWS(DimCliente), DimCliente[Compra2019] = 1))""", PCT, F, "Compradores de 2019 que vuelven en 2020")
m("DimCliente", ".Color_Retencion", semaforo(".%Retencion_2019_2020", 0.65, True, 0.05), None, F, "Meta propuesta >= 65 %")
m("FactVentas", ".%Clientes_Omnicanal", 'DIVIDE(CALCULATE([.Clientes_Unicos], DimCliente[TipoCanal] = "Omnicanal"), [.Clientes_Unicos])', PCT, F)
m("FactVentas", ".%Penetracion_Club", 'DIVIDE(CALCULATE([.Clientes_Unicos], DimCliente[ClubActivo] = "Club activo"), [.Clientes_Unicos])', PCT, F)
m("FactVentas", ".%Ventas_Top20_Clientes", 'DIVIDE(CALCULATE([.Ventas], DimCliente[SegmentoValor] = "1. Top 20 %"), [.Ventas])', PCT, F)
m("FactVentas", ".Ventas_por_Cliente_Omnicanal", 'CALCULATE([.Ventas_por_Cliente], DimCliente[TipoCanal] = "Omnicanal")', MONEY, F)
m("FactVentas", ".Ventas_por_Cliente_UnCanal", 'CALCULATE([.Ventas_por_Cliente], DimCliente[TipoCanal] IN {"Solo online", "Solo tienda"})', MONEY, F)
m("FactVentas", ".Multiplicador_Omnicanal", "DIVIDE([.Ventas_por_Cliente_Omnicanal], [.Ventas_por_Cliente_UnCanal])", '0.0"x"', F,
  "Cuántas veces más compra el cliente omnicanal")
m("FactVentas", ".%Plus_Club", """
DIVIDE(CALCULATE([.Ventas_por_Cliente], DimCliente[ClubActivo] = "Club activo"),
       CALCULATE([.Ventas_por_Cliente], DimCliente[ClubActivo] = "No activo")) - 1""", PCT, F,
  "Cuánto más compra el cliente con club activo")

F = "6. Indicadores del caso\\Metas"
m("FactMetas", ".Meta_Acumulada", """
CALCULATE([.Meta], FILTER(ALLSELECTED(DimFecha[Fecha]), DimFecha[Fecha] <= MAX(DimFecha[Fecha])))""", MONEY, F)
m("FactMetas", ".Secciones_con_Meta", "COUNTROWS(FILTER(VALUES(DimDepartamento[Seccion]), NOT ISBLANK([.Meta])))", INT, F)
m("FactMetas", ".Secciones_Cumplen", "COUNTROWS(FILTER(VALUES(DimDepartamento[Seccion]), [.%Cumplimiento_Meta] >= 1))", INT, F)
m("FactMetas", ".Secciones_Bajo_50", "COUNTROWS(FILTER(VALUES(DimDepartamento[Seccion]), NOT ISBLANK([.Meta]) && [.%Cumplimiento_Meta] < 0.5))", INT, F)
for nombre, orden in (("Top5", "DESC"), ("Bottom5", "ASC")):
    m("FactMetas", f".Cumplimiento_{nombre}", f"""
VAR r = RANKX(FILTER(ALLSELECTED(DimDepartamento[Seccion]), NOT ISBLANK([.Meta])), [.%Cumplimiento_Meta], , {orden})
RETURN
    IF(HASONEVALUE(DimDepartamento[Seccion]) && NOT ISBLANK([.Meta]) && r <= 5, [.%Cumplimiento_Meta])""", PCT, F)

F = "6. Indicadores del caso\\Narrativa"
m("FactVentas", ".Narrativa_Estrategica", """
VAR y = [.%Crecimiento_Interanual]
RETURN
    IF(ISBLANK(y),
       "Todo el periodo: " & FORMAT([.Ventas] / 1E9, "#,0") & " MM vendidos y " & FORMAT([.%Cumplimiento_Meta], "0.0 %")
           & " de la meta. Elige un año (y con cuál compararlo) para ver si crecemos.",
       "En " & [.Anio_Elegido] & " llegamos al " & FORMAT([.%Cumplimiento_Meta], "0.0 %") & " de la meta y vendemos "
           & FORMAT(y, "+0.0 %;-0.0 %") & " " & [.Txt_Comparacion] & " (tienda "
           & FORMAT([.%Interanual_Tienda], "+0.0 %;-0.0 %") & ", online " & FORMAT([.%Interanual_Online], "+0.0 %;-0.0 %") & ").")
""", None, F, "Cambia con los filtros de año y Comparar con")
m("FactMetas", ".Narrativa_Metas", """
"Llegamos al " & FORMAT([.%Cumplimiento_Meta], "0 %") & " de la meta, pero solo " & [.Secciones_Cumplen] & " de "
    & [.Secciones_con_Meta] & " secciones cumplen y " & [.Secciones_Bajo_50] & " no llegan al 50 %: metas mal repartidas."
""", None, F)
m("FactVentas", ".Narrativa_Cliente", """
"El cliente omnicanal compra " & FORMAT([.Multiplicador_Omnicanal], "0.0") & " veces más y el de club activo "
    & FORMAT([.%Plus_Club], "+0 %") & "; el top 20 % genera el " & FORMAT([.%Ventas_Top20_Clientes], "0 %")
    & " de la venta. Descuento implícito: " & FORMAT([.%Descuento_Implicito], "0.0 %") & "."
""", None, F)

# 7. Dashboards (prototipos docs\HM_Modelos_Dashboards.pptx): anillos de avance, comparacion y textos.
#    Escalable: ningun año fijo; se compara el año elegido contra el de "Comparar con" (o el anterior).
F = "7. Dashboards"
V2, A2, R2, AZ = '"#1E8449"', '"#B9770E"', '"#B03A2E"', '"#2E6DA4"'   # paleta de los prototipos

def aa(expr):
    """Mismos dias del año de comparacion (igual que .Ventas_Mismo_Periodo_AA)."""
    return f"""
VAR k = [.Desfase_Meses]
VAR fechas = SELECTCOLUMNS(VALUES(DimFecha[Fecha]), "F", EDATE(DimFecha[Fecha], -k))
RETURN
    IF(NOT ISBLANK(k) && k <> 0, CALCULATE({expr}, ALL(DimFecha), TREATAS(fechas, DimFecha[Fecha])))"""

ELIGE = '"Elige un año para compararlo"'

def vs_txt(medida, fmt="0.0 %"):
    """'vs 2019: 72,8 %' o la invitacion a elegir un año."""
    return f'IF(ISBLANK([{medida}]), {ELIGE}, [.Txt_Comparacion] & ": " & FORMAT([{medida}], "{fmt}"))'


def anillo(table, nombre, ratio, color_fijo=None):
    """Anillo de avance frente a la meta: avance (0-1), resto y color del semaforo (verde >= 1, ambar >= 0,9)."""
    m(table, f".Anillo_{nombre}", f"VAR r = {ratio}\nRETURN IF(ISBLANK(r), BLANK(), MAX(0, MIN(r, 1)))", PCT, F)
    m(table, f".Anillo_{nombre}_Resto", f"IF(ISBLANK([.Anillo_{nombre}]), BLANK(), 1 - [.Anillo_{nombre}])", PCT, F)
    m(table, f".Color_Anillo_{nombre}", color_fijo or
      f"VAR r = {ratio}\nRETURN SWITCH(TRUE(), ISBLANK(r), BLANK(), r >= 1, {V2}, r >= 0.9, {A2}, {R2})", None, F)

def pct_txt(measure, prefijo):
    return f'IF(ISBLANK([{measure}]), BLANK(), "{prefijo}" & FORMAT([{measure}], "0.0 %"))'

# Ventas en miles de millones (MM) y año anterior
m("FactVentas", ".Ventas_MM", "DIVIDE([.Ventas], 1E9)", "#,0", F, "Ventas en miles de millones")
m("FactVentas", ".Ventas_AA_MM", "DIVIDE([.Ventas_Mismo_Periodo_AA], 1E9)", "#,0", F, "Año de comparación, mismos días, en MM")
m("FactVentas", ".Ventas_Online_AA", aa("[.Ventas_Online]"), MONEY, F)
m("FactVentas", ".%Ventas_Online_AA", "DIVIDE([.Ventas_Online_AA], [.Ventas_Mismo_Periodo_AA])", PCT, F)
m("FactVentas", ".Det_Online", vs_txt(".%Ventas_Online_AA"), None, F)
m("FactVentas", ".Det_Ventas", f'IF(ISBLANK([.Interanual_I]), {ELIGE}, [.Interanual_I] & " " & [.Txt_Comparacion])', None, F)
m("FactVentas", ".Interanual_Tienda_I", 'IF(ISBLANK([.%Interanual_Tienda]), "—", FORMAT([.%Interanual_Tienda], "+0.0 %;-0.0 %"))', None, F)
m("FactVentas", ".Interanual_Total_I", 'IF(ISBLANK([.%Crecimiento_Interanual]), "—", FORMAT([.%Crecimiento_Interanual], "+0.0 %;-0.0 %"))', None, F,
  "Crecimiento contra el año de comparacion; sin año elegido muestra un guion")
m("FactVentas", ".Ventas_AA_MM_Txt", 'IF(ISBLANK([.Ventas_AA_MM]), "Elige un año", FORMAT([.Ventas_AA_MM], "#,0"))', None, F,
  "Venta del mismo periodo del año de comparacion (MM); sin año elegido pide elegirlo")
m("FactVentas", ".Retencion_I", 'IF(ISBLANK([.%Retencion]), "Elige un año", FORMAT([.%Retencion], "0.0 %"))', None, F,
  "Retencion del año elegido; sin año elegido pide elegirlo")
m("FactVentas", ".Interanual_Online_I", 'IF(ISBLANK([.%Interanual_Online]), "—", FORMAT([.%Interanual_Online], "+0.0 %;-0.0 %"))', None, F)
m("DimFecha", ".Txt_Comparacion_Tarjeta", 'IF(ISBLANK([.Txt_Comparacion]), "Elige un año para ver la variación", [.Txt_Comparacion])', None, F)
m("FactVentas", ".Ventas_por_Cliente_M", "DIVIDE([.Ventas_por_Cliente], 1E6)", "#,0", F, "Venta por cliente en millones")
m("FactVentas", ".Color_Interanual_Tienda", semaforo(".%Interanual_Tienda", 0, True, 0.10), None, F)
m("FactVentas", ".Color_Interanual_Online", semaforo(".%Interanual_Online", 0, True, 0.10), None, F)
anillo("FactVentas", "Online", "[.%Ventas_Online]", AZ)

# Cumplimiento de meta
m("FactMetas", ".Meta_AA", aa("[.Meta]"), MONEY, F)
m("FactMetas", ".%Cumplimiento_AA", "DIVIDE([.Ventas_Mismo_Periodo_AA], [.Meta_AA])", PCT, F)
m("FactMetas", ".Det_Cumplimiento", 'IF(ISBLANK([.%Cumplimiento_AA]), "Meta ≥ 100 %", "Meta ≥ 100 % · " & [.Txt_Comparacion] & ": " & FORMAT([.%Cumplimiento_AA], "0.0 %"))', None, F)
anillo("FactMetas", "Cumplimiento", "[.%Cumplimiento_Meta]")
m("FactMetas", ".Cumpl_Peor_Temporada", 'MINX(FILTER(VALUES(DimTemporada[Temporada]), NOT ISBLANK([.Meta])), [.%Cumplimiento_Meta])', PCT, F)
m("FactMetas", ".Peor_Temporada", """
VAR t = TOPN(1, FILTER(VALUES(DimTemporada[Temporada]), NOT ISBLANK([.Meta])), [.%Cumplimiento_Meta], ASC)
RETURN CONCATENATEX(t, DimTemporada[Temporada], ", ")""", None, F, "Temporada con menor cumplimiento en el filtro")
anillo("FactMetas", "Peor_Temporada", "[.Cumpl_Peor_Temporada]")
m("FactMetas", ".Secciones_Cumplen_Txt", '(0 + [.Secciones_Cumplen]) & " de " & (0 + [.Secciones_con_Meta])', None, F)
m("FactMetas", ".Secciones_Bajo_50_Txt", '(0 + [.Secciones_Bajo_50]) & " de " & (0 + [.Secciones_con_Meta])', None, F)
m("FactMetas", ".Det_Secciones", 'FORMAT(DIVIDE([.Secciones_Cumplen], [.Secciones_con_Meta]), "0 %") & " de las secciones con meta"', None, F)
m("FactMetas", ".Det_Bajo_50", '"No llegan a la mitad de su meta"', None, F)
anillo("FactMetas", "Secciones", "DIVIDE([.Secciones_Cumplen], [.Secciones_con_Meta])")
anillo("FactMetas", "Bajo_50", "DIVIDE([.Secciones_Bajo_50], [.Secciones_con_Meta])", R2)
m("FactMetas", ".Gauge_Max", "1.5", PCT, F, "Escala del velocímetro (0 a 150 %)")
m("FactMetas", ".Gauge_Meta", "1", PCT, F, "Meta del velocímetro (100 %)")
m("FactMetas", ".Gauge_Uno", "1", PCT, F, "Escala de los anillos de los KPI (0 a 100 %)")

# Retencion y descuento de tienda
# Retencion entre dos años cualesquiera: los del filtro, o el ultimo año con datos contra el anterior
m("FactVentas", ".Retencion_Anio", "IF(ISBLANK([.Anio_Elegido]), CALCULATE(MAX(DimFecha[Anio]), ALL(DimFecha)), [.Anio_Elegido])", "0", F)
m("FactVentas", ".Retencion_Base", "IF(ISBLANK([.Anio_Elegido]), [.Retencion_Anio] - 1, [.Anio_Comparacion])", "0", F)
m("FactVentas", ".%Retencion", """
VAR a = [.Retencion_Anio]
VAR c = [.Retencion_Base]
VAR antes = CALCULATETABLE(VALUES(FactVentas[ClienteKey]), ALL(DimFecha), DimFecha[Anio] = c)
VAR despues = CALCULATETABLE(VALUES(FactVentas[ClienteKey]), ALL(DimFecha), DimFecha[Anio] = a)
RETURN
    IF(c < a, DIVIDE(COUNTROWS(INTERSECT(antes, despues)), COUNTROWS(antes)))""", PCT, F,
  "Clientes que compraron en el año base y vuelven a comprar en el año elegido")
anillo("FactVentas", "Retencion", "DIVIDE([.%Retencion], 0.65)")
m("FactVentas", ".Det_Retencion", '"Meta ≥ 65 % · clientes de " & [.Retencion_Base] & " que vuelven en " & [.Retencion_Anio]', None, F)
m("FactVentas", ".%Descuento_Tienda", 'CALCULATE([.%Descuento_Implicito], DimCanal[NombreCanal] = "Tienda fisica")', PCT, F)
m("FactVentas", ".%Descuento_Tienda_AA", aa("[.%Descuento_Tienda]"), PCT, F)
m("FactVentas", ".Det_Descuento", 'IF(ISBLANK([.%Descuento_Tienda_AA]), "Meta ≤ 17 %", "Meta ≤ 17 % · " & [.Txt_Comparacion] & ": " & FORMAT([.%Descuento_Tienda_AA], "0.0 %"))', None, F)
anillo("FactVentas", "Descuento", "DIVIDE(0.17, [.%Descuento_Tienda])")

# Cliente y precio (dashboard 3)
m("FactVentas", ".Ticket_Cesta_Online", 'CALCULATE([.Ticket_Cesta], DimCanal[NombreCanal] = "Online")', MONEY, F)
m("FactVentas", ".Ticket_Cesta_Online_M", "DIVIDE([.Ticket_Cesta_Online], 1E6)", "#,0.0", F, "Ticket por cesta online en millones")
m("FactVentas", ".Ticket_Cesta_Online_AA", aa("[.Ticket_Cesta_Online]"), MONEY, F)
m("FactVentas", ".Det_Ticket", f'IF(ISBLANK([.Ticket_Cesta_Online_AA]), {ELIGE}, FORMAT(DIVIDE([.Ticket_Cesta_Online], [.Ticket_Cesta_Online_AA]) - 1, "+0.0 %;-0.0 %") & " " & [.Txt_Comparacion] & " (" & FORMAT([.Ticket_Cesta_Online_AA] / 1E6, "#,0.0") & " M)")', None, F)
anillo("FactVentas", "Ticket", "DIVIDE([.Ticket_Cesta_Online], [.Ticket_Cesta_Online_AA])")
m("FactVentas", ".Articulos_Cesta_Online", 'CALCULATE([.Articulos_por_Cesta], DimCanal[NombreCanal] = "Online")', "#,0.00", F)
m("FactVentas", ".Det_Articulos", '"Meta propuesta ≥ 3,7"', None, F)
anillo("FactVentas", "Articulos", "DIVIDE([.Articulos_Cesta_Online], 3.7)")
m("DimCliente", ".Clientes_Nuevos_AA", """
VAR k = [.Desfase_Meses]
VAR d1 = EDATE(MIN(DimFecha[Fecha]), -k)
VAR d2 = EDATE(MAX(DimFecha[Fecha]), -k)
RETURN
    IF(NOT ISBLANK(k) && k <> 0,
       CALCULATE(COUNTROWS(DimCliente), DimCliente[FechaPrimeraCompra] >= d1, DimCliente[FechaPrimeraCompra] <= d2))""",
  INT, F, "Clientes nuevos de los mismos días del año de comparación")
m("DimCliente", ".Det_Nuevos", f'IF(ISBLANK([.Clientes_Nuevos_AA]) || [.Clientes_Nuevos_AA] = 0, {ELIGE}, FORMAT(DIVIDE([.Clientes_Nuevos], [.Clientes_Nuevos_AA]) - 1, "+0.0 %;-0.0 %") & " " & [.Txt_Comparacion] & " (" & FORMAT([.Clientes_Nuevos_AA], "#,0") & ")")', None, F)
anillo("DimCliente", "Nuevos", "DIVIDE([.Clientes_Nuevos], [.Clientes_Nuevos_AA])")
anillo("FactVentas", "Omnicanal", "DIVIDE([.%Clientes_Omnicanal], 0.40)")
m("FactVentas", ".Det_Omnicanal", '"Meta ≥ 40 % · valen " & FORMAT([.Multiplicador_Omnicanal], "0.0") & " veces más"', None, F)
anillo("FactVentas", "Club", "DIVIDE([.%Penetracion_Club], 0.40)")
m("FactVentas", ".Det_Club", '"Meta ≥ 40 % · compran " & FORMAT([.%Plus_Club], "+0 %") & " más"', None, F)
for nombre, filtro in (("Omnicanal", 'DimCliente[TipoCanal] = "Omnicanal"'),
                       ("UnCanal", 'DimCliente[TipoCanal] IN {"Solo online", "Solo tienda"}'),
                       ("Club", 'DimCliente[ClubActivo] = "Club activo"'),
                       ("NoClub", 'DimCliente[ClubActivo] = "No activo"')):
    m("FactVentas", f".VPC_{nombre}_M", f"DIVIDE(CALCULATE([.Ventas_por_Cliente], {filtro}), 1E6)", "#,0", F,
      "Venta por cliente en millones")
m("FactVentas", ".Multiplicador_Omnicanal_I", '"× " & FORMAT([.Multiplicador_Omnicanal], "0.0")', None, F)

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

tables.append({
    "name": "AnioComparacion",
    "description": "Años disponibles para el filtro Comparar con (sale de DimFecha: crece solo con los datos)",
    "columns": [{"type": "calculatedTableColumn", "name": "Comparar con", "dataType": "int64", "isNameInferred": True,
                 "isDataTypeInferred": True, "sourceColumn": "[Comparar con]", "formatString": "0",
                 "summarizeBy": "none"}],
    "partitions": [{"name": "AnioComparacion", "source": {
        "type": "calculated", "expression": 'DISTINCT(SELECTCOLUMNS(DimFecha, "Comparar con", DimFecha[Anio]))'}}]})

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
        # el job de SQL Server Agent (paso 3) procesa el cubo con la cuenta del servicio del Agente
        "roles": [{"name": "ProcesoETL", "modelPermission": "refresh",
                   "description": "Permite al job Job_HM (SQL Server Agent) procesar el cubo",
                   "members": [{"memberName": "NT Service\\SQLAgent$DEV"}]}],
        "annotations": [{"name": "ClientCompatibilityLevel", "value": "400"}],
    },
    "id": "SemanticModel",
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(bim, f, ensure_ascii=False, indent=2)
print("OK", OUT, "tablas:", len(tables), "medidas:", len(M), "relaciones:", len(relationships))
