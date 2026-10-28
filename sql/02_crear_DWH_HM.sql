/* =====================================================================
   Proyecto H&M - Data Warehouse (modelo estrella)
   Instancia : LAPTOP-IO596P6A\DEV  (SQL Server 2025 Developer)
   Dimensiones : GENERICO.DimFecha, Ventas.DimTemporada, Ventas.DimCanal,
                 Ventas.DimDepartamento, Ventas.DimArticulo, Ventas.DimCliente
   Hechos      : Ventas.FactVentas  (transacciones, columnstore)
                 Ventas.FactMetas   (GoalsHyM.xlsx: metas por escenario)
   Errores     : Ventas.ErrorFactVentas, Ventas.ErrorFactMetas (filas de hechos descartadas)
                 dbo.ErrorMaestro (filas de maestros descartadas)
                 -> cada fila descartada queda con su MOTIVO; nada se pierde.
   Auditoria   : dbo.DIM_AUDIT
   Requiere que exista STAGE_HM (los SP de dimensiones leen de ahi).

   Estrategia de limpieza ("nunca confiar en los datos"):
     1. El STAGE es texto: todo entra, aunque venga sucio.
     2. TRY_CONVERT convierte; si el valor no sirve devuelve NULL (no error).
     3. Sin supuestos: un campo CALCULADO se recalcula desde su origen (p. ej. Fin_Semana desde la fecha);
        un dato ORIGINAL que no sirve no se rellena -> fila a la tabla de ERROR con motivo.
     4. Duplicados -> se conserva UNO (ROW_NUMBER ... = 1 / GROUP BY).
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;   -- requerido por la columna calculada persistida AnioMes
GO
USE [master]
GO
IF DB_ID(N'DWH_HM') IS NULL
    CREATE DATABASE [DWH_HM];
GO
ALTER DATABASE [DWH_HM] SET RECOVERY SIMPLE;
ALTER DATABASE [DWH_HM] MODIFY FILE (NAME = N'DWH_HM', FILEGROWTH = 256MB);
ALTER DATABASE [DWH_HM] MODIFY FILE (NAME = N'DWH_HM_log', FILEGROWTH = 256MB);
GO
USE [DWH_HM]
GO
IF SCHEMA_ID(N'GENERICO') IS NULL EXEC (N'CREATE SCHEMA [GENERICO]');
IF SCHEMA_ID(N'Ventas')   IS NULL EXEC (N'CREATE SCHEMA [Ventas]');
GO

/* hechos primero (tienen FK hacia las dimensiones) */
DROP TABLE IF EXISTS [Ventas].[FactVentas];
DROP TABLE IF EXISTS [Ventas].[ErrorFactVentas];
DROP TABLE IF EXISTS [Ventas].[FactMetas];
DROP TABLE IF EXISTS [Ventas].[ErrorFactMetas];
DROP TABLE IF EXISTS [Ventas].[DimArticulo];
DROP TABLE IF EXISTS [Ventas].[DimDepartamento];
DROP TABLE IF EXISTS [Ventas].[DimCliente];
DROP TABLE IF EXISTS [Ventas].[DimCanal];
DROP TABLE IF EXISTS [Ventas].[DimTemporada];
DROP TABLE IF EXISTS [GENERICO].[DimFecha];
DROP TABLE IF EXISTS [dbo].[ErrorMaestro];
GO

/* =========================== AUDITORIA =========================== */
IF OBJECT_ID(N'[dbo].[DIM_AUDIT]') IS NULL
CREATE TABLE [dbo].[DIM_AUDIT](
    [AuditKey]                INT IDENTITY(1,1) NOT NULL CONSTRAINT [PK_DIM_AUDIT] PRIMARY KEY,
    [TableName]               NVARCHAR(100)    NOT NULL,
    [PkgName]                 NVARCHAR(100)    NOT NULL,
    [PkgGUID]                 UNIQUEIDENTIFIER NULL,
    [ExecStartDT]             DATETIME         NOT NULL,
    [ExecStopDT]              DATETIME         NULL,
    [ExecutionInstanceGUID]   UNIQUEIDENTIFIER NULL,
    [ExtractRowCnt]           BIGINT           NULL,
    [TableInitialRowCnt]      BIGINT           NULL,
    [TableFinalRowCnt]        BIGINT           NULL,
    [SuccessfulProcessingInd] NCHAR(1)         NOT NULL DEFAULT ('N'),
    -- Ampliacion de la auditoria del laboratorio (calidad de la carga)
    [FilasInsertadas]         BIGINT           NULL,   -- filas nuevas (MERGE: INSERT; hechos y stage: filas cargadas)
    [FilasActualizadas]       BIGINT           NULL,   -- filas que ya existian y cambiaron (MERGE: UPDATE)
    [FilasDuplicadas]         BIGINT           NULL,   -- copias descartadas (lineas identicas o IDs repetidos)
    [FilasError]              BIGINT           NULL,   -- filas enviadas a la tabla de error (sin contar duplicados)
    [MensajeError]            NVARCHAR(2000)   NULL    -- si el paquete falla: el mensaje del error (controlador OnError)
);
GO
IF COL_LENGTH(N'dbo.DIM_AUDIT', N'FilasInsertadas') IS NULL
    ALTER TABLE [dbo].[DIM_AUDIT] ADD [FilasInsertadas] BIGINT NULL, [FilasActualizadas] BIGINT NULL,
        [FilasDuplicadas] BIGINT NULL, [FilasError] BIGINT NULL, [MensajeError] NVARCHAR(2000) NULL;
GO

/* filas de los maestros que no entraron a su dimension (cada SP borra y vuelve a llenar las suyas) */
CREATE TABLE [dbo].[ErrorMaestro](
    [Tabla]         NVARCHAR(30)   NOT NULL,
    [LlaveNegocio]  NVARCHAR(200)  NULL,
    [FilaOrigen]    INT            NULL,
    [Motivo]        NVARCHAR(300)  NOT NULL,
    [FechaRegistro] DATETIME       NOT NULL DEFAULT (GETDATE()),
    INDEX [IX_ErrorMaestro_Tabla] CLUSTERED ([Tabla])
);
GO

