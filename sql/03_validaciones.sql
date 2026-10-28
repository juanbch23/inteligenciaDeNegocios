/* =====================================================================
   Proyecto H&M - Validaciones despues de ejecutar el ETL (o el job Job_HM)
   Instancia: LAPTOP-IO596P6A\DEV
   Todo debe cuadrar: lo que entro al STAGE = lo que quedo en el DWH
   + duplicados descartados + filas enviadas a las tablas de error (con motivo).
   ===================================================================== */
SET NOCOUNT ON;

PRINT '1) Archivo -> STAGE (filas cargadas)';
SELECT 'StageArticles' AS Tabla, COUNT_BIG(*) AS Filas FROM [STAGE_HM].[HM].[StageArticles]
UNION ALL SELECT 'StageCustomers',    COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageCustomers]
UNION ALL SELECT 'StageTransactions', COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTransactions]
UNION ALL SELECT 'StageFecha',        COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageFecha]
UNION ALL SELECT 'StageTemporada',    COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTemporada]
UNION ALL SELECT 'StageGoals',        COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageGoals];

PRINT '2) Maestros: cada fila del STAGE quedo en la dimension o en ErrorMaestro (SinExplicar debe ser 0)';
-- Se revisa fila por fila (y no "total de la dimension"): el MERGE nunca borra, asi que la dimension
-- puede tener ademas clientes/articulos de cargas anteriores.
SELECT 'DimCliente' AS Tabla, COUNT(*) AS Stage,
       SUM(CASE WHEN e.[FilaOrigen] IS NULL THEN 1 ELSE 0 END)                           AS Cargadas,
       SUM(CASE WHEN e.[FilaOrigen] IS NOT NULL THEN 1 ELSE 0 END)                       AS ErrorMaestro,
       SUM(CASE WHEN e.[FilaOrigen] IS NULL AND d.[CustomerID] IS NULL THEN 1 ELSE 0 END) AS SinExplicar
  FROM [STAGE_HM].[HM].[StageCustomers] s
  LEFT JOIN [DWH_HM].[dbo].[ErrorMaestro] e ON e.[Tabla] = N'DimCliente' AND e.[FilaOrigen] = s.[FilaOrigen]
  LEFT JOIN [DWH_HM].[Ventas].[DimCliente] d ON d.[CustomerID] = LTRIM(RTRIM(s.[customer_id]))
UNION ALL
SELECT 'DimArticulo', COUNT(*),
       SUM(CASE WHEN e.[FilaOrigen] IS NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN e.[FilaOrigen] IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN e.[FilaOrigen] IS NULL AND d.[ArticleID] IS NULL THEN 1 ELSE 0 END)
  FROM [STAGE_HM].[HM].[StageArticles] s
  LEFT JOIN [DWH_HM].[dbo].[ErrorMaestro] e ON e.[Tabla] = N'DimArticulo' AND e.[FilaOrigen] = s.[FilaOrigen]
  LEFT JOIN [DWH_HM].[Ventas].[DimArticulo] d ON d.[ArticleID] = TRY_CONVERT(INT, LTRIM(RTRIM(s.[article_id])))
UNION ALL
SELECT 'DimFecha', COUNT(*),
       SUM(CASE WHEN e.[FilaOrigen] IS NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN e.[FilaOrigen] IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN e.[FilaOrigen] IS NULL AND d.[Fecha] IS NULL THEN 1 ELSE 0 END)
  FROM [STAGE_HM].[HM].[StageFecha] s
  LEFT JOIN [DWH_HM].[dbo].[ErrorMaestro] e ON e.[Tabla] = N'DimFecha' AND e.[FilaOrigen] = s.[FilaOrigen]
  LEFT JOIN [DWH_HM].[GENERICO].[DimFecha] d
         ON d.[Fecha] = COALESCE(TRY_CONVERT(DATE, LTRIM(RTRIM(s.[Fecha]))), TRY_CONVERT(DATE, LTRIM(RTRIM(s.[FechaKey]))))
