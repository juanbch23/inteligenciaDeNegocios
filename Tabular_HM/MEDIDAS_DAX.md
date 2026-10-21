# Cubo tabular H&M — medidas DAX

Servidor `localhost\TABULAR` · base `Tabular_HM` · modelo `Modelo` · compatibilidad 1200 (como pide *Cubos Tabulares y Pbi.pdf*).
Origen: `LAPTOP-IO596P6A\DEV` → `DWH_HM` (vistas de `sql/04_vistas_cubo.sql`). Generado por `gen_bim_hm.py`; este documento sale del mismo `Model.bim`.

Los indicadores del caso (carpeta *6. Indicadores del caso*) están explicados en `docs/Indicadores_y_Dashboards.md`.

**Total: 73 medidas.**

## 1. Ventas

### `.Ventas`  ·  tabla FactVentas  ·  formato `#,0.00`
Suma del precio de cada artículo vendido.
```dax
SUM(FactVentas[Precio])
```

### `.Ticket_Promedio`  ·  tabla FactVentas  ·  formato `#,0.00`
Precio promedio por artículo vendido.
```dax
AVERAGE(FactVentas[Precio])
```

### `.Transacciones`  ·  tabla FactVentas  ·  formato `#,0`
Artículos vendidos (una fila por artículo).
```dax
COUNTROWS(FactVentas)
```

### `.Clientes_Unicos`  ·  tabla FactVentas  ·  formato `#,0`
```dax
DISTINCTCOUNT(FactVentas[ClienteKey])
```

### `.Articulos_Distintos`  ·  tabla FactVentas  ·  formato `#,0`
```dax
DISTINCTCOUNT(FactVentas[ArticuloKey])
```

### `.Ventas_por_Cliente`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
DIVIDE([.Ventas], [.Clientes_Unicos])
```

### `.Articulos_por_Cliente`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
DIVIDE([.Transacciones], [.Clientes_Unicos])
```

### `.Ventas_Online`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
CALCULATE([.Ventas], DimCanal[NombreCanal] = "Online")
```

### `.Ventas_Tienda`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
CALCULATE([.Ventas], DimCanal[NombreCanal] = "Tienda fisica")
```

### `.%Ventas_Online`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE([.Ventas_Online], [.Ventas])
```

### `.%Participacion`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
Participación sobre el total visible.
```dax
DIVIDE([.Ventas], CALCULATE([.Ventas], ALLSELECTED()))
```

## 2. Tiempo

### `.Anio_Actual`  ·  tabla DimFecha  ·  formato `0`
```dax
MAX(DimFecha[Anio])
```

### `.Acumulado_Anual`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
TOTALYTD([.Ventas], DimFecha[Fecha])
```

### `.Ventas_Ultimos_Dias_7`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
CALCULATE ( [.Ventas], DATESINPERIOD ( DimFecha[Fecha], MAX ( DimFecha[Fecha] ), -7, DAY ) )
```

### `.Ventas_Ultimos_Dias_7_avg`  ·  tabla FactVentas  ·  formato `#,0.00`
Promedio diario de ventas de los últimos 7 días (media móvil).
```dax
AVERAGEX ( DATESINPERIOD ( DimFecha[Fecha], MAX ( DimFecha[Fecha] ), -7, DAY ), [.Ventas] )
```

### `.Ventas_Mismo_Periodo_AA`  ·  tabla FactVentas  ·  formato `#,0.00`
Ventas de exactamente los mismos días del año anterior (SAMEPERIODLASTYEAR completaba septiembre 2019).
```dax
VAR fechas = SELECTCOLUMNS(VALUES(DimFecha[Fecha]), "F", EDATE(DimFecha[Fecha], -12))
RETURN
    IF(HASONEVALUE(DimFecha[Anio]),                       -- solo tiene sentido dentro de un año
       CALCULATE([.Ventas], ALL(DimFecha), TREATAS(fechas, DimFecha[Fecha])))
```

