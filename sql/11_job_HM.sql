/* =====================================================================
   Proyecto H&M - Job de SQL Server Agent: todo el flujo "end to end"
   (igual que el Laboratorio 4, mas el paso del cubo)

     Paso 1  MasterExecuteStage (SSIS)  CSV/Excel  -> STAGE_HM   (copia fiel, texto)
     Paso 2  MasterExecuteDWH   (SSIS)  STAGE_HM   -> DWH_HM     (limpieza + tablas de error)
     Paso 3  Procesar el cubo   (Analysis Services) DWH_HM -> Tabular_HM
   Cada paso pasa al siguiente solo si termino bien; si falla, el job se
   detiene e informa el error (el cubo sigue con la ultima carga buena).

   Uso el dia del examen: reemplazar los archivos de proyecto\data\examen_bi
   (mismos nombres) -> SSMS > Agente SQL Server > Trabajos > Job_HM >
   "Iniciar trabajo en el paso..." -> paso 1. En Power BI: Actualizar.

   Requisitos (una sola vez): proyectos implementados en SSISDB, carpeta HM
   (herramientas\implementar_ssisdb.ps1) y el cubo Tabular_HM desplegado.
   ===================================================================== */
USE [msdb]
GO

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = N'Job_HM')
    EXEC msdb.dbo.sp_delete_job @job_name = N'Job_HM', @delete_unused_schedule = 1;
GO

DECLARE @server sysname = @@SERVERNAME;   -- LAPTOP-IO596P6A\DEV
DECLARE @cmd1 nvarchar(max) =
    N'/ISSERVER "\"\SSISDB\HM\stage_H&M\MasterExecuteStage.dtsx\"" /SERVER "\"' + @server + N'\"" '
  + N'/Par "\"$ServerOption::LOGGING_LEVEL(Int16)\"";1 /Par "\"$ServerOption::SYNCHRONIZED(Boolean)\"";True /CALLERINFO SQLAGENT /REPORTING E';
DECLARE @cmd2 nvarchar(max) =
    N'/ISSERVER "\"\SSISDB\HM\DWH_H&M\MasterExecuteDWH.dtsx\"" /SERVER "\"' + @server + N'\"" '
  + N'/Par "\"$ServerOption::LOGGING_LEVEL(Int16)\"";1 /Par "\"$ServerOption::SYNCHRONIZED(Boolean)\"";True /CALLERINFO SQLAGENT /REPORTING E';
-- TMSL: procesa todo el cubo, de a una tabla (maxParallelism 1) para no agotar la RAM
DECLARE @cmd3 nvarchar(max) =
    N'{ "sequence": { "maxParallelism": 1, "operations": [ { "refresh": { "type": "full", "objects": [ { "database": "Tabular_HM" } ] } } ] } }';

EXEC msdb.dbo.sp_add_job
     @job_name = N'Job_HM',
     @enabled = 1,
     @description = N'H&M end to end: STAGE_HM -> DWH_HM (limpieza) -> cubo Tabular_HM',
     @owner_login_name = N'LAPTOP-IO596P6A\Juan';

EXEC msdb.dbo.sp_add_jobstep
     @job_name = N'Job_HM',
     @step_name = N'Step_1_Stage_HM',
     @step_id = 1,
     @subsystem = N'SSIS',
     @command = @cmd1,
     @on_success_action = 4,   -- ir al paso indicado (igual que el Laboratorio 4, PDF p.63)
     @on_success_step_id = 2,
     @on_fail_action = 2;      -- salir informando error

EXEC msdb.dbo.sp_add_jobstep
     @job_name = N'Job_HM',
     @step_name = N'Step_2_DWH_HM',
     @step_id = 2,
     @subsystem = N'SSIS',
     @command = @cmd2,
     @on_success_action = 4,   -- ir al paso 3 (procesar el cubo)
     @on_success_step_id = 3,
     @on_fail_action = 2;

EXEC msdb.dbo.sp_add_jobstep
     @job_name = N'Job_HM',
     @step_name = N'Step_3_Procesar_Cubo',
     @step_id = 3,
     @subsystem = N'ANALYSISCOMMAND',
     @server = N'localhost\TABULAR',
     @command = @cmd3,
     @on_success_action = 1,   -- salir informando exito
     @on_fail_action = 2;

-- Horario: todos los dias a las 02:00 (ademas se puede iniciar a mano)
EXEC msdb.dbo.sp_add_jobschedule
     @job_name = N'Job_HM',
     @name = N'HM_Diario_0200',
     @enabled = 1,
     @freq_type = 4,           -- diario
     @freq_interval = 1,
     @active_start_time = 020000;

EXEC msdb.dbo.sp_add_jobserver @job_name = N'Job_HM', @server_name = N'(local)';
GO

/* ---------- Donde queda registrado cada ejecucion ----------
   1) Historial del job (por paso):                                          */
-- SELECT j.name, h.step_id, h.step_name, h.run_date, h.run_time, h.run_duration,
--        CASE h.run_status WHEN 1 THEN 'Exito' WHEN 0 THEN 'Error' ELSE 'Otro' END AS Estado, h.message
--   FROM msdb.dbo.sysjobhistory h JOIN msdb.dbo.sysjobs j ON j.job_id = h.job_id
--  WHERE j.name = 'Job_HM' ORDER BY h.instance_id DESC;
/* 2) Auditoria de cada paquete:  SELECT * FROM DWH_HM.dbo.DIM_AUDIT ORDER BY AuditKey DESC;
   3) Detalle de SSIS:  SSMS > Catalogos de Integration Services > SSISDB > Informes > Todas las ejecuciones
   4) Filas descartadas con su motivo: DWH_HM.Ventas.ErrorFactVentas, Ventas.ErrorFactMetas, dbo.ErrorMaestro */
