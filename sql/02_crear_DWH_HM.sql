/* =====================================================================
   Proyecto H&M - Data Warehouse (modelo estrella)
   Instancia : LAPTOP-IO596P6A\DEV  (SQL Server 2025 Developer)
   Dimensiones : GENERICO.DimFecha, Ventas.DimTemporada, Ventas.DimCanal,
                 Ventas.DimDepartamento, Ventas.DimArticulo, Ventas.DimCliente
   Hechos      : Ventas.FactVentas  (transacciones, columnstore)
                 Ventas.FactMetas   (GoalsHyM.xlsx: metas por escenario)
   Errores     : Ventas.ErrorFactVentas, Ventas.ErrorFactMetas
   Auditoria   : dbo.DIM_AUDIT
   Requiere que exista STAGE_HM (los SP de dimensiones leen de ahi).
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
    [SuccessfulProcessingInd] NCHAR(1)         NOT NULL DEFAULT ('N')
);
GO

/* ========================== DIMENSIONES ========================== */
CREATE TABLE [GENERICO].[DimFecha](
    [FechaKey]          INT         NOT NULL CONSTRAINT [PK_DimFecha] PRIMARY KEY,
    [Fecha]             DATE        NOT NULL,
    [Dia_Semana]        TINYINT     NOT NULL,
    [Nombre_Dia_Semana] VARCHAR(15) NOT NULL,
    [Dia_Mes]           TINYINT     NOT NULL,
    [Dia_Anio]          SMALLINT    NOT NULL,
    [Nombre_Mes]        VARCHAR(15) NOT NULL,
    [Mes_Anio]          TINYINT     NOT NULL,
    [Semana_Anio]       TINYINT     NOT NULL,
    [Anio]              SMALLINT    NOT NULL,
    [Bimestre]          TINYINT     NOT NULL,
    [Trimestre]         TINYINT     NOT NULL,
    [Cuatrimestre]      TINYINT     NOT NULL,
    [Semestre]          TINYINT     NOT NULL,
    [Fin_Semana]        TINYINT     NOT NULL,   -- recalculado en el ETL (en el CSV viene siempre 0)
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
    [Precio]          DECIMAL(19,6)  NOT NULL,
    INDEX [CCI_FactVentas] CLUSTERED COLUMNSTORE      -- ~31.8 M filas comprimidas
);
GO
CREATE TABLE [Ventas].[ErrorFactVentas](
    [t_dat]            INT           NULL,
    [customer_id]      VARCHAR(64)   NULL,
    [article_id]       INT           NULL,
    [price]            FLOAT         NULL,
    [sales_channel_id] TINYINT       NULL,
    [TemporadaID]      TINYINT       NULL,
    [FechaKey]         INT           NULL,
    [ClienteKey]       INT           NULL,
    [ArticuloKey]      INT           NULL,
    [DepartamentoKey]  INT           NULL,
    [CanalKey]         INT           NULL,
    [TemporadaKey]     INT           NULL,
    [FechaRegistro]    DATETIME      NOT NULL DEFAULT (GETDATE())
);
GO
CREATE TABLE [Ventas].[FactMetas](
    [Escenario]       NVARCHAR(30)  NOT NULL,
    [FechaKey]        INT           NOT NULL CONSTRAINT [FK_FactMetas_DimFecha]        REFERENCES [GENERICO].[DimFecha]([FechaKey]),
    [AnioMes]         INT           NOT NULL,
    [DepartamentoKey] INT           NOT NULL CONSTRAINT [FK_FactMetas_DimDepartamento] REFERENCES [Ventas].[DimDepartamento]([DepartamentoKey]),
    [TemporadaKey]    INT           NOT NULL CONSTRAINT [FK_FactMetas_DimTemporada]    REFERENCES [Ventas].[DimTemporada]([TemporadaKey]),
    [Monto]           DECIMAL(19,6) NOT NULL,
    CONSTRAINT [PK_FactMetas] PRIMARY KEY ([Escenario],[DepartamentoKey],[TemporadaKey],[AnioMes])
);
GO
CREATE TABLE [Ventas].[ErrorFactMetas](
    [Escenario]       NVARCHAR(30)  NULL,
    [Monto]           FLOAT         NULL,
    [department_name] NVARCHAR(60)  NULL,
    [section_name]    NVARCHAR(60)  NULL,
    [TemporadaID]     TINYINT       NULL,
    [AnioMes]         INT           NULL,
    [FechaKey]        INT           NULL,
    [DepartamentoKey] INT           NULL,
    [TemporadaKey]    INT           NULL,
    [FechaRegistro]   DATETIME      NOT NULL DEFAULT (GETDATE())
);
GO

/* ================= PROCEDIMIENTOS DE CARGA DE DIMENSIONES =================
   MERGE (SCD tipo 1): inserta nuevos y actualiza cambios; nunca borra,
   asi los comodines -1 se conservan. Los ejecutan los paquetes SSIS.        */
