/* =====================================================================
   Proyecto H&M - Inconsistencias de cada tabla del STAGE y como quedaron en el DWH
   Para la defensa: un bloque por archivo, en el mismo orden en que se explica.
     A) cuantas filas llegaron       B) inconsistencias encontradas (ANTES, en el Stage)
     C) como quedo en el DWH (DESPUES) y que hizo el ETL
   Ejecutar bloque por bloque (seleccionar + F5). El STAGE es copia fiel: todo es texto.
   Las cifras salen de los datos cargados (cambian si cambian los archivos).
   ===================================================================== */
SET NOCOUNT ON;

/* =====================================================================
   1. transaction.csv  ->  STAGE_HM.HM.StageTransactions  ->  Ventas.FactVentas
   ===================================================================== */
-- 1A. Filas
SELECT COUNT_BIG(*) AS Lineas FROM [STAGE_HM].[HM].[StageTransactions];

-- 1B.1 Lineas identicas repetidas (metodo del profesor: COUNT(1) ... GROUP BY ... ORDER BY 1 DESC)
SELECT TOP 10 COUNT(1) AS Veces, [t_dat], [customer_id], [article_id], [price], [sales_channel_id], [TemporadaID]
  FROM [STAGE_HM].[HM].[StageTransactions]
 GROUP BY [t_dat], [customer_id], [article_id], [price], [sales_channel_id], [TemporadaID]
 ORDER BY 1 DESC;

-- 1B.2 Dia de cambio de temporada: la fecha cae en dos rangos de Temporada.csv; el archivo usa la que termina
SELECT [t_dat] AS DiaDeCambio, [TemporadaID], COUNT_BIG(*) AS Ventas
  FROM [STAGE_HM].[HM].[StageTransactions]
 WHERE [t_dat] IN (SELECT REPLACE([FechaFin], '-', '') FROM [STAGE_HM].[HM].[StageTemporada])
 GROUP BY [t_dat], [TemporadaID] ORDER BY [t_dat];

-- 1B.3 Valores que no sirven (si llega data sucia): precio, fecha, cliente, articulo, canal
SELECT SUM(CASE WHEN TRY_CONVERT(FLOAT, [price]) IS NULL THEN 1 ELSE 0 END)                  AS PrecioNoNumerico,
       SUM(CASE WHEN [price] LIKE '%,%' THEN 1 ELSE 0 END)                                    AS PrecioConComa,
       SUM(CASE WHEN TRY_CONVERT(FLOAT, [price]) <= 0 THEN 1 ELSE 0 END)                      AS PrecioCeroONegativo,
       SUM(CASE WHEN TRY_CONVERT(DATE, [t_dat], 112) IS NULL THEN 1 ELSE 0 END)               AS FechaNoYYYYMMDD,
       SUM(CASE WHEN NULLIF(LTRIM(RTRIM([customer_id])), '') IS NULL THEN 1 ELSE 0 END)       AS ClienteVacio,
       SUM(CASE WHEN TRY_CONVERT(INT, [article_id]) IS NULL THEN 1 ELSE 0 END)                AS ArticuloInvalido,
       SUM(CASE WHEN ISNULL(TRY_CONVERT(TINYINT, [sales_channel_id]), 0) NOT IN (1, 2) THEN 1 ELSE 0 END) AS CanalInvalido
  FROM [STAGE_HM].[HM].[StageTransactions];

-- 1C. DESPUES: cuadre (Stage = filas del hecho + copias descartadas + lineas con error)
SELECT (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTransactions])                                AS Lineas_Stage,
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactVentas])                                     AS Filas_FactVentas,
       (SELECT SUM(CAST([LineasOrigen] AS BIGINT)) - COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactVentas]) AS Copias_Descartadas,
       (SELECT ISNULL(SUM(CAST([LineasOrigen] AS BIGINT)), 0) FROM [DWH_HM].[Ventas].[ErrorFactVentas]) AS Lineas_Error;
SELECT [Motivo], COUNT(*) AS Filas FROM [DWH_HM].[Ventas].[ErrorFactVentas] GROUP BY [Motivo];

/* =====================================================================
   2. customers.csv  ->  STAGE_HM.HM.StageCustomers  ->  Ventas.DimCliente
   ===================================================================== */
-- 2A. Filas y clientes distintos (duplicados por ID)
SELECT COUNT(*) AS Filas, COUNT(DISTINCT [customer_id]) AS ClientesDistintos,
       SUM(CASE WHEN NULLIF(LTRIM(RTRIM([customer_id])), '') IS NULL THEN 1 ELSE 0 END) AS IdVacio
  FROM [STAGE_HM].[HM].[StageCustomers];

