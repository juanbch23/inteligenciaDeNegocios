/* =====================================================================
   Proyecto H&M - Validaciones despues de ejecutar el ETL
   (MasterExecuteStage y luego MasterExecuteDWH)
   Instancia: LAPTOP-IO596P6A\DEV
   Valores esperados segun los archivos de origen:
     articles 105,542 | customers 1,371,980 | transaction 31,788,324
     DimFecha 734     | Temporada 9         | GoalsHyM 27,738
   ===================================================================== */
SET NOCOUNT ON;

PRINT '1) Archivo -> STAGE';
SELECT 'StageArticles' AS Tabla, COUNT(*) AS Filas, 105542 AS Esperado FROM [STAGE_HM].[HM].[StageArticles]
UNION ALL SELECT 'StageCustomers',    COUNT(*), 1371980  FROM [STAGE_HM].[HM].[StageCustomers]
UNION ALL SELECT 'StageTransactions', COUNT_BIG(*), 31788324 FROM [STAGE_HM].[HM].[StageTransactions]
UNION ALL SELECT 'StageFecha',        COUNT(*), 734      FROM [STAGE_HM].[HM].[StageFecha]
UNION ALL SELECT 'StageTemporada',    COUNT(*), 9        FROM [STAGE_HM].[HM].[StageTemporada]
UNION ALL SELECT 'StageGoals',        COUNT(*), 27738    FROM [STAGE_HM].[HM].[StageGoals];

PRINT '2) STAGE -> DWH (dimensiones, sin contar el comodin -1)';
SELECT 'DimFecha' AS Tabla, COUNT(*) AS Filas, (SELECT COUNT(*) FROM [STAGE_HM].[HM].[StageFecha]) AS Esperado
  FROM [DWH_HM].[GENERICO].[DimFecha] WHERE [FechaKey] <> -1
UNION ALL SELECT 'DimTemporada', COUNT(*), (SELECT COUNT(*) FROM [STAGE_HM].[HM].[StageTemporada])
  FROM [DWH_HM].[Ventas].[DimTemporada] WHERE [TemporadaKey] <> -1
UNION ALL SELECT 'DimCanal', COUNT(*), (SELECT COUNT(DISTINCT [sales_channel_id]) FROM [STAGE_HM].[HM].[StageTransactions])
  FROM [DWH_HM].[Ventas].[DimCanal] WHERE [CanalKey] <> -1
UNION ALL SELECT 'DimDepartamento', COUNT(*), (SELECT COUNT(*) FROM (SELECT DISTINCT [department_name],[section_name] FROM [STAGE_HM].[HM].[StageArticles]) x)
  FROM [DWH_HM].[Ventas].[DimDepartamento] WHERE [DepartamentoKey] <> -1
UNION ALL SELECT 'DimArticulo', COUNT(*), (SELECT COUNT(*) FROM [STAGE_HM].[HM].[StageArticles])
  FROM [DWH_HM].[Ventas].[DimArticulo] WHERE [ArticuloKey] <> -1
UNION ALL SELECT 'DimCliente', COUNT(*), (SELECT COUNT(*) FROM [STAGE_HM].[HM].[StageCustomers])
  FROM [DWH_HM].[Ventas].[DimCliente] WHERE [ClienteKey] <> -1;

PRINT '3) Hechos: Fact + Error = Stage';
SELECT 'Ventas' AS Hecho,
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactVentas])      AS Fact,
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[ErrorFactVentas]) AS Error,
       (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTransactions]) AS Stage
UNION ALL
SELECT 'Metas',
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[FactMetas]),
       (SELECT COUNT_BIG(*) FROM [DWH_HM].[Ventas].[ErrorFactMetas]),
       (SELECT COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageGoals]);

PRINT '4) Montos: suma en DWH vs Stage (diferencia debe ser ~0)';
SELECT 'Ventas' AS Hecho,
       (SELECT SUM(CONVERT(DECIMAL(38,6),[Precio])) FROM [DWH_HM].[Ventas].[FactVentas])
     + ISNULL((SELECT SUM(CONVERT(DECIMAL(38,6),[price])) FROM [DWH_HM].[Ventas].[ErrorFactVentas]),0)
     - (SELECT SUM(CONVERT(DECIMAL(38,6),[price])) FROM [STAGE_HM].[HM].[StageTransactions]) AS Diferencia
UNION ALL
SELECT 'Metas',
       (SELECT SUM(CONVERT(DECIMAL(38,6),[Monto])) FROM [DWH_HM].[Ventas].[FactMetas])
     + ISNULL((SELECT SUM(CONVERT(DECIMAL(38,6),[Monto])) FROM [DWH_HM].[Ventas].[ErrorFactMetas]),0)
     - (SELECT SUM(CONVERT(DECIMAL(38,6),[Monto])) FROM [STAGE_HM].[HM].[StageGoals]);

PRINT '5) Calidad de datos';
SELECT 'Llaves foraneas deshabilitadas o no confiables' AS Control, COUNT(*) AS Valor
  FROM [DWH_HM].sys.foreign_keys WHERE is_disabled = 1 OR is_not_trusted = 1
UNION ALL SELECT 'Comodines -1 (esperado 6)',
       (SELECT COUNT(*) FROM [DWH_HM].[GENERICO].[DimFecha] WHERE [FechaKey] = -1)
     + (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimTemporada] WHERE [TemporadaKey] = -1)
     + (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimCanal] WHERE [CanalKey] = -1)
     + (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimDepartamento] WHERE [DepartamentoKey] = -1)
     + (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimArticulo] WHERE [ArticuloKey] = -1)
     + (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimCliente] WHERE [ClienteKey] = -1)
UNION ALL SELECT 'DimFecha: fines de semana (sab/dom)',
       (SELECT COUNT(*) FROM [DWH_HM].[GENERICO].[DimFecha] WHERE [Fin_Semana] = 1)
UNION ALL SELECT 'DimFecha: Fin_Semana mal calculado',
       (SELECT COUNT(*) FROM [DWH_HM].[GENERICO].[DimFecha]
         -- 1900-01-07 fue domingo: resto 0 = domingo, 6 = sabado (no depende de SET DATEFIRST)
         WHERE [FechaKey] > 0 AND [Fin_Semana] <> CASE WHEN DATEDIFF(DAY,'19000107',[Fecha]) % 7 IN (0,6) THEN 1 ELSE 0 END)
UNION ALL SELECT 'Articulos sin departamento',
       (SELECT COUNT(*) FROM [DWH_HM].[Ventas].[DimArticulo] WHERE [DepartamentoKey] = -1 AND [ArticuloKey] <> -1)
UNION ALL SELECT 'Auditoria con ejecuciones fallidas (N)',
       (SELECT COUNT(*) FROM [DWH_HM].[dbo].[DIM_AUDIT] WHERE [SuccessfulProcessingInd] <> 'Y');

PRINT '6) Ultimas ejecuciones registradas en DIM_AUDIT';
SELECT TOP 20 [AuditKey],[TableName],[PkgName],[ExecStartDT],[ExecStopDT],
       DATEDIFF(SECOND,[ExecStartDT],[ExecStopDT]) AS Segundos,[TableFinalRowCnt],[SuccessfulProcessingInd]
  FROM [DWH_HM].[dbo].[DIM_AUDIT] ORDER BY [AuditKey] DESC;
