# Sincroniza las medidas y las tablas calculadas del Model.bim con el cubo ya procesado, via TOM,
# SIN reprocesar los datos (solo un "calculate" de las tablas calculadas nuevas).
#  - crea las tablas calculadas que falten (p. ej. AnioComparacion, para el filtro "Comparar con")
#  - borra del cubo las medidas que ya no estan en el Model.bim (o que cambiaron de tabla)
#  - crea o actualiza el resto de medidas
param([string]$BimPath = ".\Model.bim", [string]$Server = "localhost\TABULAR", [string]$Db = "Tabular_HM")
$ErrorActionPreference = "Stop"
$gac = "C:\Windows\Microsoft.NET\assembly\GAC_MSIL"
foreach ($n in "Microsoft.AnalysisServices.Core", "Microsoft.AnalysisServices", "Microsoft.AnalysisServices.Tabular") {
    $dll = Get-ChildItem "$gac\$n" -Recurse -Filter "$n.dll" | Sort-Object FullName -Descending | Select-Object -First 1
    Add-Type -Path $dll.FullName
}
$bim = Get-Content $BimPath -Raw -Encoding UTF8 | ConvertFrom-Json
$s = New-Object Microsoft.AnalysisServices.Tabular.Server
$s.Connect($Server)
$model = $s.Databases.FindByName($Db).Model

# 1) tablas calculadas que falten
$nuevas = 0
foreach ($t in $bim.model.tables) {
    $part = $t.partitions[0]
    if ($part.source.type -ne "calculated" -or $model.Tables.Find($t.name)) { continue }
    $tb = New-Object Microsoft.AnalysisServices.Tabular.Table; $tb.Name = $t.name; $tb.Description = $t.description
    $p = New-Object Microsoft.AnalysisServices.Tabular.Partition; $p.Name = $part.name
    $src = New-Object Microsoft.AnalysisServices.Tabular.CalculatedPartitionSource; $src.Expression = $part.source.expression
    $p.Source = $src; $tb.Partitions.Add($p); $model.Tables.Add($tb)
    $tb.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Calculate)
    $nuevas++
}
if ($nuevas) { $model.SaveChanges() | Out-Null; "Tablas calculadas creadas: $nuevas" }

# 2) medidas: borrar las que sobran, crear/actualizar las demas
$enBim = @{}
foreach ($t in $bim.model.tables) { foreach ($m in $t.measures) { $enBim["$($t.name)|$($m.name)"] = $true } }
$borradas = 0
foreach ($table in $model.Tables) {
    foreach ($tm in @($table.Measures)) {
        if (-not $enBim["$($table.Name)|$($tm.Name)"]) { [void]$table.Measures.Remove($tm); $borradas++ }
    }
}
if ($borradas) { $model.SaveChanges() | Out-Null; "Medidas borradas (ya no estan en el Model.bim): $borradas" }
$n = 0
foreach ($t in $bim.model.tables) {
    $table = $model.Tables.Find($t.name)
    foreach ($m in $t.measures) {
        $tm = $table.Measures.Find($m.name)
        if (-not $tm) { $tm = New-Object Microsoft.AnalysisServices.Tabular.Measure; $tm.Name = $m.name; $table.Measures.Add($tm) }
        $tm.Expression = $m.expression
        $tm.FormatString = $m.formatString
        $tm.DisplayFolder = $m.displayFolder
        $tm.Description = $m.description
        $n++
    }
}
$model.SaveChanges() | Out-Null
$s.Disconnect()
"Medidas sincronizadas: $n"
