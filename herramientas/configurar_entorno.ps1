<#
.SYNOPSIS
  Adapta el proyecto H&M a otra computadora: cambia el nombre del servidor SQL, el de Analysis Services,
  la carpeta de los datos y la cuenta de servicio de SSAS en todos los archivos del proyecto.

.EXAMPLE
  # desde la carpeta raíz del proyecto (donde está INSTALACION.md)
  .\herramientas\configurar_entorno.ps1 -ServidorSql "MIPC\DEV" -ServidorSsas "MIPC\TABULAR" `
      -RutaDatos "D:\HM\data\examen_bi" -CuentaSsas "NT Service\MSOLAP`$TABULAR"

  Ejecutarlo una sola vez, ANTES de abrir la solución en Visual Studio o el informe en Power BI.
  Use -Simular para ver qué archivos cambiarían sin modificarlos.
#>
param(
    [Parameter(Mandatory)][string]$ServidorSql,             # ej. MIPC\DEV  o  MIPC (instancia por defecto)
    [string]$ServidorSsas = "localhost\TABULAR",            # instancia de Analysis Services en modo tabular
    [Parameter(Mandatory)][string]$RutaDatos,               # carpeta donde están los CSV y GoalsHyM.xlsx
    [string]$CuentaSsas = 'NT Service\MSOLAP$TABULAR',      # cuenta de servicio de SSAS (procesa el cubo)
    [switch]$Simular
)
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot

# valores con los que se construyó el proyecto
$orig = @{
    Sql   = 'LAPTOP-IO596P6A\DEV'
    Ssas  = 'localhost\TABULAR'
    Ruta  = 'C:\Users\Juan\Repositorios\inteligenciaNegocios\proyecto\data\examen_bi'
    Cuenta = 'NT Service\MSOLAP$TABULAR'
}
$RutaDatos = $RutaDatos.TrimEnd('\')

# pares (buscar, reemplazar): forma normal y forma escapada de JSON (\ -> \\)
$reemplazos = @(
    @($orig.Sql,  $ServidorSql),  @($orig.Sql.Replace('\', '\\'),  $ServidorSql.Replace('\', '\\')),
    @($orig.Ssas, $ServidorSsas), @($orig.Ssas.Replace('\', '\\'), $ServidorSsas.Replace('\', '\\')),
    @($orig.Ruta, $RutaDatos),    @($orig.Ruta.Replace('\', '\\'), $RutaDatos.Replace('\', '\\')),
    @($orig.Cuenta, $CuentaSsas)
)

$extensiones = '*.dtsx', '*.conmgr', '*.dtproj', '*.params', '*.sql', '*.py', '*.ps1', '*.bim', '*.json', '*.smproj'
$excluir = '\\(_respaldo_original|_respaldo_estilo_laboratorio|referencia|data|\.git)\\'
$archivos = Get-ChildItem $raiz -Recurse -File -Include $extensiones |
            Where-Object { $_.FullName -notmatch $excluir -and $_.FullName -ne $PSCommandPath }

$cambiados = 0
foreach ($f in $archivos) {
    $bytes = [IO.File]::ReadAllBytes($f.FullName)
    $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $texto = [Text.Encoding]::UTF8.GetString($bytes, [int]$bom * 3, $bytes.Length - [int]$bom * 3)
    $nuevo = $texto
    foreach ($r in $reemplazos) { if ($r[0] -ne $r[1]) { $nuevo = $nuevo.Replace($r[0], $r[1]) } }
    if ($nuevo -ne $texto) {
        $cambiados++
        "  {0}" -f $f.FullName.Substring($raiz.Length + 1)
        if (-not $Simular) { [IO.File]::WriteAllText($f.FullName, $nuevo, (New-Object Text.UTF8Encoding($bom))) }
    }
}
if ($Simular) { "Simulación: $cambiados archivos cambiarían." } else { "Listo: $cambiados archivos actualizados." }
if (-not [IO.File]::Exists("$RutaDatos\transaction.csv")) {
    Write-Warning "No se encontró transaction.csv en $RutaDatos. Copie allí los 5 CSV y GoalsHyM.xlsx."
}
