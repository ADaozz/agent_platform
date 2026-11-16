# Windows 侧：把 80 / 443 / 8443 转发到 WSL2，并放开防火墙入站。
# 需要「以管理员身份」运行 PowerShell。
#
# 注意：本文件必须保存为「UTF-8 with BOM」。Windows PowerShell 5.1 遇到无 BOM 的
# UTF-8 会按系统 ANSI（简中 GBK）解码，中文注释会把后面的引号一起吃坏，
# 表现为 param() 之后一片「意外的标记」语法错误。
#
#   powershell -ExecutionPolicy Bypass -File deploy\windows\portproxy.ps1
#   powershell -ExecutionPolicy Bypass -File deploy\windows\portproxy.ps1 -Remove
#
# 说明
#  - 只适用于 NAT 模式（默认）。Windows 11 23H2+ 更推荐在 %UserProfile%\.wslconfig
#    里设 networkingMode=mirrored，镜像模式下不需要本脚本，WSL 直接占用 Windows 端口。
#  - WSL2 的 IP 每次重启会变，所以这个脚本要重复执行；可以挂到「任务计划程序」的
#    登录/开机触发器，或用下面的 -EveryMinutes 参数注册定时任务。
param(
  [string]$Distro = "",
  [switch]$Remove,
  [int[]]$Ports = @(80, 443, 8443),
  [int]$EveryMinutes = 0
)

$ErrorActionPreference = "Stop"
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "请以管理员身份运行 PowerShell" }

function Get-WslIp {
  if ($Distro) {
    $raw = (wsl -d $Distro -- hostname -I) 2>$null
  } else {
    $raw = (wsl -- hostname -I) 2>$null
  }
  if (-not $raw) { throw "拿不到 WSL IP：确认 WSL 正在运行（wsl -l -v）" }
  return ($raw.Trim() -split '\s+')[0]
}

if ($Remove) {
  foreach ($p in $Ports) {
    netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$p 2>&1 | Out-Null
    Remove-NetFirewallRule -DisplayName "AgentPlatform-$p" -ErrorAction SilentlyContinue
  }
  Write-Host "已清除 portproxy 与防火墙规则（端口：$($Ports -join ', ')）"
  exit 0
}

$wslIp = Get-WslIp
Write-Host "WSL2 IP: $wslIp"

foreach ($p in $Ports) {
  netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$p 2>&1 | Out-Null
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$p connectaddress=$wslIp connectport=$p | Out-Null
  Write-Host "  0.0.0.0:$p -> ${wslIp}:$p"

  if (-not (Get-NetFirewallRule -DisplayName "AgentPlatform-$p" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "AgentPlatform-$p" -Direction Inbound -Action Allow `
      -Protocol TCP -LocalPort $p -Profile Any | Out-Null
    Write-Host "  防火墙已放行 TCP $p"
  }
}

netsh interface portproxy show v4tov4

if ($EveryMinutes -gt 0) {
  $name = "AgentPlatform-PortProxy-Refresh"
  Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
  $psArgs = "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes)
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
    -RunLevel Highest -User "SYSTEM" | Out-Null
  Write-Host "已注册定时刷新任务 $name（每 $EveryMinutes 分钟）"
}