CREATE OR ALTER PROCEDURE [Ventas].[sp_DimTemporada]
AS
BEGIN
    SET NOCOUNT ON;
    MERGE [Ventas].[DimTemporada] AS T
    USING (SELECT [TemporadaID],
                  [Temporada],
                  LEFT([Temporada], CHARINDEX('-', [Temporada]) - 1)                 AS [Estacion],
                  CONVERT(SMALLINT, RIGHT([Temporada], 4))                           AS [Anio],
                  [FechaInicio], [FechaFin]
             FROM [STAGE_HM].[HM].[StageTemporada]) AS S
       ON T.[TemporadaID] = S.[TemporadaID]
    WHEN MATCHED AND (T.[Temporada] <> S.[Temporada] OR T.[FechaInicio] <> S.[FechaInicio] OR T.[FechaFin] <> S.[FechaFin]) THEN
        UPDATE SET T.[Temporada] = S.[Temporada], T.[Estacion] = S.[Estacion], T.[Anio] = S.[Anio],
                   T.[FechaInicio] = S.[FechaInicio], T.[FechaFin] = S.[FechaFin]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([TemporadaID],[Temporada],[Estacion],[Anio],[FechaInicio],[FechaFin])
        VALUES (S.[TemporadaID],S.[Temporada],S.[Estacion],S.[Anio],S.[FechaInicio],S.[FechaFin]);
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimCanal]
AS
BEGIN
    SET NOCOUNT ON;
    -- 1 = tienda fisica, 2 = online (interpretacion habitual del dataset H&M de Kaggle)
    MERGE [Ventas].[DimCanal] AS T
    USING (SELECT DISTINCT [sales_channel_id] AS [CanalID],
                  CASE [sales_channel_id] WHEN 1 THEN 'Tienda fisica'
                                          WHEN 2 THEN 'Online'
                                          ELSE 'Canal ' + CONVERT(VARCHAR(3), [sales_channel_id]) END AS [NombreCanal]
             FROM [STAGE_HM].[HM].[StageTransactions]) AS S
       ON T.[CanalID] = S.[CanalID]
    WHEN MATCHED AND T.[NombreCanal] <> S.[NombreCanal] THEN
        UPDATE SET T.[NombreCanal] = S.[NombreCanal]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([CanalID],[NombreCanal]) VALUES (S.[CanalID],S.[NombreCanal]);
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimDepartamento]
AS
BEGIN
    SET NOCOUNT ON;
    MERGE [Ventas].[DimDepartamento] AS T
    USING (SELECT DISTINCT [department_name], [section_name]
             FROM [STAGE_HM].[HM].[StageArticles]
            WHERE [department_name] IS NOT NULL AND [section_name] IS NOT NULL) AS S
       ON T.[department_name] = S.[department_name] AND T.[section_name] = S.[section_name]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([department_name],[section_name]) VALUES (S.[department_name],S.[section_name]);
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimArticulo]
AS
BEGIN
    SET NOCOUNT ON;
    MERGE [Ventas].[DimArticulo] AS T
    USING (SELECT a.[article_id], a.[product_code],
                  ISNULL(a.[prod_name], N'Sin Datos')                    AS [prod_name],
                  ISNULL(a.[product_type_name], N'Sin Datos')            AS [product_type_name],
                  ISNULL(a.[product_group_name], N'Sin Datos')           AS [product_group_name],
                  ISNULL(a.[graphical_appearance_name], N'Sin Datos')    AS [graphical_appearance_name],
                  ISNULL(a.[colour_group_name], N'Sin Datos')            AS [colour_group_name],
                  ISNULL(a.[perceived_colour_value_name], N'Sin Datos')  AS [perceived_colour_value_name],
                  ISNULL(a.[perceived_colour_master_name], N'Sin Datos') AS [perceived_colour_master_name],
                  ISNULL(a.[department_name], N'Sin Datos')              AS [department_name],
                  ISNULL(a.[index_name], N'Sin Datos')                   AS [index_name],
                  ISNULL(a.[index_group_name], N'Sin Datos')             AS [index_group_name],
                  ISNULL(a.[section_name], N'Sin Datos')                 AS [section_name],
                  ISNULL(a.[garment_group_name], N'Sin Datos')           AS [garment_group_name],
                  a.[detail_desc],
                  ISNULL(d.[DepartamentoKey], -1)                        AS [DepartamentoKey]
             FROM [STAGE_HM].[HM].[StageArticles] a
             LEFT JOIN [Ventas].[DimDepartamento] d
               ON d.[department_name] = a.[department_name] AND d.[section_name] = a.[section_name]) AS S
       ON T.[ArticleID] = S.[article_id]
    WHEN MATCHED AND (T.[ProdName] <> S.[prod_name] OR T.[DepartamentoKey] <> S.[DepartamentoKey]
                      OR T.[ColourGroupName] <> S.[colour_group_name] OR T.[ProductTypeName] <> S.[product_type_name]) THEN
        UPDATE SET T.[ProductCode] = S.[product_code], T.[ProdName] = S.[prod_name],
                   T.[ProductTypeName] = S.[product_type_name], T.[ProductGroupName] = S.[product_group_name],
                   T.[GraphicalAppearanceName] = S.[graphical_appearance_name], T.[ColourGroupName] = S.[colour_group_name],
                   T.[PerceivedColourValueName] = S.[perceived_colour_value_name],
                   T.[PerceivedColourMasterName] = S.[perceived_colour_master_name],
                   T.[DepartmentName] = S.[department_name], T.[IndexName] = S.[index_name],
                   T.[IndexGroupName] = S.[index_group_name], T.[SectionName] = S.[section_name],
                   T.[GarmentGroupName] = S.[garment_group_name], T.[DetailDesc] = S.[detail_desc],
                   T.[DepartamentoKey] = S.[DepartamentoKey]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([ArticleID],[ProductCode],[ProdName],[ProductTypeName],[ProductGroupName],[GraphicalAppearanceName],
                [ColourGroupName],[PerceivedColourValueName],[PerceivedColourMasterName],[DepartmentName],[IndexName],
                [IndexGroupName],[SectionName],[GarmentGroupName],[DetailDesc],[DepartamentoKey])
        VALUES (S.[article_id],S.[product_code],S.[prod_name],S.[product_type_name],S.[product_group_name],
                S.[graphical_appearance_name],S.[colour_group_name],S.[perceived_colour_value_name],
                S.[perceived_colour_master_name],S.[department_name],S.[index_name],S.[index_group_name],
                S.[section_name],S.[garment_group_name],S.[detail_desc],S.[DepartamentoKey]);
