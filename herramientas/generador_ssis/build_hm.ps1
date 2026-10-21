$ErrorActionPreference = 'Stop'
$sp  = Split-Path -Parent $MyInvocation.MyCommand.Path
$gac = 'C:\WINDOWS\Microsoft.Net\assembly'
$v   = 'v4.0_17.0.0.0__89845dcd8080cc91'
$refs = @(
  "$gac\GAC_MSIL\Microsoft.SqlServer.ManagedDTS\$v\Microsoft.SqlServer.ManagedDTS.dll",
  "$gac\GAC_64\Microsoft.SqlServer.DTSRuntimeWrap\$v\Microsoft.SqlServer.DTSRuntimeWrap.dll",
  "$gac\GAC_MSIL\Microsoft.SqlServer.DTSPipelineWrap\$v\Microsoft.SqlServer.DTSPipelineWrap.dll",
  "$gac\GAC_64\Microsoft.SqlServer.SQLTask\$v\Microsoft.SqlServer.SQLTask.dll",
  "$gac\GAC_MSIL\Microsoft.SqlServer.SQLTaskConnectionsWrap\$v\Microsoft.SqlServer.SQLTaskConnectionsWrap.dll",
  'System.Core.dll'
)
Add-Type -Path "$sp\HMBuilder.cs" -ReferencedAssemblies $refs -IgnoreWarnings

$data = 'C:\Users\Juan\Repositorios\inteligenciaNegocios\proyecto\data\examen_bi'
$out  = "$sp\out"
New-Item -ItemType Directory -Force $out | Out-Null

$b = New-Object HMBuilder
$b.BuildStage("$out\stage_H&M.ispac", $data)
'stage_H&M.ispac OK'
$b = New-Object HMBuilder
try { $b.BuildDwh("$out\DWH_H&M.ispac") } catch { $e=$_.Exception; while($e.InnerException){$e=$e.InnerException}; $e.Message; $e.StackTrace; throw }
'DWH_H&M.ispac OK'
