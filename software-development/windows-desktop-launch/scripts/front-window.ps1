# Raise a native Windows window: unlock the foreground rule, then bring it to front.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File front-window.ps1 -ProcessId 1234
#        powershell -NoProfile -ExecutionPolicy Bypass -File front-window.ps1 -TitleLike "Visual Studio Code"
# Success is GetForegroundWindow() == target hwnd — never the call's own return value.
# NOTE: never rename $ProcessId to $Pid — that collides with PowerShell's read-only automatic $PID.
param(
  [int]$ProcessId,
  [string]$TitleLike
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class FgWin {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern void SwitchToThisWindow(IntPtr h, bool alt);
  [DllImport("user32.dll")] public static extern IntPtr SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern void keybd_event(byte b, byte s, uint f, IntPtr e);
}
"@

if ($ProcessId -gt 0) {
  $proc = Get-Process -Id $ProcessId -ErrorAction Stop
} elseif ($TitleLike) {
  $proc = Get-Process | Where-Object { $_.MainWindowTitle -ne '' -and $_.MainWindowTitle -like "*$TitleLike*" } | Select-Object -First 1
  if (-not $proc) { Write-Output "no window matching '$TitleLike'"; exit 1 }
} else {
  Write-Output "pass -ProcessId or -TitleLike"; exit 1
}

$h = $proc.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { Write-Output "process $($proc.Id) has no main window"; exit 1 }

# ALT press/release unlocks the foreground rule for this call, then the raise sequence.
[FgWin]::keybd_event(0x12, 0, 0, [IntPtr]::Zero)
[FgWin]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)

$fg = [FgWin]::GetForegroundWindow()
$fgThread = [FgWin]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
$myThread = [FgWin]::GetCurrentThreadId()
[void][FgWin]::AttachThreadInput($myThread, $fgThread, $true)
[void][FgWin]::ShowWindow($h, 9)                     # SW_RESTORE
[void][FgWin]::BringWindowToTop($h)
[FgWin]::SwitchToThisWindow($h, $true)
# SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
[void][FgWin]::SetWindowPos($h, [IntPtr]::Zero, 0, 0, 0, 0, 0x0001 -bor 0x0002 -bor 0x0040)
[void][FgWin]::SetForegroundWindow($h)
[void][FgWin]::AttachThreadInput($myThread, $fgThread, $false)

Start-Sleep -Milliseconds 800
$now = [FgWin]::GetForegroundWindow()
Write-Output "target=$h fg_now=$now success=$($now -eq $h) title=$($proc.MainWindowTitle)"