### `.%Crecimiento_Interanual`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE([.Ventas] - [.Ventas_Mismo_Periodo_AA], [.Ventas_Mismo_Periodo_AA])
```

### `.Ventas_Anio_Actual`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
VAR anio = [.Anio_Actual]
RETURN
    CALCULATE([.Ventas], ALL(DimFecha[Anio]), DimFecha[Anio] = anio)
```

### `.Ventas_Anio_prev-1`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
VAR anio = [.Anio_Actual] - 1
RETURN
    CALCULATE([.Ventas], ALL(DimFecha[Anio]), DimFecha[Anio] = anio)
```

### `.Ventas_Anio_prev-2`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
VAR anio = [.Anio_Actual] - 2
RETURN
    CALCULATE([.Ventas], ALL(DimFecha[Anio]), DimFecha[Anio] = anio)
```

### `.%var_Ventas`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE([.Ventas_Anio_Actual] - [.Ventas_Anio_prev-1], [.Ventas_Anio_prev-1])
```

### `.%Var_Ventas_I`  ·  tabla FactVentas
```dax
VAR si = IF([.%var_Ventas] < 0, "▼", "▲")
RETURN
    IF(ISBLANK([.%var_Ventas]), BLANK(), FORMAT([.%var_Ventas], "0.00 %") & "  " & si)
```

### `.Titulo_Varianza`  ·  tabla FactVentas
```dax
"Año " & [.Anio_Actual] & " vs " & ([.Anio_Actual] - 1)
```

### `.%var_Ventas1`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE([.Ventas_Anio_Actual] - [.Ventas_Anio_prev-2], [.Ventas_Anio_prev-2])
```

### `.%Var_Ventas1_I`  ·  tabla FactVentas
```dax
VAR si = IF([.%var_Ventas1] < 0, "▼", "▲")
RETURN
    IF(ISBLANK([.%var_Ventas1]), BLANK(), FORMAT([.%var_Ventas1], "0.00 %") & "  " & si)
```

### `.Titulo_Varianza1`  ·  tabla FactVentas
```dax
"Año " & [.Anio_Actual] & " vs " & ([.Anio_Actual] - 2)
```

### `.Titulo_Comparacion_anual`  ·  tabla FactVentas
```dax
"Comparación anual " & [.Anio_Actual] & " - " & ([.Anio_Actual] - 1) & " - " & ([.Anio_Actual] - 2)
```

## 3. Pareto

### `.Titulo_Dinamico_GrupoIndice`  ·  tabla DimArticulo
```dax
VAR grupo = DISTINCT(DimArticulo[GrupoIndice])
VAR grupo_S = CONCATENATEX(grupo, DimArticulo[GrupoIndice], " - ")
VAR CANTIDAD = COUNTROWS(grupo)
VAR TITULO = IF(CANTIDAD > 4, "Pareto de ventas por sección (todos los grupos)", "Pareto de ventas por sección: " & grupo_S)
RETURN
    TITULO
```

### `.%Pareto_Ventas_Departamento`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
Porcentaje acumulado de ventas (departamentos ordenados de mayor a menor).
```dax
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
    TOTAL
```

### `.%Pareto_Ventas_Seccion`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
Porcentaje acumulado de ventas (secciones ordenadas de mayor a menor).
```dax
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
    TOTAL
```

## 4. Metas

### `.Escenario_Activo`  ·  tabla FactMetas
Escenario elegido en el segmentador; si no hay uno solo, se usa el Escenario 2 (meta oficial del caso).
```dax
SELECTEDVALUE(FactMetas[Escenario], "Escenario 2")
```

### `.Meta`  ·  tabla FactMetas  ·  formato `#,0.00`
```dax
VAR esc = [.Escenario_Activo]
RETURN
    CALCULATE(SUM(FactMetas[MetaDiaria]), FactMetas[Escenario] = esc)
```

### `.%Cumplimiento_Meta`  ·  tabla FactMetas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE([.Ventas], [.Meta])
```

### `.Brecha_Meta`  ·  tabla FactMetas  ·  formato `#,0.00`
```dax
IF(ISBLANK([.Meta]), BLANK(), [.Ventas] - [.Meta])
```