END
GO

CREATE OR ALTER PROCEDURE [Ventas].[sp_DimCliente]
AS
BEGIN
    SET NOCOUNT ON;
    MERGE [Ventas].[DimCliente] AS T
    USING (SELECT [customer_id],
                  CONVERT(BIT, CASE WHEN [FN] = '1.0' THEN 1 ELSE 0 END)                       AS [FN],
                  CONVERT(BIT, CASE WHEN [Active] = '1.0' THEN 1 ELSE 0 END)                   AS [Active],
                  ISNULL(NULLIF(LTRIM(RTRIM([club_member_status])), ''), 'SIN DATO')           AS [ClubMemberStatus],
                  CASE WHEN NULLIF(LTRIM(RTRIM([fashion_news_frequency])), '') IS NULL THEN 'SIN DATO'
                       WHEN UPPER([fashion_news_frequency]) = 'NONE' THEN 'NONE'
                       ELSE UPPER([fashion_news_frequency]) END                                AS [FashionNewsFrequency],
                  CONVERT(SMALLINT, [age])                                                     AS [Edad],
                  CASE WHEN [age] IS NULL THEN 'Sin dato'
                       WHEN [age] < 25 THEN '16-24'
                       WHEN [age] < 35 THEN '25-34'
                       WHEN [age] < 45 THEN '35-44'
                       WHEN [age] < 55 THEN '45-54'
                       WHEN [age] < 65 THEN '55-64'
                       ELSE '65+' END                                                          AS [RangoEdad],
                  ISNULL([postal_code], '-1')                                                  AS [PostalCode]
             FROM [STAGE_HM].[HM].[StageCustomers]) AS S
       ON T.[CustomerID] = S.[customer_id]
    WHEN MATCHED AND (T.[FN] <> S.[FN] OR T.[Active] <> S.[Active] OR T.[ClubMemberStatus] <> S.[ClubMemberStatus]
                      OR T.[FashionNewsFrequency] <> S.[FashionNewsFrequency]
                      OR ISNULL(T.[Edad], -1) <> ISNULL(S.[Edad], -1) OR T.[PostalCode] <> S.[PostalCode]) THEN
        UPDATE SET T.[FN] = S.[FN], T.[Active] = S.[Active], T.[ClubMemberStatus] = S.[ClubMemberStatus],
                   T.[FashionNewsFrequency] = S.[FashionNewsFrequency], T.[Edad] = S.[Edad],
                   T.[RangoEdad] = S.[RangoEdad], T.[PostalCode] = S.[PostalCode]
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ([CustomerID],[FN],[Active],[ClubMemberStatus],[FashionNewsFrequency],[Edad],[RangoEdad],[PostalCode])
        VALUES (S.[customer_id],S.[FN],S.[Active],S.[ClubMemberStatus],S.[FashionNewsFrequency],S.[Edad],S.[RangoEdad],S.[PostalCode]);
END
GO
