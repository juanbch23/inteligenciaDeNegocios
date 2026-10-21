/* =====================================================================
   Proyecto H&M - Verificación de indicadores (fuente de las cifras de
   docs\Indicadores_y_Dashboards.md). Instancia: LAPTOP-IO596P6A\DEV
   Definición de CESTA: mismo cliente + mismo día + mismo canal
   (el dataset no trae número de pedido).
   ===================================================================== */
USE [DWH_HM]
SET NOCOUNT ON;

PRINT 'I1/I3) Ventas y participación online por mes';
SELECT d.AnioMes,
       CAST(SUM(f.Precio)/1e6 AS DECIMAL(12,1))                                                    AS Ventas_M,
       CAST(SUM(CASE WHEN c.NombreCanal = 'Online' THEN f.Precio END)/1e6 AS DECIMAL(12,1))        AS Online_M,
       CAST(SUM(CASE WHEN c.NombreCanal <> 'Online' THEN f.Precio END)/1e6 AS DECIMAL(12,1))       AS Tienda_M,
       CAST(100.0*SUM(CASE WHEN c.NombreCanal = 'Online' THEN f.Precio END)/SUM(f.Precio) AS DECIMAL(5,1)) AS PctOnline
  FROM Ventas.FactVentas f
  JOIN GENERICO.DimFecha d ON d.FechaKey = f.FechaKey
  JOIN Ventas.DimCanal  c ON c.CanalKey = f.CanalKey
 GROUP BY d.AnioMes ORDER BY d.AnioMes;

PRINT 'I1) Variación interanual, mismo periodo (1 ene - 22 sep): 2020 vs 2019';
SELECT ISNULL(c.NombreCanal, 'TOTAL') AS Canal,
       CAST(SUM(CASE WHEN d.Anio = 2019 THEN f.Precio END)/1e6 AS DECIMAL(12,1)) AS Periodo2019_M,
       CAST(SUM(CASE WHEN d.Anio = 2020 THEN f.Precio END)/1e6 AS DECIMAL(12,1)) AS Periodo2020_M,
       CAST(100.0*(SUM(CASE WHEN d.Anio = 2020 THEN f.Precio END)/SUM(CASE WHEN d.Anio = 2019 THEN f.Precio END) - 1) AS DECIMAL(6,1)) AS VarPct
  FROM Ventas.FactVentas f
  JOIN GENERICO.DimFecha d ON d.FechaKey = f.FechaKey
  JOIN Ventas.DimCanal  c ON c.CanalKey = f.CanalKey
 WHERE d.Anio IN (2019, 2020) AND (d.Mes_Anio < 9 OR (d.Mes_Anio = 9 AND d.Dia_Mes <= 22))
 GROUP BY ROLLUP(c.NombreCanal);

PRINT 'I4/I5) Ticket por cesta y artículos por cesta';
WITH b AS (SELECT ClienteKey, FechaKey, CanalKey, SUM(Precio) AS V, COUNT(*) AS N
             FROM Ventas.FactVentas GROUP BY ClienteKey, FechaKey, CanalKey)
SELECT d.Anio, c.NombreCanal, COUNT_BIG(*) AS Cestas,
       CAST(AVG(b.V) AS DECIMAL(12,1)) AS Ticket, CAST(AVG(1.0*b.N) AS DECIMAL(5,2)) AS ArticulosPorCesta
  FROM b JOIN GENERICO.DimFecha d ON d.FechaKey = b.FechaKey JOIN Ventas.DimCanal c ON c.CanalKey = b.CanalKey
 GROUP BY ROLLUP(d.Anio, c.NombreCanal) ORDER BY 1, 2;

PRINT 'I6/I7/I8) Compradores, nuevos, recompra y retención 2019 -> 2020';
WITH p AS (SELECT f.ClienteKey, MIN(d.Anio) AS Primero,
                  MAX(CASE WHEN d.Anio = 2019 THEN 1 ELSE 0 END) AS C19,
                  MAX(CASE WHEN d.Anio = 2020 THEN 1 ELSE 0 END) AS C20,
                  COUNT(DISTINCT d.AnioMes) AS Meses
             FROM Ventas.FactVentas f JOIN GENERICO.DimFecha d ON d.FechaKey = f.FechaKey GROUP BY f.ClienteKey)
SELECT COUNT(*) AS Compradores,
       CAST(SUM(CASE WHEN Meses > 1 THEN 1 ELSE 0 END)*100.0/COUNT(*) AS DECIMAL(5,1)) AS PctRecompra,
       SUM(CASE WHEN Primero = 2019 THEN 1 ELSE 0 END) AS Nuevos2019,
       SUM(CASE WHEN Primero = 2020 THEN 1 ELSE 0 END) AS Nuevos2020,
       CAST(SUM(C19*C20)*100.0/SUM(C19) AS DECIMAL(5,1)) AS PctRetencion19a20
  FROM p;

PRINT 'I9) Club: compradores y venta por cliente según Active';
SELECT c.Active, COUNT(DISTINCT f.ClienteKey) AS Compradores,
       CAST(SUM(f.Precio)/COUNT(DISTINCT f.ClienteKey) AS DECIMAL(12,0)) AS VentaPorCliente
  FROM Ventas.FactVentas f JOIN Ventas.DimCliente c ON c.ClienteKey = f.ClienteKey
 GROUP BY c.Active;

