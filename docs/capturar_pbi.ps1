# Captura la ventana de Power BI Desktop agrandada (imagenes del informe). Uso: .\capturar_pbi.ps1 -Out img\d1.png -Wait 90
param([string]$Out, [int]$Wait = 0, [int]$W = 1720, [int]$H = 1180)
Start-Sleep $Wait
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W2 { [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f); }
"@
Add-Type -AssemblyName System.Drawing
$p = Get-Process PBIDesktop | ? { $_.MainWindowHandle -ne 0 } | select -First 1
[W2]::ShowWindow($p.MainWindowHandle, 9) | Out-Null; Start-Sleep 1
[W2]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, 0, 0, $W, $H, 0x0040) | Out-Null
Start-Sleep 20
$bmp = New-Object System.Drawing.Bitmap $W, $H; $g=[System.Drawing.Graphics]::FromImage($bmp)
$dc=$g.GetHdc(); [W2]::PrintWindow($p.MainWindowHandle, $dc, 2) | Out-Null; $g.ReleaseHdc($dc)
$bmp.Save($Out); "capturado $Out"
