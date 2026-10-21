/* =====================================================================
   Proyecto H&M - Usuarios, permisos y configuración de la instancia
   Ejecutar DESPUÉS de 01_crear_STAGE_HM.sql y 02_crear_DWH_HM.sql,
   conectado como administrador (el usuario de Windows que instaló SQL Server).

   Cómo entra cada quien:
   - Usted (quien instaló SQL Server): autenticación de Windows; ya es sysadmin.
   - SSIS (Visual Studio / DTExec): usa SU usuario de Windows (Integrated Security).
   - Analysis Services: procesa el cubo con su CUENTA DE SERVICIO -> sección 3.
   - Otra persona del equipo: sección 4 (Windows) o sección 5 (usuario SQL).
   ===================================================================== */
USE [master]
GO

/* ---------- 1. Memoria máxima (evita que el ETL de 31.8 M filas se quede sin RAM) ---------- */
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'max server memory (MB)', 3072; RECONFIGURE;   -- ajuste a su equipo (~25 % de la RAM)
GO

/* ---------- 2. Comprobar con qué usuario está conectado y si es administrador ---------- */
SELECT SUSER_SNAME() AS UsuarioActual, IS_SRVROLEMEMBER('sysadmin') AS EsSysadmin;   -- debe dar 1
GO

/* ---------- 3. Cuenta de servicio de Analysis Services (lectura del DWH para procesar el cubo) ----------
   Si su instancia de SSAS no se llama TABULAR, cambie el nombre: NT Service\MSOLAP$<INSTANCIA>
   (lo ve en services.msc, servicio "SQL Server Analysis Services (<INSTANCIA>)", pestaña Iniciar sesión). */
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'NT Service\MSOLAP$TABULAR')
    CREATE LOGIN [NT Service\MSOLAP$TABULAR] FROM WINDOWS;
GO
USE [DWH_HM]
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'NT Service\MSOLAP$TABULAR')
    CREATE USER [NT Service\MSOLAP$TABULAR] FOR LOGIN [NT Service\MSOLAP$TABULAR];
ALTER ROLE [db_datareader] ADD MEMBER [NT Service\MSOLAP$TABULAR];
GO

/* ---------- 4. (Opcional) Dar acceso a otra persona con su usuario de Windows ----------
   Reemplace EQUIPO\usuario por el usuario real (ej. LAPTOP-123\maria o DOMINIO\maria).
   - Rol "analista": solo lee el DWH (consultas, Power BI directo a SQL).
   - Rol "etl": puede ejecutar los paquetes SSIS (carga STAGE y DWH).                    */
/*
USE [master];
CREATE LOGIN [EQUIPO\usuario] FROM WINDOWS WITH DEFAULT_DATABASE = [DWH_HM];

USE [DWH_HM];
CREATE USER [EQUIPO\usuario] FOR LOGIN [EQUIPO\usuario];
ALTER ROLE [db_datareader] ADD MEMBER [EQUIPO\usuario];          -- analista
-- ALTER ROLE [db_owner] ADD MEMBER [EQUIPO\usuario];             -- etl (descomentar)

USE [STAGE_HM];
CREATE USER [EQUIPO\usuario] FOR LOGIN [EQUIPO\usuario];
ALTER ROLE [db_datareader] ADD MEMBER [EQUIPO\usuario];          -- analista
-- ALTER ROLE [db_owner] ADD MEMBER [EQUIPO\usuario];             -- etl (descomentar)
*/
GO

/* ---------- 5. (Opcional) Usuario SQL con contraseña (para quien no está en su Windows) ----------
   Requiere activar la autenticación mixta:
     SSMS > clic derecho en el servidor > Propiedades > Seguridad >
     "Modo de autenticación de SQL Server y de Windows" > Aceptar > reiniciar el servicio SQL Server.
   Luego se conecta en SSMS con "Autenticación de SQL Server", usuario hm_analista y la contraseña.
   Nota: los paquetes SSIS del proyecto usan autenticación de Windows; este usuario es para consultar.  */
/*
USE [master];
CREATE LOGIN [hm_analista] WITH PASSWORD = N'Cambie_Esta_Clave_2026!', CHECK_POLICY = ON, DEFAULT_DATABASE = [DWH_HM];

USE [DWH_HM];
CREATE USER [hm_analista] FOR LOGIN [hm_analista];
ALTER ROLE [db_datareader] ADD MEMBER [hm_analista];
*/
GO

/* ---------- 6. Verificación ---------- */
USE [DWH_HM]
SELECT dp.name AS Usuario, dp.type_desc AS Tipo, r.name AS Rol
  FROM sys.database_role_members rm
  JOIN sys.database_principals r  ON r.principal_id  = rm.role_principal_id
  JOIN sys.database_principals dp ON dp.principal_id = rm.member_principal_id
 WHERE dp.name NOT IN ('dbo');
GO
