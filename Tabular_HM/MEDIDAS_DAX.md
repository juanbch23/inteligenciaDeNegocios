# Cubo tabular H&M — medidas DAX

Servidor `localhost\TABULAR` · base `Tabular_HM` · modelo `Modelo` · compatibilidad 1200 (como pide *Cubos Tabulares y Pbi.pdf*).
Origen: `LAPTOP-IO596P6A\DEV` → `DWH_HM`. Generado por `gen_bim_hm.py`; este documento se genera desde el mismo `Model.bim`.

## Modelo

| Tabla | Rol | Origen |
|---|---|---|
| DimFecha | Dimensión | `[GENERICO].[DimFecha]` |
| DimTemporada | Dimensión | `[Ventas].[DimTemporada]` |
| DimCanal | Dimensión | `[Ventas].[DimCanal]` |
| DimDepartamento | Dimensión | `[Ventas].[DimDepartamento]` |
| DimArticulo | Dimensión | `[Ventas].[DimArticulo]` |
| DimCliente | Dimensión | `[Ventas].[DimCliente]` |
| FactVentas | Hechos: 1 fila por artículo vendido (31,788,324) | `[Ventas].[FactVentas]` |
| FactMetas | Hechos: meta diaria por escenario/sección/día (618,483) | `[Ventas].[vw_FactMetasDiaria]` |

**Relaciones:** FactVentas → DimFecha, DimCliente, DimArticulo, DimDepartamento, DimCanal, DimTemporada · FactMetas → DimFecha, DimDepartamento, DimTemporada.
DimFecha marcada como tabla de fechas; `Nombre_Mes` ordenado por `Mes_Anio`, `Nombre_Dia_Semana` por `Dia_Semana`, `Periodo` (Sep-2018) por `AnioMes`.

**Sobre las metas:** en `GoalsHyM.xlsx` el `Monto` se comporta como **meta diaria** (ventas ÷ (Monto × días) = 127 % / 110 % / 95 % para los escenarios 1/2/3; como meta mensual daría ~2.800 %). Por eso el cubo la usa expandida por día (`Ventas.vw_FactMetasDiaria`), y se suma correctamente con cualquier filtro de fechas.

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
Ventas del mismo periodo del año anterior.
```dax
CALCULATE([.Ventas], SAMEPERIODLASTYEAR(DimFecha[Fecha]))
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
Escenario elegido en el segmentador; si no hay uno solo, se usa Escenario 1.
```dax
SELECTEDVALUE(FactMetas[Escenario], "Escenario 1")
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
