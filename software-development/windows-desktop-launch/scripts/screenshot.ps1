# Capture the virtual screen (all monitors) to a PNG and print the path.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File screenshot.ps1 [-Out C:\path\shot.png]
# Deliver with MEDIA:<printed path>. Hash two captures (md5sum) to prove whether the screen changed.
param(
  [string]$Out = "$env:TEMP\screen_$(Get-Date -Format yyyyMMdd_HHmmss).png"
)

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output (Resolve-Path $Out).Path