UNION ALL
SELECT 'DimTemporada', COUNT(*),
       SUM(CASE WHEN e.[FilaOrigen] IS NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN e.[FilaOrigen] IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN e.[FilaOrigen] IS NULL AND d.[TemporadaID] IS NULL THEN 1 ELSE 0 END)
  FROM [STAGE_HM].[HM].[StageTemporada] s
  LEFT JOIN [DWH_HM].[dbo].[ErrorMaestro] e ON e.[Tabla] = N'DimTemporada' AND e.[FilaOrigen] = s.[FilaOrigen]
  LEFT JOIN [DWH_HM].[Ventas].[DimTemporada] d ON d.[TemporadaID] = TRY_CONVERT(INT, TRY_CONVERT(FLOAT, LTRIM(RTRIM(s.[TemporadaID]))));

PRINT '3) Hechos: STAGE = lineas en Fact + lineas en Error (LineasOrigen cuenta los duplicados identicos)';
SELECT 'Ventas' AS Hecho,
       (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTransactions])                  AS Stage,
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactVentas])                       AS FilasFact,
       (SELECT SUM(CAST([LineasOrigen] AS BIGINT)) - COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactVentas]) AS DuplicadosDescartados,
       (SELECT ISNULL(SUM(CAST([LineasOrigen] AS BIGINT)), 0) FROM [DWH_HM].[Ventas].[ErrorFactVentas]) AS LineasError,
       (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTransactions])
     - (SELECT SUM(CAST([LineasOrigen] AS BIGINT)) FROM [DWH_HM].[Ventas].[FactVentas])
     - (SELECT ISNULL(SUM(CAST([LineasOrigen] AS BIGINT)), 0) FROM [DWH_HM].[Ventas].[ErrorFactVentas]) AS Diferencia
UNION ALL
SELECT 'Metas',
       (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageGoals]),
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactMetas]),
       0,
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[ErrorFactMetas]),
       (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageGoals])
     - (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactMetas])
     - (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[ErrorFactMetas]);

PRINT '4) Motivos de descarte: que archivo, que columna, por que y cuantas filas';
WITH E AS (
    SELECT N'transaction.csv' AS Archivo, [Motivo], [LineasOrigen] AS Lineas FROM [DWH_HM].[Ventas].[ErrorFactVentas]
    UNION ALL SELECT N'GoalsHyM.xlsx', [Motivo], 1 FROM [DWH_HM].[Ventas].[ErrorFactMetas]
    UNION ALL SELECT CASE [Tabla] WHEN N'DimCliente' THEN N'customers.csv' WHEN N'DimArticulo' THEN N'articles.csv'
                                  WHEN N'DimFecha' THEN N'DimFecha.csv' ELSE N'Temporada.csv' END, [Motivo], 1
                FROM [DWH_HM].[dbo].[ErrorMaestro])
SELECT [Archivo],
       CASE WHEN [Motivo] LIKE N'%repetid%'             THEN N'(fila repetida)'
            WHEN [Motivo] LIKE N'Fecha de inicio%'      THEN N'FechaInicio / FechaFin'
            WHEN [Motivo] LIKE N'La fecha no cae%'      THEN N't_dat (sin temporada)'
            WHEN [Motivo] LIKE N'Mes fuera%' OR [Motivo] LIKE N'A_o-mes%' THEN N'AnioMes'
            WHEN [Motivo] LIKE N'Fecha%'                THEN CASE WHEN [Archivo] = N'transaction.csv' THEN N't_dat' ELSE N'Fecha' END
            WHEN [Motivo] LIKE N'%cliente%'             THEN N'customer_id'
            WHEN [Motivo] LIKE N'%rt_culo%'             THEN N'article_id'
            WHEN [Motivo] LIKE N'Canal%'                THEN N'sales_channel_id'
            WHEN [Motivo] LIKE N'Precio%'               THEN N'price'
            WHEN [Motivo] LIKE N'Escenario%'            THEN N'Escenario'
            WHEN [Motivo] LIKE N'Monto%'                THEN N'Monto'
            WHEN [Motivo] LIKE N'Departamento%'         THEN N'department_name / section_name'
            WHEN [Motivo] LIKE N'%emporada%'            THEN N'TemporadaID'
            ELSE N'(ver motivo)' END AS Columna,
       [Motivo], COUNT(*) AS Filas, SUM(CAST([Lineas] AS BIGINT)) AS LineasOrigen
  FROM E GROUP BY [Archivo], [Motivo]
 ORDER BY [Archivo], COUNT(*) DESC;

PRINT '4b) Ejemplos de filas rechazadas, con el valor tal como venia en el archivo';
SELECT TOP 20 [Motivo], [t_dat_origen], [customer_id_origen], [article_id_origen], [price_origen], [canal_origen], [temporada_origen], [LineasOrigen]
  FROM [DWH_HM].[Ventas].[ErrorFactVentas] ORDER BY [Motivo];
