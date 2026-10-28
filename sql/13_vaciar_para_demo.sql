/* =====================================================================
   Proyecto H&M - Dejar todo VACIO (como recien creado) antes de una demo
   del Job_HM "end to end". No borra tablas ni procedimientos: solo datos.

     STAGE_HM : las 6 tablas del stage
     DWH_HM   : hechos, dimensiones (menos la fila -1 "Sin Datos"),
                tablas de error y la auditoria DIM_AUDIT
     msdb     : el historial del Job_HM
   El cubo se vacia aparte (SSMS > Analysis Services > Tabular_HM >
   clic derecho > Procesar base de datos > Modo: "Procesar borrado").

   Despues: Agente SQL Server > Trabajos > Job_HM > Iniciar trabajo en el paso 1.
   ===================================================================== */
SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;   -- DimFecha tiene una columna calculada persistida (AnioMes)

/* ---------- 1. STAGE ---------- */
TRUNCATE TABLE [STAGE_HM].[HM].[StageTransactions];
TRUNCATE TABLE [STAGE_HM].[HM].[StageCustomers];
TRUNCATE TABLE [STAGE_HM].[HM].[StageArticles];
TRUNCATE TABLE [STAGE_HM].[HM].[StageGoals];
TRUNCATE TABLE [STAGE_HM].[HM].[StageFecha];
TRUNCATE TABLE [STAGE_HM].[HM].[StageTemporada];
GO

/* ---------- 2. DWH: hechos y tablas de error ---------- */
USE [DWH_HM]
GO
TRUNCATE TABLE [Ventas].[FactVentas];
TRUNCATE TABLE [Ventas].[FactMetas];
TRUNCATE TABLE [Ventas].[ErrorFactVentas];
TRUNCATE TABLE [Ventas].[ErrorFactMetas];
TRUNCATE TABLE [dbo].[ErrorMaestro];
GO

/* ---------- 3. DWH: dimensiones ----------
   Se conserva la fila -1 ("Sin Datos"), que crea 02_crear_DWH_HM.sql y no la vuelve a crear el ETL.
   DimArticulo antes que DimDepartamento (llave foranea). */
DELETE FROM [Ventas].[DimArticulo]     WHERE [ArticuloKey]     > 0;
DELETE FROM [Ventas].[DimDepartamento] WHERE [DepartamentoKey] > 0;
DELETE FROM [Ventas].[DimCliente]      WHERE [ClienteKey]      > 0;
DELETE FROM [Ventas].[DimCanal]        WHERE [CanalKey]        > 0;
DELETE FROM [Ventas].[DimTemporada]    WHERE [TemporadaKey]    > 0;
DELETE FROM [GENERICO].[DimFecha]      WHERE [FechaKey]        > 0;
-- las llaves vuelven a empezar en 1
DBCC CHECKIDENT ('Ventas.DimArticulo',     RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Ventas.DimDepartamento', RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Ventas.DimCliente',      RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Ventas.DimCanal',        RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Ventas.DimTemporada',    RESEED, 0) WITH NO_INFOMSGS;
GO

/* ---------- 4. Auditoria e historial del job ---------- */
TRUNCATE TABLE [dbo].[DIM_AUDIT];
TRUNCATE TABLE [dbo].[CalidadDatos];
EXEC msdb.dbo.sp_purge_jobhistory @job_name = N'Job_HM';
GO

/* ---------- 5. Comprobacion: todo en 0 (las dimensiones quedan con su fila -1) ---------- */
SELECT 'STAGE' AS Capa, 'StageTransactions' AS Tabla, COUNT_BIG(*) AS Filas FROM [STAGE_HM].[HM].[StageTransactions]
UNION ALL SELECT 'STAGE', 'StageCustomers',   COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageCustomers]
UNION ALL SELECT 'STAGE', 'StageArticles',    COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageArticles]
UNION ALL SELECT 'STAGE', 'StageGoals',       COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageGoals]
UNION ALL SELECT 'STAGE', 'StageFecha',       COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageFecha]
UNION ALL SELECT 'STAGE', 'StageTemporada',   COUNT_BIG(*) FROM [STAGE_HM].[HM].[StageTemporada]
UNION ALL SELECT 'DWH',   'FactVentas',       COUNT_BIG(*) FROM [Ventas].[FactVentas]
UNION ALL SELECT 'DWH',   'FactMetas',        COUNT_BIG(*) FROM [Ventas].[FactMetas]
UNION ALL SELECT 'DWH',   'DimCliente',       COUNT_BIG(*) FROM [Ventas].[DimCliente]
UNION ALL SELECT 'DWH',   'DimArticulo',      COUNT_BIG(*) FROM [Ventas].[DimArticulo]
UNION ALL SELECT 'DWH',   'DimDepartamento',  COUNT_BIG(*) FROM [Ventas].[DimDepartamento]
UNION ALL SELECT 'DWH',   'DimCanal',         COUNT_BIG(*) FROM [Ventas].[DimCanal]
UNION ALL SELECT 'DWH',   'DimTemporada',     COUNT_BIG(*) FROM [Ventas].[DimTemporada]
UNION ALL SELECT 'DWH',   'DimFecha',         COUNT_BIG(*) FROM [GENERICO].[DimFecha]
UNION ALL SELECT 'DWH',   'ErrorFactVentas',  COUNT_BIG(*) FROM [Ventas].[ErrorFactVentas]
UNION ALL SELECT 'DWH',   'ErrorFactMetas',   COUNT_BIG(*) FROM [Ventas].[ErrorFactMetas]
UNION ALL SELECT 'DWH',   'ErrorMaestro',     COUNT_BIG(*) FROM [dbo].[ErrorMaestro]
UNION ALL SELECT 'DWH',   'DIM_AUDIT',        COUNT_BIG(*) FROM [dbo].[DIM_AUDIT]
UNION ALL SELECT 'DWH',   'CalidadDatos',     COUNT_BIG(*) FROM [dbo].[CalidadDatos]
UNION ALL SELECT 'msdb',  'Historial Job_HM', COUNT_BIG(*) FROM msdb.dbo.sysjobhistory h
                                               JOIN msdb.dbo.sysjobs j ON j.job_id = h.job_id WHERE j.name = N'Job_HM';