-- 2B.1 Datos ausentes
SELECT SUM(CASE WHEN NULLIF(LTRIM(RTRIM([FN])), '') IS NULL THEN 1 ELSE 0 END)                     AS FN_Vacio,
       SUM(CASE WHEN NULLIF(LTRIM(RTRIM([Active])), '') IS NULL THEN 1 ELSE 0 END)                 AS Active_Vacio,
       SUM(CASE WHEN NULLIF(LTRIM(RTRIM([club_member_status])), '') IS NULL THEN 1 ELSE 0 END)     AS Club_Vacio,
       SUM(CASE WHEN NULLIF(LTRIM(RTRIM([fashion_news_frequency])), '') IS NULL THEN 1 ELSE 0 END) AS Noticias_Vacio,
       SUM(CASE WHEN TRY_CONVERT(FLOAT, [age]) IS NULL THEN 1 ELSE 0 END)                          AS Edad_Vacia,
       SUM(CASE WHEN TRY_CONVERT(FLOAT, [age]) NOT BETWEEN 16 AND 100 THEN 1 ELSE 0 END)           AS Edad_FueraDeRango,
       MIN(TRY_CONVERT(FLOAT, [age])) AS EdadMinima, MAX(TRY_CONVERT(FLOAT, [age])) AS EdadMaxima
  FROM [STAGE_HM].[HM].[StageCustomers];

-- 2B.2 Valores de texto (el mismo valor escrito distinto)
SELECT [fashion_news_frequency], COUNT(*) AS Clientes FROM [STAGE_HM].[HM].[StageCustomers]
 GROUP BY [fashion_news_frequency] ORDER BY 2 DESC;

-- 2B.3 Combinaciones contradictorias (FN = suscrito a noticias; frecuencia = cada cuanto las recibe)
SELECT [FN], [Active], [club_member_status], [fashion_news_frequency], COUNT(*) AS Clientes
  FROM [STAGE_HM].[HM].[StageCustomers]
 GROUP BY [FN], [Active], [club_member_status], [fashion_news_frequency] ORDER BY 5 DESC;

-- 2B.4 Codigo postal que concentra muchisimos clientes (posible valor por defecto)
SELECT TOP 3 LEFT([postal_code], 20) + '...' AS CodigoPostal, COUNT(*) AS Clientes
  FROM [STAGE_HM].[HM].[StageCustomers] GROUP BY [postal_code] ORDER BY 2 DESC;

-- 2C. DESPUES: como quedaron en la dimension y que se rechazo
SELECT [RangoEdad], COUNT(*) AS Clientes FROM [DWH_HM].[Ventas].[DimCliente] WHERE [ClienteKey] > 0 GROUP BY [RangoEdad] ORDER BY 1;
SELECT [ClubMemberStatus], COUNT(*) AS Clientes FROM [DWH_HM].[Ventas].[DimCliente] WHERE [ClienteKey] > 0 GROUP BY [ClubMemberStatus];
SELECT [FashionNewsFrequency], COUNT(*) AS Clientes FROM [DWH_HM].[Ventas].[DimCliente] WHERE [ClienteKey] > 0 GROUP BY [FashionNewsFrequency];
SELECT * FROM [DWH_HM].[dbo].[ErrorMaestro] WHERE [Tabla] = N'DimCliente';

/* =====================================================================
   3. articles.csv  ->  STAGE_HM.HM.StageArticles  ->  Ventas.DimArticulo / Ventas.DimDepartamento
   ===================================================================== */
-- 3A. Filas y articulos distintos
SELECT COUNT(*) AS Filas, COUNT(DISTINCT [article_id]) AS ArticulosDistintos,
       SUM(CASE WHEN TRY_CONVERT(INT, [article_id]) IS NULL THEN 1 ELSE 0 END) AS IdInvalido,
       SUM(CASE WHEN LEFT([article_id], 1) = '0' THEN 1 ELSE 0 END)          AS IdConCeroAdelante
  FROM [STAGE_HM].[HM].[StageArticles];

