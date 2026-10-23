# Watch for VISIBLE console windows for N seconds. Prints and logs only windows
# that appear after the baseline snapshot, so long-lived terminals stay quiet.
param(
    [int]$Seconds = 400,
    [string]$Log = "$env:LOCALAPPDATA\hermes\cache\scratch\winwatch.log"
)
$ErrorActionPreference = 'SilentlyContinue'
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class WinWatch {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
$seen = @{}
$primed = $false
$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end) {
    $script:found = New-Object System.Collections.ArrayList
    $cb = [WinWatch+EnumProc]{
        param($h, $l)
        if ([WinWatch]::IsWindowVisible($h)) {
            $cls = New-Object System.Text.StringBuilder 256
            [void][WinWatch]::GetClassName($h, $cls, 256)
            if ($cls.ToString() -match 'ConsoleWindowClass|PseudoConsoleWindow|CASCADIA_HOSTING') {
                $title = New-Object System.Text.StringBuilder 256
                [void][WinWatch]::GetWindowText($h, $title, 256)
                [uint32]$procId = 0
                [void][WinWatch]::GetWindowThreadProcessId($h, [ref]$procId)
                [void]$script:found.Add(("{0}|{1}|{2}" -f $cls.ToString(), $procId, $title.ToString()))
            }
        }
        return $true
    }
    [void][WinWatch]::EnumWindows($cb, [IntPtr]::Zero)
    foreach ($f in $script:found) {
        if (-not $seen.ContainsKey($f)) {
            $seen[$f] = $true
            if ($primed) {
                $p = $f.Split('|')
                $pname = ''
                try { $pname = (Get-Process -Id ([int]$p[1]) -ErrorAction Stop).ProcessName } catch {}
                $line = ((Get-Date).ToString('HH:mm:ss') + ' | ' + $f + ' | ' + $pname)
                Add-Content -Path $Log -Value $line -Encoding UTF8
                Write-Output $line
            }
        }
    }
    $primed = $true
    Start-Sleep -Milliseconds 150
}
Write-Output ("done: watched {0}s, log={1}" -f $Seconds, $Log)