### `.Cumplimiento_I`  ·  tabla FactMetas
```dax
VAR c = [.%Cumplimiento_Meta]
RETURN
    IF(ISBLANK(c), BLANK(), FORMAT(c, "0.0 %") & IF(c >= 1, "  ▲", "  ▼"))
```

### `.Color_Cumplimiento`  ·  tabla FactMetas
Verde >= 100 %, ámbar >= 90 %, rojo < 90 % (formato condicional por valor de campo).
```dax
VAR c = [.%Cumplimiento_Meta]
RETURN
    SWITCH(TRUE(), ISBLANK(c), BLANK(), c >= 1, "#2E7D32", c >= 0.9, "#F9A825", "#C62828")
```

### `.Titulo_Ventas_vs_Meta`  ·  tabla FactMetas
```dax
"Ventas vs meta diaria acumulada - " & [.Escenario_Activo]
```

## 5. Clientes

### `.Clientes_Registrados`  ·  tabla DimCliente  ·  formato `#,0`
```dax
COUNTROWS(DimCliente)
```

### `.Edad_Promedio_Compradores`  ·  tabla DimCliente  ·  formato `0.0`
Edad promedio de los clientes que compraron en el contexto.
```dax
CALCULATE(AVERAGE(DimCliente[Edad]), CROSSFILTER(FactVentas[ClienteKey], DimCliente[ClienteKey], BOTH))
```

### `.%Clientes_Compradores`  ·  tabla DimCliente  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE([.Clientes_Unicos], [.Clientes_Registrados])
```

## 6. Indicadores del caso\Cesta

### `.Cestas`  ·  tabla FactVentas  ·  formato `#,0`
Cesta = mismo cliente + mismo día + mismo canal (no hay número de pedido).
```dax
COUNTROWS(SUMMARIZE(FactVentas, FactVentas[ClienteKey], FactVentas[FechaKey], FactVentas[CanalKey]))
```

### `.Ticket_Cesta`  ·  tabla FactVentas  ·  formato `#,0.00`
Ventas / cestas.
```dax
DIVIDE([.Ventas], [.Cestas])
```

### `.Articulos_por_Cesta`  ·  tabla FactVentas  ·  formato `#,0.00`
Artículos (líneas) / cestas.
```dax
DIVIDE([.Transacciones], [.Cestas])
```

## 6. Indicadores del caso\Clientes

### `.Clientes_Nuevos`  ·  tabla DimCliente  ·  formato `#,0`
Clientes cuya primera compra cae en el periodo filtrado.
```dax
VAR d1 = MIN(DimFecha[Fecha])
VAR d2 = MAX(DimFecha[Fecha])
RETURN
    CALCULATE(COUNTROWS(DimCliente), DimCliente[FechaPrimeraCompra] >= d1, DimCliente[FechaPrimeraCompra] <= d2)
```

### `.%Recompra`  ·  tabla DimCliente  ·  formato `0.00 %;-0.00 %;0.00 %`
Compradores con compra en más de un mes.
```dax
DIVIDE(CALCULATE(COUNTROWS(DimCliente), DimCliente[MesesConCompra] > 1),
       CALCULATE(COUNTROWS(DimCliente), DimCliente[MesesConCompra] >= 1))
```

### `.%Retencion_2019_2020`  ·  tabla DimCliente  ·  formato `0.00 %;-0.00 %;0.00 %`
Compradores de 2019 que vuelven en 2020.
```dax
DIVIDE(CALCULATE(COUNTROWS(DimCliente), DimCliente[Compra2019] = 1, DimCliente[Compra2020] = 1),
       CALCULATE(COUNTROWS(DimCliente), DimCliente[Compra2019] = 1))
```

### `.Color_Retencion`  ·  tabla DimCliente
Meta propuesta >= 65 %.
```dax
VAR x = [.%Retencion_2019_2020]
RETURN
    SWITCH(TRUE(), ISBLANK(x), BLANK(), x >= 0.65, "#2E7D32", x >= 0.65 - 0.05, "#F9A825", "#C62828")
```