-- 3B.1 Textos que significan "no hay dato" (vacio, Unknown, undefined)
SELECT u.[Campo], COUNT(*) AS Filas
  FROM [STAGE_HM].[HM].[StageArticles] a
 CROSS APPLY (VALUES ('product_type_name', a.[product_type_name]), ('product_group_name', a.[product_group_name]),
                     ('graphical_appearance_name', a.[graphical_appearance_name]), ('colour_group_name', a.[colour_group_name]),
                     ('perceived_colour_value_name', a.[perceived_colour_value_name]),
                     ('perceived_colour_master_name', a.[perceived_colour_master_name]),
                     ('garment_group_name', a.[garment_group_name]), ('detail_desc', a.[detail_desc])) u([Campo], [Valor])
 WHERE NULLIF(LTRIM(RTRIM(u.[Valor])), '') IS NULL OR LTRIM(RTRIM(u.[Valor])) IN ('Unknown', 'undefined')
 GROUP BY u.[Campo] ORDER BY 2 DESC;

-- 3B.2 Articulos vendidos que no estan en el catalogo (integridad referencial)
SELECT COUNT(*) AS VendidosSinCatalogo
  FROM (SELECT DISTINCT TRY_CONVERT(INT, [article_id]) AS a FROM [STAGE_HM].[HM].[StageTransactions]) t
 WHERE NOT EXISTS (SELECT 1 FROM [STAGE_HM].[HM].[StageArticles] s WHERE TRY_CONVERT(INT, s.[article_id]) = t.a);

-- 3C. DESPUES
SELECT COUNT(*) AS Articulos FROM [DWH_HM].[Ventas].[DimArticulo] WHERE [ArticuloKey] > 0;
SELECT COUNT(*) AS DepartamentoSeccion FROM [DWH_HM].[Ventas].[DimDepartamento] WHERE [DepartamentoKey] > 0;
SELECT [ProductTypeName], COUNT(*) AS Articulos FROM [DWH_HM].[Ventas].[DimArticulo] WHERE [ProductTypeName] = N'Sin Datos' GROUP BY [ProductTypeName];
SELECT * FROM [DWH_HM].[dbo].[ErrorMaestro] WHERE [Tabla] = N'DimArticulo';

/* =====================================================================
   4. DimFecha.csv  ->  STAGE_HM.HM.StageFecha  ->  GENERICO.DimFecha
   ===================================================================== */
-- 4A. Filas, fechas distintas y rango (sin huecos: dias esperados = filas)
SELECT COUNT(*) AS Filas, COUNT(DISTINCT [Fecha]) AS FechasDistintas,
       MIN(TRY_CONVERT(DATE, [Fecha])) AS Desde, MAX(TRY_CONVERT(DATE, [Fecha])) AS Hasta,
       DATEDIFF(DAY, MIN(TRY_CONVERT(DATE, [Fecha])), MAX(TRY_CONVERT(DATE, [Fecha]))) + 1 AS DiasEsperados
  FROM [STAGE_HM].[HM].[StageFecha];

-- 4B. Campos calculados que no corresponden a la fecha (1900-01-07 fue domingo)
SELECT SUM(CASE WHEN TRY_CONVERT(INT, [Fin_Semana]) <> CASE WHEN DATEDIFF(DAY, '19000107', TRY_CONVERT(DATE, [Fecha])) % 7 IN (0, 6)
                                                            THEN 1 ELSE 0 END THEN 1 ELSE 0 END) AS FinSemana_Mal,
       SUM(CASE WHEN TRY_CONVERT(INT, [Anio]) <> YEAR(TRY_CONVERT(DATE, [Fecha])) THEN 1 ELSE 0 END)   AS Anio_Mal,
       SUM(CASE WHEN TRY_CONVERT(INT, [Mes_Anio]) <> MONTH(TRY_CONVERT(DATE, [Fecha])) THEN 1 ELSE 0 END) AS Mes_Mal,
       SUM(CASE WHEN TRY_CONVERT(INT, [Dia_Mes]) <> DAY(TRY_CONVERT(DATE, [Fecha])) THEN 1 ELSE 0 END) AS Dia_Mal
  FROM [STAGE_HM].[HM].[StageFecha];
SELECT [Nombre_Dia_Semana], [Fin_Semana], COUNT(*) AS Dias FROM [STAGE_HM].[HM].[StageFecha]
 GROUP BY [Nombre_Dia_Semana], [Fin_Semana] ORDER BY 1;

-- 4C. DESPUES: Fin_Semana recalculado desde la fecha
SELECT [Nombre_Dia_Semana], [Fin_Semana], COUNT(*) AS Dias FROM [DWH_HM].[GENERICO].[DimFecha]
 WHERE [FechaKey] > 0 GROUP BY [Nombre_Dia_Semana], [Fin_Semana] ORDER BY 1;
SELECT * FROM [DWH_HM].[dbo].[ErrorMaestro] WHERE [Tabla] = N'DimFecha';

/* =====================================================================
   5. Temporada.csv  ->  STAGE_HM.HM.StageTemporada  ->  Ventas.DimTemporada
   ===================================================================== */
