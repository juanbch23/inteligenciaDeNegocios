/* =====================================================================
   Proyecto H&M - Base de datos STAGE
   Instancia : LAPTOP-IO596P6A\DEV  (SQL Server 2025 Developer)
   Origen    : CSV / XLSX de proyecto\data\examen_bi

   Regla: el STAGE es una COPIA FIEL del archivo. Todas las columnas son
   TEXTO (VARCHAR / NVARCHAR), asi cualquier dato sucio entra sin hacer
   fallar la carga (texto en un numero, fecha mal escrita, campo vacio).
   La validacion, la conversion de tipos (TRY_CONVERT) y la limpieza se
   hacen al pasar al DWH; lo que no se puede corregir va a una tabla de
   error con su motivo.
   FilaOrigen = numero de fila del archivo (para "quedarse con la primera
   aparicion" cuando un ID viene repetido).
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

/* ---------- articles.csv (105,542 filas, UTF-8) ---------- */
DROP TABLE IF EXISTS [HM].[StageArticles];
CREATE TABLE [HM].[StageArticles](
    [FilaOrigen]                   INT IDENTITY(1,1) NOT NULL,
    [article_id]                   NVARCHAR(100)  NULL,
    [product_code]                 NVARCHAR(100)  NULL,
    [prod_name]                    NVARCHAR(200)  NULL,
    [product_type_no]              NVARCHAR(100)  NULL,
    [product_type_name]            NVARCHAR(200)  NULL,
    [product_group_name]           NVARCHAR(200)  NULL,
    [graphical_appearance_no]      NVARCHAR(100)  NULL,
    [graphical_appearance_name]    NVARCHAR(200)  NULL,
    [colour_group_code]            NVARCHAR(100)  NULL,
    [colour_group_name]            NVARCHAR(200)  NULL,
    [perceived_colour_value_id]    NVARCHAR(100)  NULL,
    [perceived_colour_value_name]  NVARCHAR(200)  NULL,
    [perceived_colour_master_id]   NVARCHAR(100)  NULL,
    [perceived_colour_master_name] NVARCHAR(200)  NULL,
    [department_no]                NVARCHAR(100)  NULL,
    [department_name]              NVARCHAR(200)  NULL,
    [index_code]                   NVARCHAR(100)  NULL,
    [index_name]                   NVARCHAR(200)  NULL,
    [index_group_no]               NVARCHAR(100)  NULL,
    [index_group_name]             NVARCHAR(200)  NULL,
    [section_no]                   NVARCHAR(100)  NULL,
    [section_name]                 NVARCHAR(200)  NULL,
    [garment_group_no]             NVARCHAR(100)  NULL,
    [garment_group_name]           NVARCHAR(200)  NULL,
    [detail_desc]                  NVARCHAR(2000) NULL
);
GO

/* ---------- customers.csv (1,371,980 filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageCustomers];
CREATE TABLE [HM].[StageCustomers](
    [FilaOrigen]             INT IDENTITY(1,1) NOT NULL,
    [customer_id]            VARCHAR(100) NULL,
    [FN]                     VARCHAR(100) NULL,   -- '1.0' o vacio
    [Active]                 VARCHAR(100) NULL,   -- '1.0' o vacio
    [club_member_status]     VARCHAR(100) NULL,
    [fashion_news_frequency] VARCHAR(100) NULL,
    [age]                    VARCHAR(100) NULL,
    [postal_code]            VARCHAR(100) NULL
) WITH (DATA_COMPRESSION = PAGE);
GO

/* ---------- transaction.csv (~31.8 millones de filas) ----------
   Sin FilaOrigen: las lineas no tienen ID y los duplicados se resuelven
   agrupando la linea completa (ver paquete FactVentas).                  */
DROP TABLE IF EXISTS [HM].[StageTransactions];
CREATE TABLE [HM].[StageTransactions](
    [t_dat]            VARCHAR(100) NULL,   -- yyyymmdd
    [customer_id]      VARCHAR(100) NULL,
    [article_id]       VARCHAR(100) NULL,
    [price]            VARCHAR(100) NULL,
    [sales_channel_id] VARCHAR(100) NULL,
    [TemporadaID]      VARCHAR(100) NULL
) WITH (DATA_COMPRESSION = PAGE);
GO

/* ---------- DimFecha.csv (734 filas) ---------- */
DROP TABLE IF EXISTS [HM].[StageFecha];
CREATE TABLE [HM].[StageFecha](
    [FilaOrigen]        INT IDENTITY(1,1) NOT NULL,
    [FechaKey]          VARCHAR(100) NULL,
    [Fecha]             VARCHAR(100) NULL,
    [Dia_Semana]        VARCHAR(100) NULL,
    [Nombre_Dia_Semana] VARCHAR(100) NULL,
    [Dia_Mes]           VARCHAR(100) NULL,
    [Dia_Anio]          VARCHAR(100) NULL,
    [Nombre_Mes]        VARCHAR(100) NULL,
    [Mes_Anio]          VARCHAR(100) NULL,
    [Semana_Anio]       VARCHAR(100) NULL,
    [Anio]              VARCHAR(100) NULL,
    [Bimestre]          VARCHAR(100) NULL,
    [Trimestre]         VARCHAR(100) NULL,
    [Cuatrimestre]      VARCHAR(100) NULL,
    [Semestre]          VARCHAR(100) NULL,
    [Fin_Semana]        VARCHAR(100) NULL
);
GO

/* ---------- Temporada.csv (9 filas, ANSI 1252) ---------- */
DROP TABLE IF EXISTS [HM].[StageTemporada];
CREATE TABLE [HM].[StageTemporada](
    [FilaOrigen]  INT IDENTITY(1,1) NOT NULL,
    [TemporadaID] VARCHAR(100) NULL,
    [Temporada]   VARCHAR(100) NULL,
    [FechaInicio] VARCHAR(100) NULL,
    [FechaFin]    VARCHAR(100) NULL
);
GO

/* ---------- GoalsHyM.xlsx, hoja "Hoja1" (27,738 filas) ----------
   El controlador de Excel ya entrega cada columna con un tipo; si una celda
   no calza con el tipo de la columna llega vacia (NULL), no hace fallar la
   carga. Por eso aqui se conservan los tipos que entrega Excel.           */
DROP TABLE IF EXISTS [HM].[StageGoals];
CREATE TABLE [HM].[StageGoals](
    [FilaOrigen]      INT IDENTITY(1,1) NOT NULL,
    [Escenario]       NVARCHAR(255) NULL,
    [Monto]           FLOAT         NULL,
    [department_name] NVARCHAR(255) NULL,
    [section_name]    NVARCHAR(255) NULL,
    [TemporadaID]     FLOAT         NULL,
    [AnioMes]         FLOAT         NULL   -- columna "AÑO MES" del Excel (yyyymm)
);
GO
