# Record newly created console-ish processes for N seconds: pid, parent, visible flag, command line.
# Use when winwatch.ps1 shows a window but you still need to know who spawned it.
param(
    [int]$Seconds = 120,
    [string]$Log = "$env:LOCALAPPDATA\hermes\cache\scratch\procwatch.log"
)
$ErrorActionPreference = 'SilentlyContinue'
$seen = @{}
Get-CimInstance Win32_Process | ForEach-Object { $seen[$_.ProcessId] = $true }
$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end) {
    $procs = Get-CimInstance Win32_Process -Filter "Name='cmd.exe' or Name='conhost.exe' or Name='python.exe' or Name='pythonw.exe' or Name='powershell.exe' or Name='pwsh.exe' or Name='wscript.exe' or Name='cscript.exe' or Name='ffmpeg.exe'"
    foreach ($p in $procs) {
        if ($seen.ContainsKey($p.ProcessId)) { continue }
        $seen[$p.ProcessId] = $true
        $vis = 0
        try { if ((Get-Process -Id $p.ProcessId -ErrorAction Stop).MainWindowHandle -ne 0) { $vis = 1 } } catch {}
        $par = ''
        try { $par = (Get-CimInstance Win32_Process -Filter ("ProcessId=" + $p.ParentProcessId)).Name } catch {}
        $cl = ''
        if ($p.CommandLine) { $cl = $p.CommandLine; if ($cl.Length -gt 150) { $cl = $cl.Substring(0, 150) } }
        $line = '{0} | {1} pid={2} ppid={3}({4}) visible={5} | {6}' -f (Get-Date).ToString('HH:mm:ss'), $p.Name, $p.ProcessId, $p.ParentProcessId, $par, $vis, $cl
        Add-Content -Path $Log -Value $line -Encoding UTF8
        Write-Output $line
    }
    Start-Sleep -Milliseconds 200
}
Write-Output ("done: watched {0}s, log={1}" -f $Seconds, $Log)