### `.%Clientes_Omnicanal`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE(CALCULATE([.Clientes_Unicos], DimCliente[TipoCanal] = "Omnicanal"), [.Clientes_Unicos])
```

### `.%Penetracion_Club`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE(CALCULATE([.Clientes_Unicos], DimCliente[ClubActivo] = "Club activo"), [.Clientes_Unicos])
```

### `.%Ventas_Top20_Clientes`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
DIVIDE(CALCULATE([.Ventas], DimCliente[SegmentoValor] = "1. Top 20 %"), [.Ventas])
```

### `.Ventas_por_Cliente_Omnicanal`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
CALCULATE([.Ventas_por_Cliente], DimCliente[TipoCanal] = "Omnicanal")
```

### `.Ventas_por_Cliente_UnCanal`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
CALCULATE([.Ventas_por_Cliente], DimCliente[TipoCanal] IN {"Solo online", "Solo tienda"})
```

### `.Multiplicador_Omnicanal`  ·  tabla FactVentas  ·  formato `0.0"x"`
Cuántas veces más compra el cliente omnicanal.
```dax
DIVIDE([.Ventas_por_Cliente_Omnicanal], [.Ventas_por_Cliente_UnCanal])
```

### `.%Plus_Club`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
Cuánto más compra el cliente con club activo.
```dax
DIVIDE(CALCULATE([.Ventas_por_Cliente], DimCliente[ClubActivo] = "Club activo"),
       CALCULATE([.Ventas_por_Cliente], DimCliente[ClubActivo] = "No activo")) - 1
```

## 6. Indicadores del caso\Crecimiento

### `.Delta_Interanual`  ·  tabla FactVentas  ·  formato `#,0.00`
Diferencia contra el mismo periodo del año anterior.
```dax
IF(ISBLANK([.Ventas_Mismo_Periodo_AA]), BLANK(), [.Ventas] - [.Ventas_Mismo_Periodo_AA])
```

### `.%Interanual_Tienda`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
CALCULATE([.%Crecimiento_Interanual], DimCanal[NombreCanal] = "Tienda fisica")
```

### `.%Interanual_Online`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
CALCULATE([.%Crecimiento_Interanual], DimCanal[NombreCanal] = "Online")
```

### `.Interanual_I`  ·  tabla FactVentas
```dax
VAR x = [.%Crecimiento_Interanual]
RETURN
    IF(ISBLANK(x), BLANK(), FORMAT(x, "+0.0 %;-0.0 %") & IF(x >= 0, "  ▲", "  ▼"))
```

### `.Color_Interanual`  ·  tabla FactVentas
Meta propuesta >= 0 %.
```dax
VAR x = [.%Crecimiento_Interanual]
RETURN
    SWITCH(TRUE(), ISBLANK(x), BLANK(), x >= 0, "#2E7D32", x >= 0 - 0.05, "#F9A825", "#C62828")
```

### `.Ventas_Acumuladas`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
CALCULATE([.Ventas], FILTER(ALLSELECTED(DimFecha[Fecha]), DimFecha[Fecha] <= MAX(DimFecha[Fecha])))
```

## 6. Indicadores del caso\Metas

### `.Meta_Acumulada`  ·  tabla FactMetas  ·  formato `#,0.00`
```dax
CALCULATE([.Meta], FILTER(ALLSELECTED(DimFecha[Fecha]), DimFecha[Fecha] <= MAX(DimFecha[Fecha])))
```

### `.Secciones_con_Meta`  ·  tabla FactMetas  ·  formato `#,0`
```dax
COUNTROWS(FILTER(VALUES(DimDepartamento[Seccion]), NOT ISBLANK([.Meta])))
```

### `.Secciones_Cumplen`  ·  tabla FactMetas  ·  formato `#,0`
```dax
COUNTROWS(FILTER(VALUES(DimDepartamento[Seccion]), [.%Cumplimiento_Meta] >= 1))
```