SELECT TOP 20 [Motivo], [FilaOrigen], [escenario_origen], [monto_origen], [department_origen], [section_origen], [temporada_origen], [aniomes_origen]
  FROM [DWH_HM].[Ventas].[ErrorFactMetas] ORDER BY [Motivo];
SELECT TOP 20 [Tabla], [Motivo], [FilaOrigen], [LlaveNegocio]
  FROM [DWH_HM].[dbo].[ErrorMaestro] ORDER BY [Tabla], [Motivo];

PRINT '5) Controles de valores (el precio se carga tal como viene: no se rellena ni se corrige)';
SELECT 'Ventas con precio 0 (posible oferta, se carga tal cual: informativo)' AS Control, COUNT_BIG(*) AS Valor
  FROM [DWH_HM].[Ventas].[FactVentas] WHERE [Precio] = 0
UNION ALL SELECT 'Ventas con precio negativo (posible devolucion, se carga tal cual: informativo)',
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactVentas] WHERE [Precio] < 0)
-- las lineas identicas del origen ya se juntaron en una (LineasOrigen); si aqui sale > 0 son
-- lineas de origen DISTINTAS (otro precio en texto, otra TemporadaID) que quedaron iguales al corregirlas
UNION ALL SELECT 'Filas iguales despues de corregir (origen distinto, informativo)',
       (SELECT COUNT_BIG(*) FROM (SELECT 1 AS x FROM [DWH_HM].[Ventas].[FactVentas]
                                   GROUP BY [FechaKey],[ClienteKey],[ArticuloKey],[CanalKey],[Precio] HAVING COUNT(*) > 1) d)
UNION ALL SELECT 'DimFecha: Fin_Semana mal calculado (debe ser 0)',
       (SELECT COUNT(*) FROM [DWH_HM].[GENERICO].[DimFecha]
         -- 1900-01-07 fue domingo: resto 0 = domingo, 6 = sabado (no depende de SET DATEFIRST)
         WHERE [FechaKey] > 0 AND [Fin_Semana] <> CASE WHEN DATEDIFF(DAY,'19000107',[Fecha]) % 7 IN (0,6) THEN 1 ELSE 0 END)
UNION ALL SELECT 'Articulos sin departamento (comodin -1)',
       (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimArticulo] WHERE [DepartamentoKey] = -1 AND [ArticuloKey] <> -1)
UNION ALL SELECT 'Llaves foraneas deshabilitadas o no confiables (debe ser 0)',
       (SELECT COUNT(*) FROM [DWH_HM].sys.foreign_keys WHERE is_disabled = 1 OR is_not_trusted = 1)
UNION ALL SELECT 'Auditoria con ejecuciones fallidas (N)',
       (SELECT COUNT(*) FROM [DWH_HM].[dbo].[DIM_AUDIT] WHERE [SuccessfulProcessingInd] <> 'Y');

PRINT '6) Ultimas ejecuciones registradas en DIM_AUDIT (columnas del laboratorio + calidad de la carga)';
SELECT TOP 20 [AuditKey],[TableName],[PkgName],[ExecStartDT],[ExecStopDT],
       DATEDIFF(SECOND,[ExecStartDT],[ExecStopDT]) AS Segundos,[TableInitialRowCnt],[TableFinalRowCnt],
       [FilasInsertadas],[FilasActualizadas],[FilasDuplicadas],[FilasError],[SuccessfulProcessingInd],[MensajeError]
  FROM [DWH_HM].[dbo].[DIM_AUDIT] ORDER BY [AuditKey] DESC;

PRINT '7) Calidad de los datos que SI entraron (resumen por campo de la ultima ejecucion de cada tabla)';
WITH U AS (SELECT [Entidad], MAX([AuditKey]) AS [AuditKey] FROM [DWH_HM].[dbo].[CalidadDatos] GROUP BY [Entidad])
SELECT c.[Entidad], c.[Campo], c.[TipoProblema], c.[Descripcion], c.[Tratamiento], c.[Cantidad]
  FROM [DWH_HM].[dbo].[CalidadDatos] c JOIN U ON U.[Entidad] = c.[Entidad] AND U.[AuditKey] = c.[AuditKey]
 ORDER BY c.[Entidad], c.[TipoProblema], c.[Campo];
