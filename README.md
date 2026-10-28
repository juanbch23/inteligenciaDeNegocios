# Inteligencia de Negocios — Proyecto H&M

Solución BI de punta a punta sobre el dataset de ventas de H&M:
**CSV / Excel → STAGE → Datamart (SSIS) → Cubo tabular (SSAS) → Power BI**, ejecutada con un solo Job de
SQL Server Agent (`Job_HM`). Sigue las guías del curso incluidas en el repositorio: `proceso_bi_parte 1 y  2.pdf`
(SSIS y Job) y `Cubos Tabulares y Pbi.pdf` (SSAS + Power BI).

> **¿Quieres replicarlo desde cero?** Sigue [INSTALACION.md](INSTALACION.md).

## Estructura

| Carpeta | Contenido |
|---|---|
| `data/examen_bi/` | Datos de origen. **Solo está `GoalsHyM.xlsx`**; los CSV no se suben por su tamaño |
| `sql/` | Creación de `STAGE_HM` y `DWH_HM`, validaciones, vistas del cubo, Job, vaciado para demo e inconsistencias del Stage |
| `H&M/` | Solución de Visual Studio `H&M.sln`: proyectos SSIS `stage_H&M` y `DWH_H&M` + proyecto tabular |
| `Tabular_HM/` | Cubo tabular (compatibilidad 1200): `Model.bim`, generador, despliegue y sincronización de medidas |
| `PowerBI/` | Informe `HM_Dashboard.pbip` (conexión en vivo al cubo) con 5 dashboards y su generador |
| `herramientas/` | Generador de los paquetes SSIS, implementación en SSISDB y generador de datos sucios de prueba |
| `docs/` | Caso (`Caso_HM.docx/pdf`), prototipos (`HM_Modelos_Dashboards.pptx`) y guía de exposición |

## Datos de origen (no incluidos)

Copiar en `data/examen_bi/` (mismos nombres): `transaction.csv`, `customers.csv`, `articles.csv`, `DimFecha.csv`,
`Temporada.csv` y `GoalsHyM.xlsx`. La carpeta se indica con el parámetro de proyecto **`RutaDatos`** de `stage_H&M`
(en Visual Studio: `Project.params`; para el Job: SSISDB → HM → stage_H&M → Configurar).

## Cómo ejecutarlo

1. **Bases de datos** (`LAPTOP-IO596P6A\DEV`): `sql/01_crear_STAGE_HM.sql`, `sql/02_crear_DWH_HM.sql`, `sql/04_vistas_cubo.sql`.
2. **Paquetes SSIS** en SSISDB (carpeta `HM`): `herramientas/implementar_ssisdb.ps1` (o Implementar desde Visual Studio).
3. **Cubo**: en `Tabular_HM/`, `python gen_bim_hm.py Model.bim` y `.\deploy.ps1 -BimPath .\Model.bim`.
4. **Job**: `sql/11_job_HM.sql` crea `Job_HM` (Stage → DWH → cubo). Agente SQL Server → Job_HM → Iniciar en el paso 1.
5. **Validar**: `sql/03_validaciones.sql` (Stage = cargado + duplicados + error, diferencia 0) y
   `sql/14_inconsistencias_stage.sql` (inconsistencias de cada archivo, antes y después).
6. **Power BI**: abrir `PowerBI/HM_Dashboard.pbip` → Actualizar.

## Modelo

**STAGE_HM** (esquema `HM`): copia fiel de cada archivo, todo como texto y sin valores por defecto.

**DWH_HM** (estrella):
- Hechos: `Ventas.FactVentas` (columnstore; `LineasOrigen` = cuántas líneas idénticas venían) y `Ventas.FactMetas`
  (metas tal como vienen: escenario, sección, temporada y mes).
- Dimensiones: `GENERICO.DimFecha`, `Ventas.DimTemporada`, `Ventas.DimCanal`, `Ventas.DimDepartamento`,
  `Ventas.DimArticulo`, `Ventas.DimCliente` (fila `-1` "Sin Datos"; cargadas con `MERGE`).
- Errores (filas que no entran, con motivo y valor original): `Ventas.ErrorFactVentas`, `Ventas.ErrorFactMetas`, `dbo.ErrorMaestro`.
- Auditoría: `dbo.DIM_AUDIT` (como en el laboratorio + filas insertadas, actualizadas, duplicadas, con error y
  `MensajeError` del controlador OnError) y `dbo.CalidadDatos` (resumen por campo de los datos que entran con algún
  problema y su tratamiento).

## Reglas de calidad de datos

- Línea idéntica en todas sus columnas → se conserva una (`LineasOrigen`); en las maestras, `ROW_NUMBER` y la copia va a `ErrorMaestro`.
- `price` × 40 000 con 4 decimales, en el ETL del DWH (después del Stage). La coma se lee como decimal; precio vacío o con letras → error; 0 o negativo se carga tal cual.
- Fechas: `yyyymmdd` / `yyyy-mm-dd`; con “/” se lee día/mes/año (`dbo.fn_LeerFecha`); fecha imposible → error.
- Campos calculados del archivo (`Fin_Semana`, día, semana, mes…) se recalculan desde la fecha.
- La temporada de cada venta se deduce de su fecha con los rangos de `Temporada.csv`; el día de cambio va a la temporada que termina (igual que el `TemporadaID` del archivo).
- `sales_channel_id`: 1 = Tienda física, 2 = Online (confirmado por el profesor).
- Nada de supuestos: lo que no se puede deducir se separa con su motivo; nada se pierde sin explicación.

## Dashboards (Power BI)

| # | Dashboard | Pregunta |
|---|---|---|
| 1 | Clientes | ¿Quiénes compran y cómo? |
| 2 | Artículos | ¿Qué artículos y secciones mueven la venta? |
| 3 | Transacciones | ¿Cómo evolucionan las ventas y por qué canal? |
| 4 | Temporadas y fechas | ¿Cómo se comparan las temporadas y los años? |
| 5 | Metas por temporada y fechas | ¿Qué temporadas y secciones están fuera de meta? |

Nada está escrito a mano: los filtros (Año, Comparar con, Mes, Canal, Temporada, Escenario…) y los valores salen del cubo,
así que los datos nuevos aparecen solos al ejecutar el Job y actualizar Power BI.
