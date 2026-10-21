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

-- ventas con precio de lista (precio máximo observado del artículo) y banda de descuento
-- -> indicador "Descuento implícito" (docs\Indicadores_y_Dashboards.md, 3.11)
CREATE OR ALTER VIEW [Ventas].[vw_FactVentasCubo]
AS
SELECT v.[FechaKey], v.[ClienteKey], v.[ArticuloKey], v.[DepartamentoKey], v.[CanalKey], v.[TemporadaKey],
       v.[Precio], v.[PrecioLista],
       CASE WHEN v.[Precio] >= v.[PrecioLista]       THEN '1. Sin descuento'
            WHEN v.[Precio] >= 0.9 * v.[PrecioLista] THEN '2. Hasta 10 %'
            WHEN v.[Precio] >= 0.7 * v.[PrecioLista] THEN '3. 10 % a 30 %'
            ELSE '4. Más de 30 %' END AS [BandaDescuento]
  FROM (SELECT f.*, MAX(f.[Precio]) OVER (PARTITION BY f.[ArticuloKey]) AS [PrecioLista]
          FROM [Ventas].[FactVentas] f) v;
GO

-- comportamiento de compra de cada cliente (calculado sobre todo el historial)
-- -> captación, recompra, retención, omnicanalidad, club y concentración (3.6 a 3.10, 3.12)
CREATE OR ALTER VIEW [Ventas].[vw_ClienteComportamiento]
AS
WITH c AS (
    SELECT f.[ClienteKey],
           MIN(f.[FechaKey])                                                       AS [PrimeraCompraKey],
           COUNT(DISTINCT d.[AnioMes])                                             AS [MesesConCompra],
           MAX(CASE WHEN ch.[NombreCanal] = 'Online' THEN 1 ELSE 0 END)           AS [UsaOnline],
           MAX(CASE WHEN ch.[NombreCanal] <> 'Online' THEN 1 ELSE 0 END)          AS [UsaTienda],
           MAX(CASE WHEN d.[Anio] = 2019 THEN 1 ELSE 0 END)                        AS [Compra2019],
           MAX(CASE WHEN d.[Anio] = 2020 THEN 1 ELSE 0 END)                        AS [Compra2020],
           NTILE(10) OVER (ORDER BY SUM(f.[Precio]) DESC)                          AS [DecilValor]   -- solo compradores
      FROM [Ventas].[FactVentas] f
      JOIN [GENERICO].[DimFecha] d  ON d.[FechaKey] = f.[FechaKey]
      JOIN [Ventas].[DimCanal]   ch ON ch.[CanalKey] = f.[CanalKey]
     GROUP BY f.[ClienteKey])
SELECT dc.[ClienteKey], dc.[FN], dc.[Active], dc.[ClubMemberStatus], dc.[FashionNewsFrequency], dc.[Edad], dc.[RangoEdad],
       CASE WHEN dc.[Active] = 1 THEN 'Club activo' ELSE 'No activo' END                     AS [ClubActivo],
       CAST(CAST(CAST(c.[PrimeraCompraKey] AS CHAR(8)) AS DATE) AS DATETIME)                 AS [FechaPrimeraCompra],
       ISNULL(c.[MesesConCompra], 0)                                                         AS [MesesConCompra],
       CASE WHEN c.[ClienteKey] IS NULL THEN 'Sin compras'
            WHEN c.[UsaOnline] = 1 AND c.[UsaTienda] = 1 THEN 'Omnicanal'
            WHEN c.[UsaOnline] = 1 THEN 'Solo online' ELSE 'Solo tienda' END                 AS [TipoCanal],
       ISNULL(c.[Compra2019], 0)                                                             AS [Compra2019],
       ISNULL(c.[Compra2020], 0)                                                             AS [Compra2020],
       CASE WHEN c.[ClienteKey] IS NULL THEN 'Sin compras'
            WHEN c.[DecilValor] <= 2 THEN '1. Top 20 %'
            WHEN c.[DecilValor] <= 5 THEN '2. Siguiente 30 %'
            ELSE '3. Resto 50 %' END                                                         AS [SegmentoValor]
  FROM [Ventas].[DimCliente] dc
  LEFT JOIN c ON c.[ClienteKey] = dc.[ClienteKey]
 WHERE dc.[ClienteKey] > 0;
GO

-- permiso de lectura para el servicio de Analysis Services (procesa el cubo)
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'NT Service\MSOLAP$TABULAR')
    CREATE LOGIN [NT Service\MSOLAP$TABULAR] FROM WINDOWS;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'NT Service\MSOLAP$TABULAR')
    CREATE USER [NT Service\MSOLAP$TABULAR] FOR LOGIN [NT Service\MSOLAP$TABULAR];
ALTER ROLE [db_datareader] ADD MEMBER [NT Service\MSOLAP$TABULAR];
GO