/* ========================== DIMENSIONES ========================== */
CREATE TABLE [GENERICO].[DimFecha](
    [FechaKey]          INT         NOT NULL CONSTRAINT [PK_DimFecha] PRIMARY KEY,
    [Fecha]             DATE        NOT NULL,
    [Dia_Semana]        TINYINT     NOT NULL,   -- 1 = domingo ... 7 = sabado (igual que el CSV)
    [Nombre_Dia_Semana] VARCHAR(15) NOT NULL,
    [Dia_Mes]           TINYINT     NOT NULL,
    [Dia_Anio]          SMALLINT    NOT NULL,
    [Nombre_Mes]        VARCHAR(15) NOT NULL,
    [Mes_Anio]          TINYINT     NOT NULL,
    [Semana_Anio]       TINYINT     NOT NULL,   -- semana que empieza en domingo (igual que el CSV)
    [Anio]              SMALLINT    NOT NULL,
    [Bimestre]          TINYINT     NOT NULL,
    [Trimestre]         TINYINT     NOT NULL,
    [Cuatrimestre]      TINYINT     NOT NULL,
    [Semestre]          TINYINT     NOT NULL,
    [Fin_Semana]        TINYINT     NOT NULL,   -- recalculado (en el CSV venia mal en 210 dias)
    [AnioMes]           AS (CONVERT(INT, [Anio]) * 100 + [Mes_Anio]) PERSISTED
);
GO
CREATE TABLE [Ventas].[DimTemporada](
    [TemporadaKey] INT IDENTITY(1,1) NOT NULL CONSTRAINT [PK_DimTemporada] PRIMARY KEY,
    [TemporadaID]  TINYINT      NOT NULL CONSTRAINT [UQ_DimTemporada_ID] UNIQUE,
    [Temporada]    VARCHAR(30)  NOT NULL,
    [Estacion]     VARCHAR(15)  NOT NULL,
    [Anio]         SMALLINT     NOT NULL,
    [FechaInicio]  DATE         NOT NULL,
    [FechaFin]     DATE         NOT NULL
);
GO
CREATE TABLE [Ventas].[DimCanal](
    [CanalKey]    INT IDENTITY(1,1) NOT NULL CONSTRAINT [PK_DimCanal] PRIMARY KEY,
    [CanalID]     TINYINT     NOT NULL CONSTRAINT [UQ_DimCanal_ID] UNIQUE,
    [NombreCanal] VARCHAR(30) NOT NULL
);
GO
CREATE TABLE [Ventas].[DimDepartamento](
    [DepartamentoKey] INT IDENTITY(1,1) NOT NULL CONSTRAINT [PK_DimDepartamento] PRIMARY KEY,
    [department_name] NVARCHAR(60) NOT NULL,
    [section_name]    NVARCHAR(60) NOT NULL,
    CONSTRAINT [UQ_DimDepartamento] UNIQUE ([department_name], [section_name])
);
GO
CREATE TABLE [Ventas].[DimArticulo](
    [ArticuloKey]                  INT IDENTITY(1,1) NOT NULL CONSTRAINT [PK_DimArticulo] PRIMARY KEY,
    [ArticleID]                    INT            NOT NULL CONSTRAINT [UQ_DimArticulo_ID] UNIQUE,
    [ProductCode]                  INT            NOT NULL,
    [ProdName]                     NVARCHAR(100)  NOT NULL,
    [ProductTypeName]              NVARCHAR(50)   NOT NULL,
    [ProductGroupName]             NVARCHAR(50)   NOT NULL,
    [GraphicalAppearanceName]      NVARCHAR(50)   NOT NULL,
    [ColourGroupName]              NVARCHAR(50)   NOT NULL,
    [PerceivedColourValueName]     NVARCHAR(50)   NOT NULL,
    [PerceivedColourMasterName]    NVARCHAR(50)   NOT NULL,
    [DepartmentName]               NVARCHAR(60)   NOT NULL,
    [IndexName]                    NVARCHAR(50)   NOT NULL,
    [IndexGroupName]               NVARCHAR(50)   NOT NULL,
    [SectionName]                  NVARCHAR(60)   NOT NULL,
    [GarmentGroupName]             NVARCHAR(50)   NOT NULL,
    [DetailDesc]                   NVARCHAR(1000) NULL,
    [DepartamentoKey]              INT            NOT NULL
        CONSTRAINT [FK_DimArticulo_DimDepartamento] REFERENCES [Ventas].[DimDepartamento]([DepartamentoKey])
);
GO
CREATE TABLE [Ventas].[DimCliente](
    [ClienteKey]           INT IDENTITY(1,1) NOT NULL CONSTRAINT [PK_DimCliente] PRIMARY KEY,
    [CustomerID]           VARCHAR(64) NOT NULL CONSTRAINT [UQ_DimCliente_ID] UNIQUE,
    [FN]                   BIT         NOT NULL,
    [Active]               BIT         NOT NULL,
    [ClubMemberStatus]     VARCHAR(20) NOT NULL,
    [FashionNewsFrequency] VARCHAR(20) NOT NULL,
    [Edad]                 SMALLINT    NULL,
    [RangoEdad]            VARCHAR(10) NOT NULL,
    [PostalCode]           VARCHAR(64) NOT NULL
);
GO

/* ------------------- comodines -1 (proceso_bi parte 2) ------------------- */
INSERT INTO [GENERICO].[DimFecha]
    ([FechaKey],[Fecha],[Dia_Semana],[Nombre_Dia_Semana],[Dia_Mes],[Dia_Anio],[Nombre_Mes],[Mes_Anio],
     [Semana_Anio],[Anio],[Bimestre],[Trimestre],[Cuatrimestre],[Semestre],[Fin_Semana])
VALUES (-1,'1900-01-01',0,'Sin Fecha',0,0,'Sin Fecha',0,0,0,0,0,0,0,0);

SET IDENTITY_INSERT [Ventas].[DimTemporada] ON;
INSERT INTO [Ventas].[DimTemporada] ([TemporadaKey],[TemporadaID],[Temporada],[Estacion],[Anio],[FechaInicio],[FechaFin])
VALUES (-1, 0, 'Sin Datos', 'Sin Datos', 0, '1900-01-01', '1900-01-01');
SET IDENTITY_INSERT [Ventas].[DimTemporada] OFF;

SET IDENTITY_INSERT [Ventas].[DimCanal] ON;
INSERT INTO [Ventas].[DimCanal] ([CanalKey],[CanalID],[NombreCanal]) VALUES (-1, 0, 'Sin Datos');
SET IDENTITY_INSERT [Ventas].[DimCanal] OFF;

SET IDENTITY_INSERT [Ventas].[DimDepartamento] ON;
INSERT INTO [Ventas].[DimDepartamento] ([DepartamentoKey],[department_name],[section_name]) VALUES (-1, N'Sin Datos', N'Sin Datos');
SET IDENTITY_INSERT [Ventas].[DimDepartamento] OFF;

SET IDENTITY_INSERT [Ventas].[DimArticulo] ON;
INSERT INTO [Ventas].[DimArticulo]
    ([ArticuloKey],[ArticleID],[ProductCode],[ProdName],[ProductTypeName],[ProductGroupName],[GraphicalAppearanceName],
     [ColourGroupName],[PerceivedColourValueName],[PerceivedColourMasterName],[DepartmentName],[IndexName],
     [IndexGroupName],[SectionName],[GarmentGroupName],[DetailDesc],[DepartamentoKey])
VALUES (-1,-1,-1,N'Sin Datos',N'Sin Datos',N'Sin Datos',N'Sin Datos',N'Sin Datos',N'Sin Datos',N'Sin Datos',
        N'Sin Datos',N'Sin Datos',N'Sin Datos',N'Sin Datos',N'Sin Datos',NULL,-1);
SET IDENTITY_INSERT [Ventas].[DimArticulo] OFF;

SET IDENTITY_INSERT [Ventas].[DimCliente] ON;
INSERT INTO [Ventas].[DimCliente]
    ([ClienteKey],[CustomerID],[FN],[Active],[ClubMemberStatus],[FashionNewsFrequency],[Edad],[RangoEdad],[PostalCode])
VALUES (-1,'-1',0,0,'SIN DATO','SIN DATO',NULL,'Sin dato','-1');
SET IDENTITY_INSERT [Ventas].[DimCliente] OFF;
GO