### `.Secciones_Bajo_50`  ·  tabla FactMetas  ·  formato `#,0`
```dax
COUNTROWS(FILTER(VALUES(DimDepartamento[Seccion]), NOT ISBLANK([.Meta]) && [.%Cumplimiento_Meta] < 0.5))
```

### `.Cumplimiento_Top5`  ·  tabla FactMetas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
VAR r = RANKX(FILTER(ALLSELECTED(DimDepartamento[Seccion]), NOT ISBLANK([.Meta])), [.%Cumplimiento_Meta], , DESC)
RETURN
    IF(HASONEVALUE(DimDepartamento[Seccion]) && NOT ISBLANK([.Meta]) && r <= 5, [.%Cumplimiento_Meta])
```

### `.Cumplimiento_Bottom5`  ·  tabla FactMetas  ·  formato `0.00 %;-0.00 %;0.00 %`
```dax
VAR r = RANKX(FILTER(ALLSELECTED(DimDepartamento[Seccion]), NOT ISBLANK([.Meta])), [.%Cumplimiento_Meta], , ASC)
RETURN
    IF(HASONEVALUE(DimDepartamento[Seccion]) && NOT ISBLANK([.Meta]) && r <= 5, [.%Cumplimiento_Meta])
```

## 6. Indicadores del caso\Narrativa

### `.Narrativa_Estrategica`  ·  tabla FactVentas
Elige un año para ver la comparación interanual.
```dax
VAR y = [.%Crecimiento_Interanual]
RETURN
    "Cumplimos el " & FORMAT([.%Cumplimiento_Meta], "0 %") & " de la meta, pero vendemos " & FORMAT(y, "+0.0 %;-0.0 %")
        & " vs. el año anterior (tienda " & FORMAT([.%Interanual_Tienda], "+0.0 %;-0.0 %") & ", online "
        & FORMAT([.%Interanual_Online], "+0.0 %;-0.0 %") & "). El cliente omnicanal compra "
        & FORMAT([.Multiplicador_Omnicanal], "0.0") & " veces más."
```

### `.Narrativa_Cliente`  ·  tabla FactVentas
```dax
"El cliente omnicanal compra " & FORMAT([.Multiplicador_Omnicanal], "0.0") & " veces más y el de club activo "
    & FORMAT([.%Plus_Club], "+0 %") & "; el top 20 % genera el " & FORMAT([.%Ventas_Top20_Clientes], "0 %")
    & " de la venta. Descuento implícito: " & FORMAT([.%Descuento_Implicito], "0.0 %") & "."
```

### `.Narrativa_Metas`  ·  tabla FactMetas
```dax
"Llegamos al " & FORMAT([.%Cumplimiento_Meta], "0 %") & " de la meta, pero solo " & [.Secciones_Cumplen] & " de "
    & [.Secciones_con_Meta] & " secciones cumplen y " & [.Secciones_Bajo_50] & " no llegan al 50 %: metas mal repartidas."
```

## 6. Indicadores del caso\Precio

### `.Precio_Lista`  ·  tabla FactVentas  ·  formato `#,0.00`
```dax
SUM(FactVentas[PrecioLista])
```

### `.%Descuento_Implicito`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
1 - precio cobrado / precio máximo observado del artículo.
```dax
IF([.Precio_Lista] > 0, 1 - DIVIDE([.Ventas], [.Precio_Lista]))
```

### `.%Lineas_Descuento_30`  ·  tabla FactVentas  ·  formato `0.00 %;-0.00 %;0.00 %`
Líneas vendidas con más de 30 % de descuento.
```dax
DIVIDE(CALCULATE([.Transacciones], FactVentas[BandaDescuento] = "4. Más de 30 %"), [.Transacciones])
```

### `.Color_Descuento`  ·  tabla FactVentas
Meta propuesta <= 17 %.
```dax
VAR x = [.%Descuento_Implicito]
RETURN
    SWITCH(TRUE(), ISBLANK(x), BLANK(), x <= 0.17, "#2E7D32", x <= 0.17 + 0.02, "#F9A825", "#C62828")
```