-- 5A. Las temporadas tal como vienen
SELECT [TemporadaID], [Temporada], [FechaInicio], [FechaFin] FROM [STAGE_HM].[HM].[StageTemporada]
 ORDER BY TRY_CONVERT(INT, [TemporadaID]);

-- 5B. Dia compartido: una temporada termina el mismo dia que empieza la siguiente
SELECT a.[Temporada] AS Termina, b.[Temporada] AS Empieza, a.[FechaFin] AS DiaCompartido
  FROM [STAGE_HM].[HM].[StageTemporada] a
  JOIN [STAGE_HM].[HM].[StageTemporada] b ON a.[FechaFin] = b.[FechaInicio] AND a.[TemporadaID] <> b.[TemporadaID];

-- 5C. DESPUES: estacion y año derivados del nombre; el dia compartido va a la que termina (ver 1B.2)
SELECT [TemporadaID], [Temporada], [Estacion], [Anio], [FechaInicio], [FechaFin]
  FROM [DWH_HM].[Ventas].[DimTemporada] WHERE [TemporadaKey] > 0 ORDER BY [TemporadaID];

/* =====================================================================
   6. GoalsHyM.xlsx  ->  STAGE_HM.HM.StageGoals  ->  Ventas.FactMetas
   ===================================================================== */
-- 6A. Filas por escenario y periodo
SELECT [Escenario], COUNT(*) AS Metas, MIN([AnioMes]) AS Desde, MAX([AnioMes]) AS Hasta,
       MIN([Monto]) AS MontoMin, MAX([Monto]) AS MontoMax
  FROM [STAGE_HM].[HM].[StageGoals] GROUP BY [Escenario];

-- 6B.1 Metas repetidas (misma clave)
SELECT COUNT(*) AS ClavesRepetidas
  FROM (SELECT [Escenario], [department_name], [section_name], [TemporadaID], [AnioMes]
          FROM [STAGE_HM].[HM].[StageGoals]
         GROUP BY [Escenario], [department_name], [section_name], [TemporadaID], [AnioMes] HAVING COUNT(*) > 1) x;

-- 6B.2 Escenarios que no van de menor a mayor (Escenario 1 < 2 < 3)
SELECT COUNT(*) AS Combinaciones, SUM(CASE WHEN NOT (e1 < e2 AND e2 < e3) THEN 1 ELSE 0 END) AS Desordenadas
  FROM (SELECT MAX(CASE WHEN [Escenario] = 'Escenario 1' THEN [Monto] END) AS e1,
               MAX(CASE WHEN [Escenario] = 'Escenario 2' THEN [Monto] END) AS e2,
               MAX(CASE WHEN [Escenario] = 'Escenario 3' THEN [Monto] END) AS e3
          FROM [STAGE_HM].[HM].[StageGoals]
         GROUP BY [department_name], [section_name], [TemporadaID], [AnioMes]) m;

-- 6B.3 Departamento/seccion de la meta que no existe en los articulos
SELECT COUNT(*) AS SeccionesSinArticulos
  FROM (SELECT DISTINCT [department_name], [section_name] FROM [STAGE_HM].[HM].[StageGoals]) g
 WHERE NOT EXISTS (SELECT 1 FROM [STAGE_HM].[HM].[StageArticles] a
                    WHERE LTRIM(RTRIM(a.[department_name])) = LTRIM(RTRIM(g.[department_name]))
                      AND LTRIM(RTRIM(a.[section_name])) = LTRIM(RTRIM(g.[section_name])));

-- 6C. DESPUES: cuadre y rechazos
SELECT (SELECT COUNT(*) FROM [STAGE_HM].[HM].[StageGoals]) AS Metas_Stage,
       (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[FactMetas]) AS Metas_DWH,
       (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[ErrorFactMetas]) AS Metas_Error;
SELECT [Motivo], COUNT(*) AS Filas FROM [DWH_HM].[Ventas].[ErrorFactMetas] GROUP BY [Motivo];

/* =====================================================================
   Resumen de todo lo anterior que registra el propio ETL en cada carga
   ===================================================================== */
SELECT [Entidad], [Campo], [TipoProblema], [Descripcion], [Tratamiento], [Cantidad]
  FROM [DWH_HM].[dbo].[CalidadDatos]
 WHERE [AuditKey] IN (SELECT MAX([AuditKey]) FROM [DWH_HM].[dbo].[CalidadDatos] GROUP BY [Entidad])
 ORDER BY [Entidad], [TipoProblema], [Campo];
