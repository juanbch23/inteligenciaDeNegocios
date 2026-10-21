# Guía de instalación y réplica desde cero — Proyecto BI H&M

Esta guía lleva a cualquier persona, **desde una computadora sin nada instalado**, hasta tener funcionando
la solución completa: bases de datos, carga de datos (ETL), cubo tabular y dashboards de Power BI.

| | |
|---|---|
| **Tiempo total** | ~3 horas (≈1 h de instalaciones + ≈1 h de cargas automáticas + verificación) |
| **Sistema** | Windows 10/11 de 64 bits |
| **Memoria** | 16 GB de RAM recomendados (con 8 GB funciona, pero la carga es más lenta) |
| **Disco libre** | **15 GB** como mínimo (datos 3.6 GB + bases ≈ 6 GB + instaladores) |
| **Permisos** | Ser administrador de la computadora (para instalar) |

> **Convención de esta guía.** Donde diga `TU_PC` reemplace por el nombre de su computadora
> (lo ve con el comando `hostname` en PowerShell). Los nombres de instancia usados en el proyecto son
> **`DEV`** (motor SQL) y **`TABULAR`** (Analysis Services). Si usa otros nombres, la sección 4 explica cómo adaptarlo.

---

## Índice

1. [Instalar el software](#1-instalar-el-software)
2. [Descargar el proyecto](#2-descargar-el-proyecto)
3. [Copiar los datos de origen](#3-copiar-los-datos-de-origen)
4. [Adaptar el proyecto a su computadora](#4-adaptar-el-proyecto-a-su-computadora)
5. [Conectarse a SQL Server](#5-conectarse-a-sql-server)
6. [Crear las bases de datos](#6-crear-las-bases-de-datos)
7. [Usuarios y permisos](#7-usuarios-y-permisos)
8. [Cargar los datos (ETL con SSIS)](#8-cargar-los-datos-etl-con-ssis)
9. [Validar la carga](#9-validar-la-carga)
10. [Crear el cubo tabular](#10-crear-el-cubo-tabular)
11. [Abrir los dashboards de Power BI](#11-abrir-los-dashboards-de-power-bi)
12. [Problemas frecuentes](#12-problemas-frecuentes)

---

## 1. Instalar el software

Instale en este orden. Todo es **gratuito** para uso académico.

### 1.1 SQL Server 2025 Developer — motor, Integration Services y Analysis Services

1. Descargue **SQL Server 2025 Developer** desde <https://www.microsoft.com/es-es/sql-server/sql-server-downloads>
   (botón *Developer* → descarga `SQL2025-SSEI-EntDev.exe`).
2. Ejecútelo **como administrador** → **Personalizado (Custom)** → elija una carpeta → **Instalar**.
3. Se abre el *Centro de instalación* → **Instalación** → **Nueva instalación independiente de SQL Server**.
4. **Edición:** *Especificar una edición gratuita* → **Enterprise Developer** (⚠ no elija *Evaluation*: caduca a los 180 días;
   tampoco *Express*: no trae Integration Services ni Analysis Services).
5. **Selección de características** — marque:
   - ✅ Servicios de Motor de base de datos
   - ✅ Integration Services
   - ✅ Analysis Services
6. **Configuración de instancia:** *Instancia con nombre* → **`DEV`**.
7. **Configuración del servidor:** deje las cuentas de servicio por defecto, tipo de inicio **Automático**.
8. **Configuración del Motor de base de datos** → pestaña *Configuración del servidor*:
   - Modo de autenticación: **Autenticación de Windows** (recomendado).
   - **Agregar usuario actual** (su usuario de Windows queda como administrador).
9. **Configuración de Analysis Services:**
   - Modo de servidor: **Modo tabular**.
   - **Agregar usuario actual**.

   > El instalador crea **una instancia de Analysis Services con el mismo nombre** (`DEV`). El proyecto usa una
   > instancia llamada `TABULAR`; para replicarlo exacto, repita el instalador solo con *Analysis Services* y
   > *Instancia con nombre* = `TABULAR`. O bien use `TU_PC\DEV` como servidor de Analysis Services en la sección 4.
10. **Instalar** y espere a que todo diga *Correcto*.

### 1.2 SQL Server Management Studio (SSMS)
Descargue **SSMS 21 o 22** desde <https://learn.microsoft.com/es-es/ssms/install/install> e instálelo con las opciones por defecto.

### 1.3 Visual Studio 2022 Community + extensiones
1. Descargue **Visual Studio 2022 Community** (<https://visualstudio.microsoft.com/es/vs/community/>).
   En el instalador marque la carga de trabajo **Almacenamiento y procesamiento de datos**.
2. Abra Visual Studio → **Extensiones → Administrar extensiones** → busque e instale:
   - **SQL Server Integration Services Projects 2022** (para los paquetes `.dtsx`).
   - **Microsoft Analysis Services Projects 2022** (para el cubo `.smproj`).
3. Cierre Visual Studio para que se instalen y vuelva a abrirlo.

### 1.4 Controladores
- **Microsoft OLE DB Driver 19 for SQL Server** (`MSOLEDBSQL19`):
  <https://learn.microsoft.com/es-es/sql/connect/oledb/download-oledb-driver-for-sql-server>
- **Microsoft Access Database Engine 2016 Redistributable (x64)** — necesario para leer `GoalsHyM.xlsx` desde SSIS:
  <https://www.microsoft.com/es-es/download/details.aspx?id=54920> (elija `accessdatabaseengine_X64.exe`).

### 1.5 Power BI Desktop
Instálelo desde Microsoft Store (búsqueda: *Power BI Desktop*) o desde <https://powerbi.microsoft.com/es-es/desktop/>.

### 1.6 Opcionales
- **Git** (<https://git-scm.com/download/win>) para clonar el repositorio.
- **Python 3.11+** (<https://www.python.org/downloads/>) solo si quiere **regenerar** el modelo del cubo o el informe Word
  (`pip install python-docx`).

### 1.7 Verificar que los servicios están en ejecución
En PowerShell:
```powershell
Get-Service | Where-Object { $_.Name -match 'MSSQL\$|MSOLAP|MsDts' } | Format-Table Name, Status, StartType
```
Deben aparecer **Running**: `MSSQL$DEV`, `MSOLAP$TABULAR` (o `MSOLAP$DEV`) y `MsDtsServer170`.

---

## 2. Descargar el proyecto

```powershell
cd C:\
git clone https://github.com/juanbch23/inteligenciaDeNegocios.git HM
cd C:\HM
```
(Sin Git: en GitHub → **Code → Download ZIP** y descomprímalo en `C:\HM`.)

Estructura principal:

| Carpeta | Contenido |
|---|---|
| `sql\` | Scripts de bases de datos, permisos, validaciones e indicadores |
| `H&M\` | Solución de Visual Studio `H&M.sln` (2 proyectos SSIS + proyecto tabular) |
| `Tabular_HM\` | Cubo tabular: `Model.bim` y scripts de despliegue |
| `PowerBI\` | Informe `HM_Dashboard.pbip` |
| `data\examen_bi\` | Datos de origen (solo `GoalsHyM.xlsx` viene en el repositorio) |
| `docs\` | Informe y guion de presentación, indicadores |
| `herramientas\` | `configurar_entorno.ps1` y generador de paquetes SSIS |

---

## 3. Copiar los datos de origen

Los CSV **no están en el repositorio** por su tamaño (3.6 GB). Cópielos en `C:\HM\data\examen_bi\`
**con estos nombres exactos**:

| Archivo | Filas (sin encabezado) | Tamaño |
|---|---|---|
| `transaction.csv` | 31,788,324 | 3.4 GB |
| `customers.csv` | 1,371,980 | 207 MB |
| `articles.csv` | 105,542 | 36 MB |
| `DimFecha.csv` | 734 | 47 KB |
| `Temporada.csv` | 9 | < 1 KB |
| `GoalsHyM.xlsx` | 27,738 (hoja `Hoja1`) | 0.9 MB — ya viene incluido |

> No abra ni guarde los CSV con Excel: cambia formatos (ceros a la izquierda, fechas, separadores) y el ETL fallaría.

---

## 4. Adaptar el proyecto a su computadora

El proyecto se construyó en una PC llamada `LAPTOP-IO596P6A`. Un script cambia el servidor y la ruta de los datos
en los ~28 archivos que los usan (conexiones SSIS, scripts SQL, cubo y Power BI).

1. Abra **PowerShell** en `C:\HM`.
2. Permita ejecutar scripts en esta sesión:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```
3. Vea primero qué cambiaría (no modifica nada):
   ```powershell
   .\herramientas\configurar_entorno.ps1 -ServidorSql "TU_PC\DEV" -ServidorSsas "TU_PC\TABULAR" `
       -RutaDatos "C:\HM\data\examen_bi" -Simular
   ```
4. Si la lista es correcta, ejecútelo sin `-Simular`:
   ```powershell
   .\herramientas\configurar_entorno.ps1 -ServidorSql "TU_PC\DEV" -ServidorSsas "TU_PC\TABULAR" `
       -RutaDatos "C:\HM\data\examen_bi"
   ```

| Parámetro | Qué poner |
|---|---|
| `-ServidorSql` | `TU_PC\DEV` (o solo `TU_PC` si instaló la instancia por defecto) |
| `-ServidorSsas` | `TU_PC\TABULAR` (o `TU_PC\DEV` si Analysis Services quedó en la instancia DEV) |
| `-RutaDatos` | Carpeta donde están los CSV y el Excel |
| `-CuentaSsas` | Solo si su instancia de SSAS no se llama TABULAR: `` "NT Service\MSOLAP`$DEV" `` (la `` ` `` antes del `$` es obligatoria en PowerShell) |

> Ejecute el script **una sola vez**. Si se equivoca, vuelva a descargar el proyecto y repítalo.

---

## 5. Conectarse a SQL Server

1. Abra **SQL Server Management Studio**.
2. En la ventana **Conectar al servidor**:

   | Campo | Valor |
   |---|---|
   | Tipo de servidor | Motor de base de datos |
   | Nombre del servidor | `TU_PC\DEV` |
   | Autenticación | **Autenticación de Windows** |
   | Cifrado | Obligatorio |
   | **Certificado de servidor de confianza** | ✅ **marcar** (si no, sale un error de certificado) |

3. **Conectar**. Debe ver el servidor en el *Explorador de objetos*.

Para Analysis Services, igual pero con *Tipo de servidor* = **Analysis Services** y nombre `TU_PC\TABULAR`.

---

## 6. Crear las bases de datos

En SSMS: **Archivo → Abrir → Archivo**, abra cada script y ejecútelo con **F5**, en este orden:

| # | Script | Qué hace |
|---|---|---|
| 1 | `sql\01_crear_STAGE_HM.sql` | Crea la base **STAGE_HM** (esquema `HM`) con 6 tablas, una por archivo |
| 2 | `sql\02_crear_DWH_HM.sql` | Crea la base **DWH_HM**: 6 dimensiones (con miembro comodín −1), 2 hechos, tablas de error, auditoría `DIM_AUDIT` y 5 procedimientos `MERGE` |

Alternativa por consola (PowerShell en `C:\HM\sql`):
```powershell
$S = "TU_PC\DEV"
sqlcmd -S $S -E -C -I -f 65001 -i 01_crear_STAGE_HM.sql
sqlcmd -S $S -E -C -I -f 65001 -i 02_crear_DWH_HM.sql
```
> En `sqlcmd` use siempre **`-I`** (activa QUOTED_IDENTIFIER, que exige la tabla de fechas) y **`-f 65001`**
> (lee el archivo como UTF-8; si no, las tildes se guardan mal).

Verificación: en SSMS presione F5 sobre *Bases de datos*; deben aparecer **STAGE_HM** y **DWH_HM**.

---

## 7. Usuarios y permisos

Ejecute **`sql\00_usuarios_y_permisos.sql`** (mismo método que el paso 6). Hace lo siguiente:

| Sección | Para qué |
|---|---|
| 1. Memoria máxima 3 GB | Evita que SQL Server acapare la RAM y el ETL se quede detenido |
| 2. Comprobación | Muestra su usuario y que es administrador (`EsSysadmin = 1`) |
| 3. Cuenta de Analysis Services | Da lectura sobre `DWH_HM` a `NT Service\MSOLAP$TABULAR`: el cubo se procesa con esa cuenta |
| 4. *(Opcional)* Otro usuario de Windows | Plantilla para dar acceso de lectura (analista) o de carga (ETL) a otra persona |
| 5. *(Opcional)* Usuario SQL con contraseña | Plantilla `hm_analista`; requiere activar la autenticación mixta (instrucciones en el script) |

**¿Quién entra y cómo?**

| Quién | Cómo se autentica | Permisos |
|---|---|---|
| Usted (quien instaló) | Su usuario de Windows | Administrador (sysadmin) |
| Paquetes SSIS (Visual Studio) | Su usuario de Windows | Los suyos |
| Analysis Services al procesar | `NT Service\MSOLAP$TABULAR` | Lectura de `DWH_HM` |
| Otra persona | Su Windows (sección 4) o `hm_analista` (sección 5) | Lectura o carga, según el rol |

Para que otra persona **consulte el cubo** desde Power BI: en SSMS conéctese a Analysis Services →
*Bases de datos* → **Tabular_HM** → *Roles* → clic derecho **Nuevo rol** → permiso **Leer** → pestaña
*Pertenencia* → agregue su usuario de Windows.

---

## 8. Cargar los datos (ETL con SSIS)

### 8.1 Abrir la solución
1. Doble clic en **`C:\HM\H&M\H&M.sln`** (se abre en Visual Studio 2022).
2. En el *Explorador de soluciones* verá: **stage_H&M** (7 paquetes), **DWH_H&M** (9 paquetes) y **Tabular_HM**.
3. Revise el parámetro de proyecto: doble clic en **stage_H&M → Project.params** → `RutaDatos` debe ser la carpeta de los CSV.

### 8.2 Ejecutar la carga
> Antes de empezar **cierre navegadores y programas pesados**: la carga de transacciones necesita memoria.

| Orden | Paquete | Qué hace | Tiempo aprox. |
|---|---|---|---|
| 1 | `stage_H&M` → **MasterExecuteStage.dtsx** | CSV / Excel → STAGE_HM (6 paquetes en paralelo) | 7 min |
| 2 | `DWH_H&M` → **MasterExecuteDWH.dtsx** | STAGE → DWH: contenedor *Dimensiones* y luego *Hechos* | 35–40 min |

Para cada uno: clic derecho sobre el paquete → **Ejecutar paquete**. Espere a que **todas las tareas tengan ✔ verde**
y luego **Depuración → Detener depuración** (Mayús + F5).

Cada paquete sigue la plantilla del curso: *Task Prior RowCnt → Task Get AuditKey → TRUNCATE → flujo de datos →
Task Post RowCnt → Update AuditDim*. El progreso se ve en la tabla de auditoría:
```sql
SELECT AuditKey, TableName, ExecStartDT, ExecStopDT, TableFinalRowCnt, SuccessfulProcessingInd
FROM DWH_HM.dbo.DIM_AUDIT ORDER BY AuditKey DESC;   -- 'Y' = terminó bien; 'N' = en curso o falló
```

### 8.3 Alternativa por consola (sin Visual Studio abierto)
1. En Visual Studio: clic derecho en cada proyecto SSIS → **Compilar**. Genera `bin\Development\<proyecto>.ispac`.
2. En PowerShell:
```powershell
$dt = "C:\Program Files\Microsoft SQL Server\170\DTS\Binn\DTExec.exe"
& $dt /Project "C:\HM\H&M\stage_H&M\bin\Development\stage_H&M.ispac" /Package "MasterExecuteStage.dtsx"
& $dt /Project "C:\HM\H&M\DWH_H&M\bin\Development\DWH_H&M.ispac"   /Package "MasterExecuteDWH.dtsx"
```

---

## 9. Validar la carga

Ejecute **`sql\03_validaciones.sql`**. Todos los conteos deben coincidir con la columna *Esperado*:

| Control | Resultado correcto |
|---|---|
| StageTransactions / FactVentas | **31,788,324** / ErrorFactVentas **0** |
| StageCustomers / DimCliente | 1,371,980 |
| StageArticles / DimArticulo | 105,542 |
| StageGoals / FactMetas | 27,738 / ErrorFactMetas 0 |
| DimFecha / DimTemporada / DimCanal / DimDepartamento | 734 / 9 / 2 / 299 |
| Diferencia de montos DWH vs STAGE | 0.000000 |
| Llaves foráneas no confiables | 0 |
| Comodines −1 | 6 |
| Auditoría con `N` | 0 (si todo corrió a la primera) |

---

## 10. Crear el cubo tabular

1. Ejecute **`sql\04_vistas_cubo.sql`** (crea las vistas que alimentan el cubo).
   Por consola: `sqlcmd -S $S -E -C -I -f 65001 -i 04_vistas_cubo.sql`.
2. **Cierre Power BI** si está abierto.
3. Implemente y procese el cubo (≈ 6 min). Elija **una** opción:

   **Opción A — script (recomendada):**
   ```powershell
   cd C:\HM\Tabular_HM
   .\deploy.ps1 -BimPath .\Model.bim        # muestra DEPLOY OK y PROCESS OK
   ```
   **Opción B — Visual Studio:** en `H&M.sln`, clic derecho en **Tabular_HM → Propiedades** → *Servidor* =
   `TU_PC\TABULAR` → Aceptar → clic derecho **Tabular_HM → Implementar**. La primera vez pide el servidor del
   *área de trabajo*: use el mismo.
4. Verifique con una consulta DAX:
   ```powershell
   .\dax_query.ps1 -Dax 'EVALUATE ROW("Ventas",[.Ventas],"Transacciones",[.Transacciones],"Cumplimiento",[.%Cumplimiento_Meta])'
   ```
   Debe dar ≈ 88,464,597,098 de ventas, 31,788,324 transacciones y 1.10 de cumplimiento.

El cubo tiene 8 tablas, 9 relaciones y 73 medidas DAX (documentadas en `Tabular_HM\MEDIDAS_DAX.md`).

---

## 11. Abrir los dashboards de Power BI

1. Doble clic en **`C:\HM\PowerBI\HM_Dashboard.pbip`**.
2. Power BI se conecta **en directo** al cubo (abajo a la derecha: *Conexión dinámica: conectada*).
3. Páginas:

   | Página | Pregunta |
   |---|---|
   | 1 · Estratégico | ¿Crecemos de forma sana? |
   | 2 · Táctico: Torre de metas | ¿Qué secciones y temporadas no cumplen? |
   | 3 · Analítico: Cliente y precio | ¿Qué palanca de cliente y precio genera más impacto? |

4. Comprobación rápida: en *1 · Estratégico* (año 2020, Escenario 2) debe ver **−10,6 %** frente al año anterior
   y **103,0 %** de cumplimiento.

Si pide credenciales, elija **Usar mis credenciales actuales (Windows)**.

---

## 12. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| SSMS: *"La cadena de certificados fue emitida por una entidad que no es de confianza"* | Certificado autofirmado | Marque **Certificado de servidor de confianza** al conectar |
| `CREATE TABLE ... QUOTED_IDENTIFIER` | `sqlcmd` sin `-I` | Ejecute con `sqlcmd ... -I` (o desde SSMS) |
| Textos con `Ã¡`, `Ã©` en lugar de tildes | Script leído sin UTF-8 | `sqlcmd ... -f 65001`, o ejecútelo desde SSMS |
| SSIS: *"Se truncó el texto..."* en customers o articles | Archivos CSV modificados (Excel) | Vuelva a copiar los CSV originales |
| SSIS: no se puede leer el Excel / *ACE.OLEDB no registrado* | Falta el motor de Access de 64 bits | Instale `accessdatabaseengine_X64.exe` (paso 1.4) |
| La carga de FactVentas deja de avanzar | Poca memoria libre | Cierre programas; confirme el paso 7 (memoria máxima 3 GB) y vuelva a ejecutar `MasterExecuteDWH` |
| DTExec: *"evaluation period has expired"* | Se instaló la edición Evaluation | Reinstale con la edición **Developer** |
| Procesar el cubo: *error de inicio de sesión* | La cuenta de SSAS no tiene permiso | Ejecute `00_usuarios_y_permisos.sql`, sección 3, con el nombre correcto de la instancia |
| Procesar el cubo: *el formato de la cadena de inicialización no cumple OLE DB* | Proveedor OLE DB distinto | Instale el **OLE DB Driver** (paso 1.4) |
| Power BI abre una **"Página 1" vacía** | Falta el archivo de referencia o hay un `model.bim` en `HM_Dashboard.SemanticModel` | No guarde; verifique que esa carpeta tenga solo `definition.pbism` y `modelReference.json` |
| Power BI: *no se puede conectar a Analysis Services* | Servidor SSAS distinto | Revise `PowerBI\HM_Dashboard.SemanticModel\modelReference.json` (paso 4) |

---

### Resumen del orden completo

```
1. Instalar software (SQL Server Developer: motor + SSIS + SSAS tabular, SSMS, VS 2022 + extensiones, drivers, Power BI)
2. git clone  →  3. copiar CSV  →  4. configurar_entorno.ps1
5. Conectar en SSMS  →  6. 01 y 02 (bases)  →  7. 00 (usuarios y permisos)
8. MasterExecuteStage  →  MasterExecuteDWH  →  9. 03_validaciones
10. 04_vistas_cubo  →  deploy.ps1  →  11. abrir HM_Dashboard.pbip
```