PRINT 'I10/I12) Omnicanal, venta cruzada y concentración de clientes';
WITH c AS (SELECT f.ClienteKey, SUM(f.Precio) AS V, COUNT(DISTINCT a.IndexGroupName) AS Grupos, COUNT(DISTINCT f.CanalKey) AS Canales
             FROM Ventas.FactVentas f JOIN Ventas.DimArticulo a ON a.ArticuloKey = f.ArticuloKey GROUP BY f.ClienteKey),
     r AS (SELECT V, Grupos, Canales, NTILE(5) OVER (ORDER BY V DESC) AS Q FROM c)
SELECT CAST(100.0*SUM(CASE WHEN Q = 1 THEN V END)/SUM(V) AS DECIMAL(5,1))                  AS PctVentasTop20Clientes,
       CAST(100.0*SUM(CASE WHEN Grupos >= 2 THEN 1 ELSE 0 END)/COUNT(*) AS DECIMAL(5,1))   AS PctClientesMultiGrupo,
       CAST(100.0*SUM(CASE WHEN Canales = 2 THEN 1 ELSE 0 END)/COUNT(*) AS DECIMAL(5,1))   AS PctClientesOmnicanal,
       CAST(AVG(CASE WHEN Canales = 2 THEN V END) AS DECIMAL(12,0))                          AS VentaClienteOmnicanal,
       CAST(AVG(CASE WHEN Canales = 1 THEN V END) AS DECIMAL(12,0))                          AS VentaClienteUnCanal
  FROM r;

PRINT 'I11) Descuento implícito (precio vs. precio máximo observado del artículo)';
WITH lp AS (SELECT ArticuloKey, MAX(Precio) AS PL FROM Ventas.FactVentas GROUP BY ArticuloKey)
SELECT d.Anio, c.NombreCanal,
       CAST(100*(1 - SUM(f.Precio)/SUM(lp.PL)) AS DECIMAL(5,1))                                  AS DescuentoPct,
       CAST(100.0*SUM(CASE WHEN f.Precio < 0.7*lp.PL THEN 1 ELSE 0 END)/COUNT(*) AS DECIMAL(5,1)) AS PctLineasDescMayor30
  FROM Ventas.FactVentas f JOIN lp ON lp.ArticuloKey = f.ArticuloKey
  JOIN GENERICO.DimFecha d ON d.FechaKey = f.FechaKey JOIN Ventas.DimCanal c ON c.CanalKey = f.CanalKey
 GROUP BY ROLLUP(d.Anio, c.NombreCanal) ORDER BY 1, 2;

PRINT 'I2) Cumplimiento de meta por temporada (meta diaria, ver 04_vistas_cubo.sql)';
WITH v AS (SELECT FechaKey, DepartamentoKey, SUM(Precio) AS V FROM Ventas.FactVentas GROUP BY FechaKey, DepartamentoKey),
     m AS (SELECT Escenario, FechaKey, DepartamentoKey, SUM(MetaDiaria) AS M FROM Ventas.vw_FactMetasDiaria GROUP BY Escenario, FechaKey, DepartamentoKey),
     j AS (SELECT m.Escenario, m.FechaKey, m.M, ISNULL(v.V, 0) AS V FROM m LEFT JOIN v ON v.FechaKey = m.FechaKey AND v.DepartamentoKey = m.DepartamentoKey)
SELECT t.Temporada,
       CAST(100*SUM(CASE WHEN Escenario = 'Escenario 1' THEN V END)/SUM(CASE WHEN Escenario = 'Escenario 1' THEN M END) AS DECIMAL(6,1)) AS Esc1,
       CAST(100*SUM(CASE WHEN Escenario = 'Escenario 2' THEN V END)/SUM(CASE WHEN Escenario = 'Escenario 2' THEN M END) AS DECIMAL(6,1)) AS Esc2,
       CAST(100*SUM(CASE WHEN Escenario = 'Escenario 3' THEN V END)/SUM(CASE WHEN Escenario = 'Escenario 3' THEN M END) AS DECIMAL(6,1)) AS Esc3
  FROM j JOIN Ventas.vw_FechaTemporada ft ON ft.FechaKey = j.FechaKey
  JOIN Ventas.DimTemporada t ON t.TemporadaKey = ft.TemporadaKey
 GROUP BY t.TemporadaID, t.Temporada ORDER BY t.TemporadaID;

PRINT 'I2) Cumplimiento por sección (Escenario 2)';
WITH v AS (SELECT DepartamentoKey, SUM(Precio) AS V FROM Ventas.FactVentas GROUP BY DepartamentoKey),
     m AS (SELECT DepartamentoKey, SUM(MetaDiaria) AS M FROM Ventas.vw_FactMetasDiaria WHERE Escenario = 'Escenario 2' GROUP BY DepartamentoKey)
SELECT dd.section_name AS Seccion, CAST(SUM(ISNULL(v.V,0))/1e6 AS DECIMAL(12,1)) AS Ventas_M, CAST(SUM(m.M)/1e6 AS DECIMAL(12,1)) AS Meta_M,
       CAST(100*SUM(ISNULL(v.V,0))/SUM(m.M) AS DECIMAL(8,1)) AS CumplimientoPct
  FROM m JOIN Ventas.DimDepartamento dd ON dd.DepartamentoKey = m.DepartamentoKey
  LEFT JOIN v ON v.DepartamentoKey = m.DepartamentoKey
 GROUP BY dd.section_name ORDER BY CumplimientoPct;
