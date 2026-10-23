# 「老是弹命令窗口」排查手册（Windows）

用户说「打游戏/干活的时候老弹黑窗」时，九成是本机自己的计划任务或常驻看护在开控制台。按下面的顺序走，别先怀疑别的会话、客户端或游戏本身。

## 1. 先看计划任务，对齐时间

```powershell
# 非 Microsoft 的任务，带上次/下次运行时间
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft*' } | ForEach-Object {
  $i = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath -ErrorAction SilentlyContinue
  '{0,-32} state={1,-8} last={2:HH:mm:ss} next={3:HH:mm:ss} result={4}' -f $_.TaskName, $_.State, $i.LastRunTime, $i.NextRunTime, $i.LastTaskResult
}

# 单个任务的动作 + 重复间隔
$t = Get-ScheduledTask -TaskName HermesWatchdog
$t.Actions | Format-List Execute, Arguments
$t.Triggers[0].Repetition | Format-List Interval, Duration
$t.Principal | Format-List LogonType
```

判读：

- 动作是 `cmd.exe` / 某个 `.cmd` / `.bat`，`LogonType=Interactive` → **每次触发都会开控制台**。
- 弹窗节律 = Repetition（`PT5M` = 每 5 分钟一次）。
- 任务的 `Settings.Hidden` / `Settings.Hidden` 只是任务列表里的可见性，**不隐藏控制台窗口**。`Run whether user is logged on or not` 确实不开窗，但要存用户密码，不优先。

## 2. 抓现场：只盯可见的控制台窗口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\32672\AppData\Local\hermes\skills\devops\windows-local-app-setup\scripts\winwatch.ps1" -Seconds 400
```

它用 `EnumWindows` + `IsWindowVisible` 只记录三类窗口：`ConsoleWindowClass`（传统 conhost）、`PseudoConsoleWindow`（ConPTY / Windows Terminal 里的伪控制台）、`CASCADIA_HOSTING_WINDOW_CLASS`（Windows Terminal 宿主）。启动时已有的窗口当作基线不报，只报新出现的。

为什么不用 `Get-Process ... MainWindowHandle`：隐藏控制台的进程同样返回 0，而真正可见的窗口常挂在 conhost.exe / WindowsTerminal.exe 上，看错进程就永远找不到元凶。

## 3. 还定位不到：抓进程创建链

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "...\scripts\procwatch.ps1" -Seconds 120
```

输出 `pid/ppid/父进程名/visible/命令行`，能看到「svchost(Task Scheduler) → cmd.exe → powershell.exe」这种链，直接锁定任务。

## 4. 排除自家会话（别冤枉客户端）

- Hermes 自己的终端工具用 `windows_hide_flags()`（`CREATE_NO_WINDOW`）起 bash，客户端会话跑命令**不会**弹窗。
- 客户端是不是在干活，看事实：`logs/qq-bridge-client1.log`、`logs/qq-bridge-client2.log`，以及它自己的 NapCat 端口（3011 / 3013）。桥接掉线时日志会刷 `[ws] 断开（[WinError 10061] ...）`，这种时候它连消息都收不到，不可能在点歌/画图。
- 真在生图会有明显的 GPU 占用：`nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv`。

## 5. 修法：任务动作换成隐藏启动器

1) 建一个纯 ASCII 的启动器（放 `%LOCALAPPDATA%\hermes\scripts\`，别用 write_file 写中文）：

```vb
' Gateway watchdog launcher - no console window. ASCII only.
Option Explicit
Dim sh, fso, cmd
cmd = "C:\Users\32672\AppData\Local\hermes\scripts\gateway-watch.cmd"
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(cmd) Then WScript.Quit 0
Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c """ & cmd & """", 0, False
```

2) 换任务动作：

```powershell
$a = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '"C:\Users\32672\AppData\Local\hermes\scripts\gateway-watch-hidden.vbs"'
Set-ScheduledTask -TaskName HermesWatchdog -Action $a
```

（只换 Action，触发器/重复间隔/主体设置原样保留。）

## 6. 验证（两个周期才算数）

```powershell
Start-ScheduledTask -TaskName HermesWatchdog; Start-Sleep 8
(Get-ScheduledTaskInfo -TaskName HermesWatchdog) | Select LastRunTime, LastTaskResult   # 期望 0
```

然后 `winwatch.ps1` 覆盖**下一次自然触发**（看 `NextRunTime`），日志应完全没有新窗口。顺带确认原来的工作还做了（例如 watchdog 真去探了端口），别把任务改成形式上的 0。

## 7. 坑

- **写坏的启动 VBS**：`C:\Users?72` 这种是 `\U`/`\3` 被当成转义吃掉了。`read_file` 报 `Binary file` 就是野字节的信号；用 `printf '%s\r\n' ...`（反斜杠双写）重写，`od -c` 验一遍全 ASCII。这类文件只在开机执行，坏着也看不出来。
- **别在任务动作里写带空格路径不加引号**：`Argument` 里整段路径要 `"..."`。
- **重复的看护进程**：`Get-CimInstance Win32_Process` 按命令行过滤，父/子两个 python 可能是同一个脚本的 re-exec（`uptime-alert.py` 就这样），先看 ppid 再判断是不是重复启动。
- **改 scripts/ 目录**：本机 `scripts/` 是两个 Hermes 会话共管，先 `python scripts/agentlock.py acquire <file> --owner 主控 --reason ...`，用 patch 改，改完 commit + 在 `PROGRESS.md` 顶上加一行。