/* ============================= HECHOS ============================= */
CREATE TABLE [Ventas].[FactVentas](
    [FechaKey]        INT            NOT NULL CONSTRAINT [FK_FactVentas_DimFecha]        REFERENCES [GENERICO].[DimFecha]([FechaKey]),
    [ClienteKey]      INT            NOT NULL CONSTRAINT [FK_FactVentas_DimCliente]      REFERENCES [Ventas].[DimCliente]([ClienteKey]),
    [ArticuloKey]     INT            NOT NULL CONSTRAINT [FK_FactVentas_DimArticulo]     REFERENCES [Ventas].[DimArticulo]([ArticuloKey]),
    [DepartamentoKey] INT            NOT NULL CONSTRAINT [FK_FactVentas_DimDepartamento] REFERENCES [Ventas].[DimDepartamento]([DepartamentoKey]),
    [CanalKey]        INT            NOT NULL CONSTRAINT [FK_FactVentas_DimCanal]        REFERENCES [Ventas].[DimCanal]([CanalKey]),
    [TemporadaKey]    INT            NOT NULL CONSTRAINT [FK_FactVentas_DimTemporada]    REFERENCES [Ventas].[DimTemporada]([TemporadaKey]),
    [Precio]          DECIMAL(19,4)  NOT NULL,   -- price x 40000 con 4 decimales (indicacion del profesor; sin precios supuestos)
    [LineasOrigen]    INT            NOT NULL,   -- veces que la linea venia identica en el archivo (se conserva 1)
    INDEX [CCI_FactVentas] CLUSTERED COLUMNSTORE      -- ~29 M filas comprimidas
);
GO
CREATE TABLE [Ventas].[ErrorFactVentas](
    [t_dat_origen]       VARCHAR(100)  NULL,   -- valores tal como venian en el archivo
    [customer_id_origen] VARCHAR(100)  NULL,
    [article_id_origen]  VARCHAR(100)  NULL,
    [price_origen]       VARCHAR(100)  NULL,
    [canal_origen]       VARCHAR(100)  NULL,
    [temporada_origen]   VARCHAR(100)  NULL,
    [FechaKey]           INT           NULL,
    [ClienteKey]         INT           NULL,
    [ArticuloKey]        INT           NULL,
    [DepartamentoKey]    INT           NULL,
    [CanalKey]           INT           NULL,
    [TemporadaKey]       INT           NULL,
    [LineasOrigen]       INT           NULL,
    [Motivo]             NVARCHAR(200) NULL,
    [FechaRegistro]      DATETIME      NOT NULL DEFAULT (GETDATE())
);
GO
CREATE TABLE [Ventas].[FactMetas](
    [Escenario]       NVARCHAR(30)  NOT NULL,
    [FechaKey]        INT           NOT NULL CONSTRAINT [FK_FactMetas_DimFecha]        REFERENCES [GENERICO].[DimFecha]([FechaKey]),
    [AnioMes]         INT           NOT NULL,
    [DepartamentoKey] INT           NOT NULL CONSTRAINT [FK_FactMetas_DimDepartamento] REFERENCES [Ventas].[DimDepartamento]([DepartamentoKey]),
    [TemporadaKey]    INT           NOT NULL CONSTRAINT [FK_FactMetas_DimTemporada]    REFERENCES [Ventas].[DimTemporada]([TemporadaKey]),
    [Monto]           DECIMAL(19,4) NOT NULL,   -- Monto tal como viene en GoalsHyM (sin x 40000)
    CONSTRAINT [PK_FactMetas] PRIMARY KEY ([Escenario],[DepartamentoKey],[TemporadaKey],[AnioMes])
);
GO
CREATE TABLE [Ventas].[ErrorFactMetas](
    [FilaOrigen]         INT           NULL,
    [escenario_origen]   NVARCHAR(255) NULL,
    [monto_origen]       FLOAT         NULL,
    [department_origen]  NVARCHAR(255) NULL,
    [section_origen]     NVARCHAR(255) NULL,
    [temporada_origen]   FLOAT         NULL,
    [aniomes_origen]     FLOAT         NULL,
    [FechaKey]           INT           NULL,
    [DepartamentoKey]    INT           NULL,
    [TemporadaKey]       INT           NULL,
    [Motivo]             NVARCHAR(200) NULL,
    [FechaRegistro]      DATETIME      NOT NULL DEFAULT (GETDATE())
);
GO

/* Lectura de fechas (regla del proyecto):
     yyyymmdd / yyyy-mm-dd             -> formato de los archivos del caso
     con "/" (dd/mm/yyyy)              -> REGLA: dia/mes/anio, como se escribe en el Peru (01/02/2019 = 1 de febrero)
     con "/" y el 2do numero > 12      -> solo puede ser mes/dia (07/25/2019 = 25 de julio)
     fecha imposible (30/02/2019, abc) -> NULL -> tabla de error con el valor original */
CREATE OR ALTER FUNCTION [dbo].[fn_LeerFecha](@x NVARCHAR(50))
RETURNS DATE
AS
BEGIN
    DECLARE @t NVARCHAR(50) = LTRIM(RTRIM(@x));
    DECLARE @d DATE = COALESCE(TRY_CONVERT(DATE, @t, 112), TRY_CONVERT(DATE, @t, 23));
    IF @d IS NOT NULL OR @t NOT LIKE N'%/%/%' RETURN @d;
    DECLARE @p NVARCHAR(50) = REPLACE(@t, N'/', N'.');
    DECLARE @a INT = TRY_CONVERT(INT, PARSENAME(@p, 3)), @b INT = TRY_CONVERT(INT, PARSENAME(@p, 2)),
            @y INT = TRY_CONVERT(INT, PARSENAME(@p, 1));
    IF @a IS NULL OR @b IS NULL OR @y IS NULL OR @y < 1900 RETURN NULL;
    IF @b > 12 AND @a <= 12                 -- solo puede ser mes/dia
        RETURN TRY_CONVERT(DATE, CONCAT(@y, N'-', RIGHT(CONCAT(N'0', @a), 2), N'-', RIGHT(CONCAT(N'0', @b), 2)), 23);
    -- regla: dia/mes/anio
    RETURN TRY_CONVERT(DATE, CONCAT(@y, N'-', RIGHT(CONCAT(N'0', @b), 2), N'-', RIGHT(CONCAT(N'0', @a), 2)), 23);
END
GO

/* ================= PROCEDIMIENTOS DE CARGA DE DIMENSIONES =================
   Patron de todos los SP:
     #S  = filas del STAGE ya convertidas con TRY_CONVERT y limpiadas,
           con Motivo (por que no sirve) y rn (ROW_NUMBER por ID: 1 = primera aparicion).
     -> filas con Motivo  : a dbo.ErrorMaestro
     -> filas sin Motivo  : MERGE (SCD tipo 1) en la dimension; nunca borra,
                            asi los comodines -1 se conservan.
   Los ejecutan los paquetes SSIS del proyecto DWH_H&M.                     */

-- texto limpio: sin espacios a los lados; vacio / Unknown / undefined -> 'Sin Datos'; recortado al largo de la columna
CREATE OR ALTER FUNCTION [dbo].[fn_Texto](@x NVARCHAR(4000), @largo INT)
RETURNS NVARCHAR(4000)
AS
BEGIN
    DECLARE @t NVARCHAR(4000) = LTRIM(RTRIM(@x));
    RETURN LEFT(CASE WHEN @t IS NULL OR @t IN (N'', N'Unknown', N'undefined') THEN N'Sin Datos' ELSE @t END, @largo);
END
GO

