# Sincroniza SOLO las medidas del Model.bim con el cubo ya procesado (sin reprocesar datos), via TOM.
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
