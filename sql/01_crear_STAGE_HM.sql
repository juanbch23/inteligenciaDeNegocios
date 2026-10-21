/* =====================================================================
   Proyecto H&M - Base de datos STAGE
   Instancia : LAPTOP-IO596P6A\DEV  (SQL Server 2025 Developer)
   Origen    : CSV / XLSX de proyecto\data\examen_bi
   Las tablas reciben los archivos tal cual (sin limpieza); la limpieza
   y las llaves sustitutas se hacen al pasar al DWH.
   ===================================================================== */
USE [master]
GO
IF DB_ID(N'STAGE_HM') IS NULL
    CREATE DATABASE [STAGE_HM];
GO
-- carga masiva: registro minimo y crecimiento en bloques grandes
ALTER DATABASE [STAGE_HM] SET RECOVERY SIMPLE;
ALTER DATABASE [STAGE_HM] MODIFY FILE (NAME = N'STAGE_HM', FILEGROWTH = 512MB);
ALTER DATABASE [STAGE_HM] MODIFY FILE (NAME = N'STAGE_HM_log', FILEGROWTH = 256MB);
GO
USE [STAGE_HM]
GO
IF SCHEMA_ID(N'HM') IS NULL EXEC (N'CREATE SCHEMA [HM]');
GO

/* ---------- articles.csv (105,542 filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageArticles];
CREATE TABLE [HM].[StageArticles](
    [article_id]                   INT            NOT NULL,
    [product_code]                 INT            NULL,
    [prod_name]                    NVARCHAR(100)  NULL,
    [product_type_no]              INT            NULL,
    [product_type_name]            NVARCHAR(50)   NULL,
    [product_group_name]           NVARCHAR(50)   NULL,
    [graphical_appearance_no]      INT            NULL,
    [graphical_appearance_name]    NVARCHAR(50)   NULL,
    [colour_group_code]            INT            NULL,
    [colour_group_name]            NVARCHAR(50)   NULL,
    [perceived_colour_value_id]    INT            NULL,
    [perceived_colour_value_name]  NVARCHAR(50)   NULL,
    [perceived_colour_master_id]   INT            NULL,
    [perceived_colour_master_name] NVARCHAR(50)   NULL,
    [department_no]                INT            NULL,
    [department_name]              NVARCHAR(60)   NULL,
    [index_code]                   NVARCHAR(5)    NULL,
    [index_name]                   NVARCHAR(50)   NULL,
    [index_group_no]               INT            NULL,
    [index_group_name]             NVARCHAR(50)   NULL,
    [section_no]                   INT            NULL,
    [section_name]                 NVARCHAR(60)   NULL,
    [garment_group_no]             INT            NULL,
    [garment_group_name]           NVARCHAR(50)   NULL,
    [detail_desc]                  NVARCHAR(1000) NULL
);
GO

/* ---------- customers.csv (1,371,980 filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageCustomers];
CREATE TABLE [HM].[StageCustomers](
    [customer_id]            VARCHAR(64) NOT NULL,
    [FN]                     VARCHAR(5)  NULL,   -- '1.0' o vacio
    [Active]                 VARCHAR(5)  NULL,   -- '1.0' o vacio
    [club_member_status]     VARCHAR(20) NULL,
    [fashion_news_frequency] VARCHAR(20) NULL,
    [age]                    INT         NULL,
    [postal_code]            VARCHAR(64) NULL
);
GO

/* ---------- transaction.csv (~31.8 millones de filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageTransactions];
CREATE TABLE [HM].[StageTransactions](
    [t_dat]            INT         NOT NULL,   -- yyyymmdd
    [customer_id]      VARCHAR(64) NOT NULL,
    [article_id]       INT         NOT NULL,
    [price]            FLOAT       NOT NULL,
    [sales_channel_id] TINYINT     NOT NULL,
    [TemporadaID]      TINYINT     NOT NULL
) WITH (DATA_COMPRESSION = PAGE);   -- ~3 GB sin comprimir
GO

/* ---------- DimFecha.csv (734 filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageFecha];
CREATE TABLE [HM].[StageFecha](
    [FechaKey]          INT          NOT NULL,
    [Fecha]             DATE         NOT NULL,
    [Dia_Semana]        TINYINT      NULL,
    [Nombre_Dia_Semana] VARCHAR(15)  NULL,
    [Dia_Mes]           TINYINT      NULL,
    [Dia_Anio]          SMALLINT     NULL,
    [Nombre_Mes]        VARCHAR(15)  NULL,
    [Mes_Anio]          TINYINT      NULL,
    [Semana_Anio]       TINYINT      NULL,
    [Anio]              SMALLINT     NULL,
    [Bimestre]          TINYINT      NULL,
    [Trimestre]         TINYINT      NULL,
    [Cuatrimestre]      TINYINT      NULL,
    [Semestre]          TINYINT      NULL,
    [Fin_Semana]        TINYINT      NULL
);
GO

/* ---------- Temporada.csv (9 filas, ANSI 1252) ---------- */
DROP TABLE IF EXISTS [HM].[StageTemporada];
CREATE TABLE [HM].[StageTemporada](
    [TemporadaID] TINYINT     NOT NULL,
    [Temporada]   VARCHAR(30) NOT NULL,
    [FechaInicio] DATE        NOT NULL,
    [FechaFin]    DATE        NOT NULL
);
GO

/* ---------- GoalsHyM.xlsx, hoja "Hoja1" (27,738 filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageGoals];
CREATE TABLE [HM].[StageGoals](
    [Escenario]       NVARCHAR(255) NULL,
    [Monto]           FLOAT         NULL,
    [department_name] NVARCHAR(255) NULL,
    [section_name]    NVARCHAR(255) NULL,
    [TemporadaID]     FLOAT         NULL,
    [AnioMes]         FLOAT         NULL   -- columna "AÑO MES" del Excel (yyyymm)
);
GO