CREATE OR ALTER PROCEDURE [GENERICO].[sp_DimFecha]
    @AuditKey INT = NULL   -- fila de DIM_AUDIT de esta ejecucion: se registran insertadas / actualizadas
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Acciones TABLE ([Accion] NVARCHAR(10));
    -- La fecha es el dato confiable: todos los demas atributos se recalculan a partir de ella
    -- (el CSV traia Fin_Semana errado). Si [Fecha] no sirve se intenta con [FechaKey] (yyyymmdd).
    -- Lectura de la fecha con la regla del proyecto (dbo.fn_LeerFecha).
    SELECT [FilaOrigen], [FechaKey] AS [FechaKeyOrigen], [Fecha] AS [FechaOrigen],
           COALESCE([dbo].[fn_LeerFecha]([Fecha]), TRY_CONVERT(DATE, LTRIM(RTRIM([FechaKey])), 112)) AS [F]
      INTO #S
      FROM [STAGE_HM].[HM].[StageFecha];

    SELECT *, ROW_NUMBER() OVER (PARTITION BY [F] ORDER BY [FilaOrigen]) AS [rn] INTO #R FROM #S;

    DELETE FROM [dbo].[ErrorMaestro] WHERE [Tabla] = N'DimFecha';
    INSERT INTO [dbo].[ErrorMaestro] ([Tabla],[LlaveNegocio],[FilaOrigen],[Motivo])
    SELECT N'DimFecha', LEFT([FechaKeyOrigen], 200), [FilaOrigen],
           CASE WHEN [F] IS NULL THEN N'Fecha inválida: ' + ISNULL(LEFT([FechaOrigen], 50), N'(vacía)')
                ELSE N'Fecha repetida (se conservó la primera aparición)' END
      FROM #R WHERE [F] IS NULL OR [rn] > 1;

    INSERT INTO [GENERICO].[DimFecha]
        ([FechaKey],[Fecha],[Dia_Semana],[Nombre_Dia_Semana],[Dia_Mes],[Dia_Anio],[Nombre_Mes],[Mes_Anio],
         [Semana_Anio],[Anio],[Bimestre],[Trimestre],[Cuatrimestre],[Semestre],[Fin_Semana])
    SELECT CONVERT(INT, CONVERT(CHAR(8), r.[F], 112)), r.[F], d.[dw],
           CHOOSE(d.[dw], 'Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'),
           DAY(r.[F]), DATEPART(DAYOFYEAR, r.[F]),
           CHOOSE(MONTH(r.[F]), 'January','February','March','April','May','June','July','August',
                                'September','October','November','December'),
           MONTH(r.[F]),
           (DATEPART(DAYOFYEAR, r.[F]) - 1 + d.[dwEnero1]) / 7 + 1,
           YEAR(r.[F]), (MONTH(r.[F]) + 1) / 2, (MONTH(r.[F]) + 2) / 3, (MONTH(r.[F]) + 3) / 4, (MONTH(r.[F]) + 5) / 6,
           CASE WHEN d.[dw] IN (1, 7) THEN 1 ELSE 0 END
      FROM #R r
      -- 1900-01-07 fue domingo: asi el dia de la semana no depende de SET DATEFIRST ni del idioma
     CROSS APPLY (SELECT DATEDIFF(DAY, '19000107', r.[F]) % 7 + 1 AS [dw],
                         DATEDIFF(DAY, '19000107', DATEFROMPARTS(YEAR(r.[F]), 1, 1)) % 7 AS [dwEnero1]) d
     WHERE r.[F] IS NOT NULL AND r.[rn] = 1
       AND NOT EXISTS (SELECT 1 FROM [GENERICO].[DimFecha] x WHERE x.[FechaKey] = CONVERT(INT, CONVERT(CHAR(8), r.[F], 112)));
    DECLARE @Nuevas BIGINT = @@ROWCOUNT;
    IF @AuditKey IS NOT NULL
        UPDATE [dbo].[DIM_AUDIT] SET [FilasInsertadas] = @Nuevas, [FilasActualizadas] = 0 WHERE [AuditKey] = @AuditKey;
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimTemporada]
    @AuditKey INT = NULL   -- fila de DIM_AUDIT de esta ejecucion: se registran insertadas / actualizadas
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Acciones TABLE ([Accion] NVARCHAR(10));
    SELECT s.[FilaOrigen], s.[TemporadaID] AS [IdOrigen], v.[Id], v.[Nombre], v.[FI], v.[FF],
           ROW_NUMBER() OVER (PARTITION BY v.[Id] ORDER BY s.[FilaOrigen]) AS [rn],
           CAST(NULL AS NVARCHAR(300)) AS [Motivo]
      INTO #S
      FROM [STAGE_HM].[HM].[StageTemporada] s
     CROSS APPLY (SELECT TRY_CONVERT(TINYINT, LTRIM(RTRIM(s.[TemporadaID]))) AS [Id],
                         LEFT(NULLIF(LTRIM(RTRIM(s.[Temporada])), ''), 30) AS [Nombre],
                         [dbo].[fn_LeerFecha](s.[FechaInicio]) AS [FI],   -- regla de fechas (dbo.fn_LeerFecha)
                         [dbo].[fn_LeerFecha](s.[FechaFin])    AS [FF]) v;

    UPDATE #S SET [Motivo] =
        CASE WHEN [Id] IS NULL OR [Id] = 0 THEN N'ID de temporada inválido: ' + ISNULL(LEFT([IdOrigen], 50), N'(vacío)')
             WHEN [Nombre] IS NULL         THEN N'Nombre de temporada vacío'
             WHEN [FI] IS NULL OR [FF] IS NULL THEN N'Fecha de inicio o de fin inválida'
             WHEN [FI] > [FF]              THEN N'Fecha de inicio posterior a la fecha de fin'
             WHEN [rn] > 1                 THEN N'Temporada repetida (se conservó la primera aparición)' END;

    DELETE FROM [dbo].[ErrorMaestro] WHERE [Tabla] = N'DimTemporada';
    INSERT INTO [dbo].[ErrorMaestro] ([Tabla],[LlaveNegocio],[FilaOrigen],[Motivo])
    SELECT N'DimTemporada', LEFT([IdOrigen], 200), [FilaOrigen], [Motivo] FROM #S WHERE [Motivo] IS NOT NULL;

    MERGE [Ventas].[DimTemporada] AS T
    USING (SELECT [Id] AS [TemporadaID], [Nombre] AS [Temporada],
                  -- "invierno-2018" -> estacion "invierno", anio 2018
                  LEFT(CASE WHEN CHARINDEX('-', [Nombre]) > 1 THEN LEFT([Nombre], CHARINDEX('-', [Nombre]) - 1) ELSE [Nombre] END, 15) AS [Estacion],
                  ISNULL(TRY_CONVERT(SMALLINT, RIGHT([Nombre], 4)), YEAR([FF])) AS [Anio],
                  [FI] AS [FechaInicio], [FF] AS [FechaFin]
             FROM #S WHERE [Motivo] IS NULL) AS S
       ON T.[TemporadaID] = S.[TemporadaID]
    WHEN MATCHED AND (T.[Temporada] <> S.[Temporada] OR T.[FechaInicio] <> S.[FechaInicio] OR T.[FechaFin] <> S.[FechaFin]) THEN
        UPDATE SET T.[Temporada] = S.[Temporada], T.[Estacion] = S.[Estacion], T.[Anio] = S.[Anio],
                   T.[FechaInicio] = S.[FechaInicio], T.[FechaFin] = S.[FechaFin]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([TemporadaID],[Temporada],[Estacion],[Anio],[FechaInicio],[FechaFin])
        VALUES (S.[TemporadaID],S.[Temporada],S.[Estacion],S.[Anio],S.[FechaInicio],S.[FechaFin])
    OUTPUT $action INTO @Acciones;
    IF @AuditKey IS NOT NULL
        UPDATE [dbo].[DIM_AUDIT]
           SET [FilasInsertadas]   = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'INSERT'),
               [FilasActualizadas] = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'UPDATE')
         WHERE [AuditKey] = @AuditKey;
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimCanal]
    @AuditKey INT = NULL   -- fila de DIM_AUDIT de esta ejecucion: se registran insertadas / actualizadas
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Acciones TABLE ([Accion] NVARCHAR(10));
    -- Catalogo fijo del caso: 1 = tienda fisica, 2 = online. Un canal distinto en las
    -- transacciones no crea un canal nuevo: esa linea va a ErrorFactVentas ("Canal inexistente").
    MERGE [Ventas].[DimCanal] AS T
    USING (VALUES (CONVERT(TINYINT, 1), CONVERT(VARCHAR(30), 'Tienda fisica')),
                  (CONVERT(TINYINT, 2), CONVERT(VARCHAR(30), 'Online'))) AS S ([CanalID], [NombreCanal])
       ON T.[CanalID] = S.[CanalID]
    WHEN MATCHED AND T.[NombreCanal] <> S.[NombreCanal] THEN
        UPDATE SET T.[NombreCanal] = S.[NombreCanal]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([CanalID],[NombreCanal]) VALUES (S.[CanalID],S.[NombreCanal])
    OUTPUT $action INTO @Acciones;
    IF @AuditKey IS NOT NULL
        UPDATE [dbo].[DIM_AUDIT]
           SET [FilasInsertadas]   = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'INSERT'),
               [FilasActualizadas] = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'UPDATE')
         WHERE [AuditKey] = @AuditKey;
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimDepartamento]
    @AuditKey INT = NULL   -- fila de DIM_AUDIT de esta ejecucion: se registran insertadas / actualizadas
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Acciones TABLE ([Accion] NVARCHAR(10));
    -- un articulo sin departamento o seccion queda en el comodin -1 (ver sp_DimArticulo)
    MERGE [Ventas].[DimDepartamento] AS T
    USING (SELECT DISTINCT [dbo].[fn_Texto]([department_name], 60) AS [department_name],
                           [dbo].[fn_Texto]([section_name], 60)    AS [section_name]
             FROM [STAGE_HM].[HM].[StageArticles]
            WHERE NULLIF(LTRIM(RTRIM([department_name])), N'') IS NOT NULL
              AND NULLIF(LTRIM(RTRIM([section_name])), N'') IS NOT NULL) AS S
       ON T.[department_name] = S.[department_name] AND T.[section_name] = S.[section_name]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([department_name],[section_name]) VALUES (S.[department_name],S.[section_name])
    OUTPUT $action INTO @Acciones;
    IF @AuditKey IS NOT NULL
        UPDATE [dbo].[DIM_AUDIT]
           SET [FilasInsertadas]   = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'INSERT'),
               [FilasActualizadas] = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'UPDATE')
         WHERE [AuditKey] = @AuditKey;
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimArticulo]
    @AuditKey INT = NULL   -- fila de DIM_AUDIT de esta ejecucion: se registran insertadas / actualizadas
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Acciones TABLE ([Accion] NVARCHAR(10));
    -- article_id viene con cero a la izquierda ("0108775015"); TRY_CONVERT(INT) lo deja igual que en transacciones
    SELECT a.[FilaOrigen], a.[article_id] AS [IdOrigen],
           TRY_CONVERT(INT, LTRIM(RTRIM(a.[article_id])))                AS [Id],
           ISNULL(TRY_CONVERT(INT, LTRIM(RTRIM(a.[product_code]))), -1)  AS [ProductCode],
           [dbo].[fn_Texto](a.[prod_name], 100)                          AS [ProdName],
           [dbo].[fn_Texto](a.[product_type_name], 50)                   AS [ProductTypeName],
           [dbo].[fn_Texto](a.[product_group_name], 50)                  AS [ProductGroupName],
           [dbo].[fn_Texto](a.[graphical_appearance_name], 50)           AS [GraphicalAppearanceName],
           [dbo].[fn_Texto](a.[colour_group_name], 50)                   AS [ColourGroupName],
           [dbo].[fn_Texto](a.[perceived_colour_value_name], 50)         AS [PerceivedColourValueName],
           [dbo].[fn_Texto](a.[perceived_colour_master_name], 50)        AS [PerceivedColourMasterName],
           [dbo].[fn_Texto](a.[department_name], 60)                     AS [DepartmentName],
           [dbo].[fn_Texto](a.[index_name], 50)                          AS [IndexName],
           [dbo].[fn_Texto](a.[index_group_name], 50)                    AS [IndexGroupName],
           [dbo].[fn_Texto](a.[section_name], 60)                        AS [SectionName],
           [dbo].[fn_Texto](a.[garment_group_name], 50)                  AS [GarmentGroupName],
           LEFT(NULLIF(LTRIM(RTRIM(a.[detail_desc])), N''), 1000)        AS [DetailDesc],
           CAST(NULL AS NVARCHAR(300))                                    AS [Motivo]
      INTO #S
      FROM [STAGE_HM].[HM].[StageArticles] a;

    WITH R AS (SELECT [Id], [IdOrigen], [Motivo], ROW_NUMBER() OVER (PARTITION BY [Id] ORDER BY [FilaOrigen]) AS [rn] FROM #S)
    UPDATE R SET [Motivo] =
        CASE WHEN [Id] IS NULL OR [Id] <= 0 THEN N'Código de artículo inválido: ' + ISNULL(LEFT([IdOrigen], 50), N'(vacío)')
             WHEN [rn] > 1 THEN N'Artículo repetido (se conservó la primera aparición)' END;

    DELETE FROM [dbo].[ErrorMaestro] WHERE [Tabla] = N'DimArticulo';
    INSERT INTO [dbo].[ErrorMaestro] ([Tabla],[LlaveNegocio],[FilaOrigen],[Motivo])
    SELECT N'DimArticulo', LEFT([IdOrigen], 200), [FilaOrigen], [Motivo] FROM #S WHERE [Motivo] IS NOT NULL;

    MERGE [Ventas].[DimArticulo] AS T
    USING (SELECT s.*, ISNULL(d.[DepartamentoKey], -1) AS [DepartamentoKey]
             FROM #S s
             LEFT JOIN [Ventas].[DimDepartamento] d
               ON d.[department_name] = s.[DepartmentName] AND d.[section_name] = s.[SectionName]
            WHERE s.[Motivo] IS NULL) AS S
       ON T.[ArticleID] = S.[Id]
    WHEN MATCHED AND (T.[ProdName] <> S.[ProdName] OR T.[DepartamentoKey] <> S.[DepartamentoKey] OR T.[ProductCode] <> S.[ProductCode]
                      OR T.[ColourGroupName] <> S.[ColourGroupName] OR T.[ProductTypeName] <> S.[ProductTypeName]
                      OR T.[IndexGroupName] <> S.[IndexGroupName] OR T.[GarmentGroupName] <> S.[GarmentGroupName]) THEN
        UPDATE SET T.[ProductCode] = S.[ProductCode], T.[ProdName] = S.[ProdName],
                   T.[ProductTypeName] = S.[ProductTypeName], T.[ProductGroupName] = S.[ProductGroupName],
                   T.[GraphicalAppearanceName] = S.[GraphicalAppearanceName], T.[ColourGroupName] = S.[ColourGroupName],
                   T.[PerceivedColourValueName] = S.[PerceivedColourValueName],
                   T.[PerceivedColourMasterName] = S.[PerceivedColourMasterName],
                   T.[DepartmentName] = S.[DepartmentName], T.[IndexName] = S.[IndexName],
                   T.[IndexGroupName] = S.[IndexGroupName], T.[SectionName] = S.[SectionName],
                   T.[GarmentGroupName] = S.[GarmentGroupName], T.[DetailDesc] = S.[DetailDesc],
                   T.[DepartamentoKey] = S.[DepartamentoKey]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([ArticleID],[ProductCode],[ProdName],[ProductTypeName],[ProductGroupName],[GraphicalAppearanceName],
                [ColourGroupName],[PerceivedColourValueName],[PerceivedColourMasterName],[DepartmentName],[IndexName],
                [IndexGroupName],[SectionName],[GarmentGroupName],[DetailDesc],[DepartamentoKey])
        VALUES (S.[Id],S.[ProductCode],S.[ProdName],S.[ProductTypeName],S.[ProductGroupName],
                S.[GraphicalAppearanceName],S.[ColourGroupName],S.[PerceivedColourValueName],
                S.[PerceivedColourMasterName],S.[DepartmentName],S.[IndexName],S.[IndexGroupName],
                S.[SectionName],S.[GarmentGroupName],S.[DetailDesc],S.[DepartamentoKey])
    OUTPUT $action INTO @Acciones;
    IF @AuditKey IS NOT NULL
        UPDATE [dbo].[DIM_AUDIT]
           SET [FilasInsertadas]   = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'INSERT'),
               [FilasActualizadas] = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'UPDATE')
         WHERE [AuditKey] = @AuditKey;
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimCliente]
    @AuditKey INT = NULL   -- fila de DIM_AUDIT de esta ejecucion: se registran insertadas / actualizadas
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Acciones TABLE ([Accion] NVARCHAR(10));
    SELECT c.[FilaOrigen], c.[customer_id] AS [IdOrigen], v.[Id],
           -- FN / Active vienen como '1.0' o vacio: 1 si el numero es 1, si no 0
           CONVERT(BIT, CASE WHEN TRY_CONVERT(FLOAT, LTRIM(RTRIM(c.[FN]))) = 1 THEN 1 ELSE 0 END)     AS [FN],
           CONVERT(BIT, CASE WHEN TRY_CONVERT(FLOAT, LTRIM(RTRIM(c.[Active]))) = 1 THEN 1 ELSE 0 END) AS [Active],
           LEFT(ISNULL(NULLIF(UPPER(LTRIM(RTRIM(c.[club_member_status]))), ''), 'SIN DATO'), 20)      AS [ClubMemberStatus],
           -- "None" y "NONE" son el mismo valor
           LEFT(ISNULL(NULLIF(UPPER(LTRIM(RTRIM(c.[fashion_news_frequency]))), ''), 'SIN DATO'), 20)  AS [FashionNewsFrequency],
           -- edad fuera de 16..100 o no numerica -> sin dato
           CASE WHEN v.[Edad] BETWEEN 16 AND 100 THEN CONVERT(SMALLINT, v.[Edad]) END                 AS [Edad],
           LEFT(ISNULL(NULLIF(LTRIM(RTRIM(c.[postal_code])), ''), '-1'), 64)                          AS [PostalCode],
           CAST(NULL AS NVARCHAR(300))                                                                AS [Motivo]
      INTO #S
      FROM [STAGE_HM].[HM].[StageCustomers] c
     CROSS APPLY (SELECT NULLIF(LTRIM(RTRIM(c.[customer_id])), '') AS [Id],
                         TRY_CONVERT(INT, TRY_CONVERT(DECIMAL(9,2), LTRIM(RTRIM(c.[age])))) AS [Edad]) v;

    WITH R AS (SELECT [Id], [Motivo], ROW_NUMBER() OVER (PARTITION BY [Id] ORDER BY [FilaOrigen]) AS [rn] FROM #S)
    UPDATE R SET [Motivo] =
        CASE WHEN [Id] IS NULL     THEN N'ID de cliente vacío'
             WHEN LEN([Id]) > 64   THEN N'ID de cliente con formato inválido (más de 64 caracteres)'
             WHEN [rn] > 1         THEN N'Cliente repetido (se conservó la primera aparición)' END;

    DELETE FROM [dbo].[ErrorMaestro] WHERE [Tabla] = N'DimCliente';
    INSERT INTO [dbo].[ErrorMaestro] ([Tabla],[LlaveNegocio],[FilaOrigen],[Motivo])
    SELECT N'DimCliente', LEFT([IdOrigen], 200), [FilaOrigen], [Motivo] FROM #S WHERE [Motivo] IS NOT NULL;

    MERGE [Ventas].[DimCliente] AS T
    USING (SELECT CONVERT(VARCHAR(64), [Id]) AS [customer_id], [FN], [Active], [ClubMemberStatus], [FashionNewsFrequency], [Edad],
                  CASE WHEN [Edad] IS NULL THEN 'Sin dato'
                       WHEN [Edad] < 25 THEN '16-24'
                       WHEN [Edad] < 35 THEN '25-34'
                       WHEN [Edad] < 45 THEN '35-44'
                       WHEN [Edad] < 55 THEN '45-54'
                       WHEN [Edad] < 65 THEN '55-64'
                       ELSE '65+' END AS [RangoEdad],
                  [PostalCode]
             FROM #S WHERE [Motivo] IS NULL) AS S
       ON T.[CustomerID] = S.[customer_id]
    WHEN MATCHED AND (T.[FN] <> S.[FN] OR T.[Active] <> S.[Active] OR T.[ClubMemberStatus] <> S.[ClubMemberStatus]
                      OR T.[FashionNewsFrequency] <> S.[FashionNewsFrequency]
                      OR ISNULL(T.[Edad], -1) <> ISNULL(S.[Edad], -1) OR T.[PostalCode] <> S.[PostalCode]) THEN
        UPDATE SET T.[FN] = S.[FN], T.[Active] = S.[Active], T.[ClubMemberStatus] = S.[ClubMemberStatus],
                   T.[FashionNewsFrequency] = S.[FashionNewsFrequency], T.[Edad] = S.[Edad],
                   T.[RangoEdad] = S.[RangoEdad], T.[PostalCode] = S.[PostalCode]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([CustomerID],[FN],[Active],[ClubMemberStatus],[FashionNewsFrequency],[Edad],[RangoEdad],[PostalCode])
        VALUES (S.[customer_id],S.[FN],S.[Active],S.[ClubMemberStatus],S.[FashionNewsFrequency],S.[Edad],S.[RangoEdad],S.[PostalCode])
    OUTPUT $action INTO @Acciones;
    IF @AuditKey IS NOT NULL
        UPDATE [dbo].[DIM_AUDIT]
           SET [FilasInsertadas]   = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'INSERT'),
               [FilasActualizadas] = (SELECT COUNT_BIG(*) FROM @Acciones WHERE [Accion] = N'UPDATE')
         WHERE [AuditKey] = @AuditKey;
END
GO

/* Registro de calidad de datos de cada carga (complementa las tablas de error):
   las tablas de error guardan las filas que NO entraron; CalidadDatos resume por campo los datos que SI
   entraron pero venian con un problema (ausente, inconsistente, en otro formato) y que se hizo con ellos.
   Una fila por problema encontrado (Cantidad > 0), unida a DIM_AUDIT por AuditKey. */
IF OBJECT_ID(N'[dbo].[CalidadDatos]') IS NULL
CREATE TABLE [dbo].[CalidadDatos](
    [AuditKey]      INT            NOT NULL,   -- ejecucion del paquete (DIM_AUDIT)
    [Entidad]       NVARCHAR(60)   NOT NULL,   -- tabla del DWH
    [Campo]         NVARCHAR(60)   NOT NULL,   -- columna del archivo
    [TipoProblema]  NVARCHAR(40)   NOT NULL,   -- DATO_AUSENTE, INCONSISTENCIA, FORMATO, VALOR_ATIPICO
    [Descripcion]   NVARCHAR(300)  NOT NULL,
    [Tratamiento]   NVARCHAR(200)  NOT NULL,   -- que hizo el ETL
    [Cantidad]      BIGINT         NOT NULL,
    [FechaRegistro] DATETIME       NOT NULL DEFAULT (GETDATE()),
    INDEX [IX_CalidadDatos_AuditKey] CLUSTERED ([AuditKey])
);
GO

/* Calcula los problemas de calidad del archivo de una tabla (lee el STAGE de esa carga) y los registra.
   Lo llama dbo.sp_CerrarAuditoria al final de cada paquete. */
CREATE OR ALTER PROCEDURE [dbo].[sp_RegistrarCalidad]
    @AuditKey INT,
    @Tabla    NVARCHAR(60)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @R TABLE ([Campo] NVARCHAR(60), [Tipo] NVARCHAR(40), [Descripcion] NVARCHAR(300),
                      [Tratamiento] NVARCHAR(200), [Cantidad] BIGINT);

    IF @Tabla = N'DimFecha'
        INSERT INTO @R
        SELECT v.* FROM (
            SELECT SUM(CASE WHEN TRY_CONVERT(INT, s.[Fin_Semana]) <> CASE WHEN d.[dw] IN (1, 7) THEN 1 ELSE 0 END THEN 1 ELSE 0 END) AS FinSem,
                   SUM(CASE WHEN TRY_CONVERT(INT, s.[Semana_Anio]) <> (DATEPART(DAYOFYEAR, f.[F]) - 1 + d.[dw1]) / 7 + 1 THEN 1 ELSE 0 END) AS Sem,
                   SUM(CASE WHEN TRY_CONVERT(INT, s.[Dia_Semana]) <> d.[dw] THEN 1 ELSE 0 END) AS DiaSem
              FROM [STAGE_HM].[HM].[StageFecha] s
             CROSS APPLY (SELECT [dbo].[fn_LeerFecha](s.[Fecha]) AS [F]) f
             CROSS APPLY (SELECT DATEDIFF(DAY, '19000107', f.[F]) % 7 + 1 AS [dw],
                                 DATEDIFF(DAY, '19000107', DATEFROMPARTS(YEAR(f.[F]), 1, 1)) % 7 AS [dw1]) d
             WHERE f.[F] IS NOT NULL) x
        CROSS APPLY (VALUES
            (N'Fin_Semana', N'INCONSISTENCIA', N'El valor no corresponde a la fecha (sábado y domingo deben ser 1).', N'Recalculado desde la fecha', x.FinSem),
            (N'Semana_Anio', N'INCONSISTENCIA', N'La semana del año no corresponde a la fecha.', N'Recalculado desde la fecha', x.Sem),
            (N'Dia_Semana', N'INCONSISTENCIA', N'El día de la semana no corresponde a la fecha.', N'Recalculado desde la fecha', x.DiaSem)) v(c, t, d, tr, n);

    IF @Tabla = N'DimTemporada'
        INSERT INTO @R
        SELECT N'FechaInicio / FechaFin', N'AMBIGUEDAD',
               N'El día de cambio aparece en dos temporadas (una termina el mismo día que empieza la siguiente).',
               N'Se asigna a la temporada que termina, igual que el TemporadaID de las ventas del archivo', COUNT(*)
          FROM [STAGE_HM].[HM].[StageTemporada] a
          JOIN [STAGE_HM].[HM].[StageTemporada] b
            ON [dbo].[fn_LeerFecha](a.[FechaFin]) = [dbo].[fn_LeerFecha](b.[FechaInicio]) AND a.[TemporadaID] <> b.[TemporadaID];

    IF @Tabla = N'DimArticulo'
    BEGIN
        INSERT INTO @R
        SELECT N'article_id', N'FORMATO', N'El código viene con cero a la izquierda; en transacciones viene sin él.',
               N'Convertido a número para que cruce con las ventas', COUNT(*)
          FROM [STAGE_HM].[HM].[StageArticles] WHERE LEFT(LTRIM([article_id]), 1) = '0';
        INSERT INTO @R
        SELECT u.[Campo], N'DATO_AUSENTE',
               CASE WHEN u.[Campo] = N'detail_desc' THEN N'La descripción no está informada.'
                    ELSE N'El valor no está informado (vacío, Unknown o undefined).' END,
               CASE WHEN u.[Campo] = N'detail_desc' THEN N'Se guarda vacía (es solo descriptiva)'
                    ELSE N'Se unifica como Sin Datos' END, COUNT(*)
          FROM [STAGE_HM].[HM].[StageArticles] a
         CROSS APPLY (VALUES (N'prod_name', a.[prod_name]), (N'product_type_name', a.[product_type_name]),
                             (N'product_group_name', a.[product_group_name]), (N'graphical_appearance_name', a.[graphical_appearance_name]),
                             (N'colour_group_name', a.[colour_group_name]), (N'perceived_colour_value_name', a.[perceived_colour_value_name]),
                             (N'perceived_colour_master_name', a.[perceived_colour_master_name]), (N'department_name', a.[department_name]),
                             (N'section_name', a.[section_name]), (N'garment_group_name', a.[garment_group_name]),
                             (N'detail_desc', a.[detail_desc])) u([Campo], [Valor])
         WHERE NULLIF(LTRIM(RTRIM(u.[Valor])), N'') IS NULL OR LTRIM(RTRIM(u.[Valor])) IN (N'Unknown', N'undefined')
         GROUP BY u.[Campo];
    END

    IF @Tabla = N'DimCliente'
    BEGIN
        INSERT INTO @R
        SELECT v.* FROM (
            SELECT SUM(CASE WHEN TRY_CONVERT(FLOAT, [age]) IS NULL OR TRY_CONVERT(FLOAT, [age]) NOT BETWEEN 16 AND 100 THEN 1 ELSE 0 END) AS Edad,
                   SUM(CASE WHEN NULLIF(LTRIM(RTRIM([club_member_status])), '') IS NULL THEN 1 ELSE 0 END) AS Club,
                   SUM(CASE WHEN NULLIF(LTRIM(RTRIM([fashion_news_frequency])), '') IS NULL THEN 1 ELSE 0 END) AS Noticias,
                   -- el mismo valor escrito con otras mayusculas: filas que no usan la escritura mas comun de su valor
                   (SELECT ISNULL(SUM(g.[Filas] - g.[Mayor]), 0)
                      FROM (SELECT UPPER(v.[x]) AS [u], SUM(v.[n]) AS [Filas], MAX(v.[n]) AS [Mayor]
                              FROM (SELECT LTRIM(RTRIM([fashion_news_frequency])) COLLATE Latin1_General_CS_AS AS [x], COUNT(*) AS [n]
                                      FROM [STAGE_HM].[HM].[StageCustomers]
                                     WHERE NULLIF(LTRIM(RTRIM([fashion_news_frequency])), '') IS NOT NULL
                                     GROUP BY LTRIM(RTRIM([fashion_news_frequency])) COLLATE Latin1_General_CS_AS) v
                             GROUP BY UPPER(v.[x]) HAVING COUNT(*) > 1) g) AS NoticiasFmt,
                   SUM(CASE WHEN NULLIF(LTRIM(RTRIM([FN])), '') IS NULL THEN 1 ELSE 0 END) AS FN,
                   SUM(CASE WHEN NULLIF(LTRIM(RTRIM([Active])), '') IS NULL THEN 1 ELSE 0 END) AS Act,
                   SUM(CASE WHEN TRY_CONVERT(FLOAT, [FN]) = 1 AND UPPER(LTRIM(RTRIM([fashion_news_frequency]))) = 'NONE' THEN 1 ELSE 0 END) AS FnNone,
                   SUM(CASE WHEN NULLIF(LTRIM(RTRIM([FN])), '') IS NULL
                             AND UPPER(LTRIM(RTRIM([fashion_news_frequency]))) IN ('REGULARLY', 'MONTHLY') THEN 1 ELSE 0 END) AS NoFnNews,
                   SUM(CASE WHEN TRY_CONVERT(FLOAT, [Active]) = 1 AND UPPER(LTRIM(RTRIM([club_member_status]))) = 'LEFT CLUB' THEN 1 ELSE 0 END) AS ActLeft
              FROM [STAGE_HM].[HM].[StageCustomers]) x
        CROSS APPLY (VALUES
            (N'age', N'DATO_AUSENTE', N'La edad no está informada o está fuera de 16–100.', N'Edad NULL; rango de edad "Sin dato" (el cliente se carga)', x.Edad),
            (N'club_member_status', N'DATO_AUSENTE', N'El estado del club no está informado.', N'Se guarda como SIN DATO', x.Club),
            (N'fashion_news_frequency', N'DATO_AUSENTE', N'La frecuencia de noticias no está informada.', N'Se guarda como SIN DATO', x.Noticias),
            (N'fashion_news_frequency', N'FORMATO', N'El mismo valor escrito con otras mayúsculas (None / NONE).', N'Se unifica en mayúsculas', x.NoticiasFmt),
            (N'FN', N'DATO_AUSENTE', N'El archivo solo trae 1 o vacío.', N'Vacío se guarda como 0 (no suscrito)', x.FN),
            (N'Active', N'DATO_AUSENTE', N'El archivo solo trae 1 o vacío.', N'Vacío se guarda como 0 (no activo)', x.Act),
            (N'FN / fashion_news_frequency', N'INCONSISTENCIA', N'Recibe noticias (FN = 1) pero la frecuencia es NONE.', N'Se carga tal cual; se reporta al negocio', x.FnNone),
            (N'FN / fashion_news_frequency', N'INCONSISTENCIA', N'FN vacío pero la frecuencia es Regularly o Monthly.', N'Se carga tal cual; se reporta al negocio', x.NoFnNews),
            (N'Active / club_member_status', N'INCONSISTENCIA', N'Cliente activo (Active = 1) pero el club dice LEFT CLUB.', N'Se carga tal cual; se reporta al negocio', x.ActLeft)) v(c, t, d, tr, n);
        -- codigo postal que concentra demasiados clientes: posible valor por defecto del sistema
        INSERT INTO @R
        SELECT TOP (1) N'postal_code', N'VALOR_ATIPICO',
               N'Un mismo código postal concentra muchísimos clientes: posible valor por defecto del sistema.',
               N'Se carga tal cual; se reporta al negocio', COUNT(*)
          FROM [STAGE_HM].[HM].[StageCustomers]
         GROUP BY [postal_code] HAVING COUNT(*) > 1000 ORDER BY COUNT(*) DESC;
    END

    IF @Tabla = N'FactVentas'
        INSERT INTO @R
        SELECT v.* FROM (
            SELECT SUM(CASE WHEN p.[Pre] LIKE '%,%' AND p.[Pre] NOT LIKE '%.%' THEN 1 ELSE 0 END) AS Coma,
                   SUM(CASE WHEN TRY_CONVERT(FLOAT, p.[Pre]) = 0 THEN 1 ELSE 0 END) AS Cero,
                   SUM(CASE WHEN TRY_CONVERT(FLOAT, p.[Pre]) < 0 THEN 1 ELSE 0 END) AS Neg,
                   SUM(CASE WHEN s.[t_dat] LIKE '%/%' THEN 1 ELSE 0 END) AS FechaBarra
              FROM [STAGE_HM].[HM].[StageTransactions] s
             CROSS APPLY (SELECT NULLIF(LTRIM(RTRIM(s.[price])), '') AS [Pre]) p) x
        CROSS APPLY (VALUES
            (N'price', N'FORMATO', N'Precio con coma decimal.', N'La coma se lee como decimal y se multiplica por 40 000', x.Coma),
            (N'price', N'VALOR_ATIPICO', N'Precio 0 (posible oferta).', N'Se carga tal cual', x.Cero),
            (N'price', N'VALOR_ATIPICO', N'Precio negativo (posible devolución).', N'Se carga tal cual', x.Neg),
            (N't_dat', N'FORMATO', N'Fecha con "/" en lugar de yyyymmdd.', N'Se lee como día/mes/año', x.FechaBarra)) v(c, t, d, tr, n);

    IF @Tabla = N'FactMetas'
        INSERT INTO @R
        SELECT N'Escenario / Monto', N'INCONSISTENCIA',
               N'Los escenarios no van de menor a mayor (Escenario 1 < 2 < 3) para la misma sección, temporada y mes.',
               N'Se carga tal cual; se reporta al negocio', COUNT(*)
          FROM (SELECT [department_name], [section_name], [TemporadaID], [AnioMes],
                       MAX(CASE WHEN [Escenario] = 'Escenario 1' THEN [Monto] END) AS e1,
                       MAX(CASE WHEN [Escenario] = 'Escenario 2' THEN [Monto] END) AS e2,
                       MAX(CASE WHEN [Escenario] = 'Escenario 3' THEN [Monto] END) AS e3
                  FROM [STAGE_HM].[HM].[StageGoals]
                 GROUP BY [department_name], [section_name], [TemporadaID], [AnioMes]) m
         WHERE NOT (m.e1 < m.e2 AND m.e2 < m.e3);

    INSERT INTO [dbo].[CalidadDatos] ([AuditKey], [Entidad], [Campo], [TipoProblema], [Descripcion], [Tratamiento], [Cantidad])
    SELECT @AuditKey, @Tabla, [Campo], [Tipo], [Descripcion], [Tratamiento], [Cantidad] FROM @R WHERE [Cantidad] > 0;
END
GO

/* Cierre de la auditoria de cada paquete (tarea "Update AuditDim").
   Hace lo mismo que el UPDATE del laboratorio y ademas registra la calidad de la carga:
   duplicados descartados y filas enviadas a la tabla de error de esa tabla. */
CREATE OR ALTER PROCEDURE [dbo].[sp_CerrarAuditoria]
    @AuditKey INT,
    @RowCount INT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE [dbo].[DIM_AUDIT]
       SET [ExecStopDT] = SYSDATETIME(), [ExtractRowCnt] = @RowCount, [TableFinalRowCnt] = @RowCount,
           [SuccessfulProcessingInd] = 'Y'
     WHERE [AuditKey] = @AuditKey;

    DECLARE @Tabla NVARCHAR(100) = (SELECT [TableName] FROM [dbo].[DIM_AUDIT] WHERE [AuditKey] = @AuditKey);
    DECLARE @Dup BIGINT = 0, @Err BIGINT = 0;

    IF @Tabla = N'[Ventas].[FactVentas]'
    BEGIN
        -- lineas identicas: quedaron en una fila y LineasOrigen dice cuantas venian
        SELECT @Dup = ISNULL(SUM(CAST([LineasOrigen] AS BIGINT)) - COUNT_BIG(*), 0) FROM [Ventas].[FactVentas];
        SELECT @Err = COUNT_BIG(*) FROM [Ventas].[ErrorFactVentas];
    END
    ELSE IF @Tabla = N'[Ventas].[FactMetas]'
        SELECT @Dup = ISNULL(SUM(CASE WHEN [Motivo] LIKE N'%repetid%' THEN 1 ELSE 0 END), 0),
               @Err = ISNULL(SUM(CASE WHEN [Motivo] LIKE N'%repetid%' THEN 0 ELSE 1 END), 0)
          FROM [Ventas].[ErrorFactMetas];
    ELSE   -- tablas maestras: ErrorMaestro guarda el nombre corto (DimCliente, DimArticulo...)
        SELECT @Dup = ISNULL(SUM(CASE WHEN [Motivo] LIKE N'%repetid%' THEN 1 ELSE 0 END), 0),
               @Err = ISNULL(SUM(CASE WHEN [Motivo] LIKE N'%repetid%' THEN 0 ELSE 1 END), 0)
          FROM [dbo].[ErrorMaestro] WHERE [Tabla] = PARSENAME(@Tabla, 1);

    UPDATE [dbo].[DIM_AUDIT]
       SET [FilasDuplicadas]   = @Dup,
           [FilasError]        = @Err,
           -- dimensiones: ya las registro su procedimiento (MERGE); stage y hechos se recargan completos
           [FilasInsertadas]   = ISNULL([FilasInsertadas], @RowCount),
           [FilasActualizadas] = ISNULL([FilasActualizadas], 0)
     WHERE [AuditKey] = @AuditKey;

    -- resumen de calidad del archivo de esta tabla (datos que entraron con algun problema)
    DECLARE @Entidad NVARCHAR(60) = PARSENAME(@Tabla, 1);
    EXEC [dbo].[sp_RegistrarCalidad] @AuditKey = @AuditKey, @Tabla = @Entidad;
END
GO
