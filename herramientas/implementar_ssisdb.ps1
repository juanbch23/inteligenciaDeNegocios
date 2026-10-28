# Proyecto H&M - Implementa los proyectos SSIS en el catalogo SSISDB (igual que el Laboratorio 4)
# Equivale a: Visual Studio > clic derecho en el proyecto > Implementar > SQL Server > carpeta "HM"
# Uso: .\implementar_ssisdb.ps1   (despues de compilar los .ispac)
param(
    [string]$Server   = 'LAPTOP-IO596P6A\DEV',
    [string]$Password = 'HM_SSISDB#2026',   # solo se usa si el catalogo SSISDB todavia no existe
    [string]$Folder   = 'HM',
    [string]$IspacDir = 'C:\Users\Juan\Repositorios\inteligenciaDeNegocios\herramientas\generador_ssis\out'
)
$ErrorActionPreference = 'Stop'
# La API de administracion de SSIS depende de SMO / Microsoft.Data.SqlClient, que trae SSMS 22
$ssms = 'C:\Program Files\Microsoft SQL Server Management Studio 22\Release\Common7\IDE'
$script:probe = @($ssms, "$ssms\CommonExtensions\Microsoft\SSIS\170\Binn")
[AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($s, $e)
    $n = ($e.Name -split ',')[0] + '.dll'
    foreach ($d in $script:probe) { $p = Join-Path $d $n; if (Test-Path $p) { return [Reflection.Assembly]::LoadFrom($p) } }
    return $null
})
[void][Reflection.Assembly]::LoadFrom("$ssms\Microsoft.Data.SqlClient.dll")
[void][Reflection.Assembly]::LoadFrom("$ssms\CommonExtensions\Microsoft\SSIS\170\Binn\Microsoft.SqlServer.Management.IntegrationServices.dll")

$cn = New-Object Microsoft.Data.SqlClient.SqlConnection "Data Source=$Server;Initial Catalog=master;Integrated Security=SSPI;TrustServerCertificate=True"
$cn.Open()
$ssis = New-Object Microsoft.SqlServer.Management.IntegrationServices.IntegrationServices $cn
$catalog = $ssis.Catalogs['SSISDB']
if (-not $catalog) {
    $cmd = $cn.CreateCommand(); $cmd.CommandText = "EXEC sp_configure 'clr enabled', 1; RECONFIGURE;"; [void]$cmd.ExecuteNonQuery()
    $catalog = New-Object Microsoft.SqlServer.Management.IntegrationServices.Catalog($ssis, 'SSISDB', $Password)
    $catalog.Create()
    "Catalogo SSISDB creado"
}

$f = $catalog.Folders[$Folder]
if (-not $f) {
    $f = New-Object Microsoft.SqlServer.Management.IntegrationServices.CatalogFolder($catalog, $Folder, 'Proyecto H&M: STAGE_HM y DWH_HM')
    $f.Create()
    "Carpeta $Folder creada"
}

# nombre en el catalogo (igual al del proyecto) -> archivo .ispac
$proyectos = [ordered]@{ 'stage_H&M' = 'stage_H&M.ispac'; 'DWH_H&M' = 'DWH_H&M.ispac' }   # el nombre debe ser el del proyecto
foreach ($p in $proyectos.Keys) {
    $bytes = [IO.File]::ReadAllBytes((Join-Path $IspacDir $proyectos[$p]))
    [void]$f.DeployProject($p, $bytes)
    "Proyecto $p implementado"
}
$f.Refresh()
$f.Projects | ForEach-Object { "  $($_.Name): " + (($_.Packages | ForEach-Object Name) -join ', ') }
$cn.Close()
