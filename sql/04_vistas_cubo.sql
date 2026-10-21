/* =====================================================================
   Proyecto H&M - Vistas que alimentan el cubo tabular
   Instancia: LAPTOP-IO596P6A\DEV

   GoalsHyM.xlsx trae una meta por Escenario, departamento/seccion,
   temporada y mes. Comparando contra las ventas reales, [Monto] se
   comporta como META DIARIA:
       ventas / (Monto x dias)  =  139% / 121% / 105%  (Escenario 1/2/3)
   mientras que tomarlo como meta mensual da ~2.800%.
   Por eso el cubo usa la meta expandida a nivel dia: asi se suma bien
   con cualquier filtro de fechas (dia, semana, mes, temporada).
   ===================================================================== */
USE [DWH_HM]
GO

-- dia -> temporada, tal como lo asignan las transacciones (un dia = una temporada)
CREATE OR ALTER VIEW [Ventas].[vw_FechaTemporada]
AS
SELECT DISTINCT [FechaKey], [TemporadaKey]
  FROM [Ventas].[FactVentas];
GO

-- meta diaria: una fila por escenario, departamento y dia del mes/temporada de la meta
CREATE OR ALTER VIEW [Ventas].[vw_FactMetasDiaria]
AS
SELECT m.[Escenario],
       ft.[FechaKey],
       m.[DepartamentoKey],
       m.[TemporadaKey],
       m.[Monto] AS [MetaDiaria]
  FROM [Ventas].[FactMetas] m
  JOIN [Ventas].[vw_FechaTemporada] ft
    ON ft.[TemporadaKey] = m.[TemporadaKey]
  JOIN [GENERICO].[DimFecha] d
    ON d.[FechaKey] = ft.[FechaKey]
   AND d.[AnioMes]  = m.[AnioMes];
GO

-- permiso de lectura para el servicio de Analysis Services (procesa el cubo)
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'NT Service\MSOLAP$TABULAR')
    CREATE LOGIN [NT Service\MSOLAP$TABULAR] FROM WINDOWS;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'NT Service\MSOLAP$TABULAR')
    CREATE USER [NT Service\MSOLAP$TABULAR] FOR LOGIN [NT Service\MSOLAP$TABULAR];
ALTER ROLE [db_datareader] ADD MEMBER [NT Service\MSOLAP$TABULAR];
GO
