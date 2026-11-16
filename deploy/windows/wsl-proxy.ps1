# 把 Windows 本机上「只监听 127.0.0.1」的端口桥接到 WSL 的 vEthernet 网卡，
# 让 WSL2（默认 NAT 模式）能用 <网关IP>:<端口> 访问 Windows 上的服务。
#
# 典型用途：代理客户端（Clash / SakuraCat 等）只监听 127.0.0.1:12450，
# WSL 里的 127.0.0.1 是 WSL 自己，必须经 Windows 侧 vEthernet(WSL) 的地址中转。
#
# 需要「以管理员身份」运行 PowerShell。
#
#   powershell -ExecutionPolicy Bypass -File C:\ProgramData\agent-platform\wsl-proxy.ps1 -Port 12450
#   powershell -ExecutionPolicy Bypass -File C:\ProgramData\agent-platform\wsl-proxy.ps1 -Port 12450 -Remove
#
# 注意：本文件必须保存为「UTF-8 with BOM」。Windows PowerShell 5.1 遇到无 BOM 的
# UTF-8 会按系统 ANSI（简中 GBK）解码，中文注释会把后面的引号一起吃坏，
# 表现为 param() 之后一片「意外的标记」语法错误。
param(
  [int]$Port = 12450,
  [string]$ConnectAddress = "127.0.0.1",
  [switch]$Remove
)

$ErrorActionPreference = "Stop"
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "请以管理员身份运行 PowerShell" }

# WSL 的 vEthernet 网卡地址（Windows 侧；对 WSL 来说就是默认网关）
function Get-WslHostIp {
  $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -like "*WSL*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -First 1 -ExpandProperty IPAddress
  if (-not $ip) { throw "找不到 vEthernet(WSL) 的 IPv4 地址：确认 WSL 正在运行（wsl -l -v）" }
  return $ip
}

$hostIp = Get-WslHostIp
Write-Host "WSL 网卡地址: $hostIp"

if ($Remove) {
  netsh interface portproxy delete v4tov4 listenaddress=$hostIp listenport=$Port 2>&1 | Out-Null
  Remove-NetFirewallRule -DisplayName "WslProxy-$Port" -ErrorAction SilentlyContinue
  netsh interface portproxy show v4tov4
  Write-Host "已清除 $hostIp`:$Port 的桥接规则"
  exit 0
}

# 上游必须真的在监听，否则桥接建了也是坏的
$upstream = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if (-not $upstream) { throw "Windows 上没有进程监听 $Port。先启动代理客户端，确认它的监听端口是 $Port" }
Write-Host "上游监听: $(($upstream | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort)" } | Sort-Object -Unique) -join ', ')"

netsh interface portproxy delete v4tov4 listenaddress=$hostIp listenport=$Port 2>&1 | Out-Null
netsh interface portproxy add v4tov4 listenaddress=$hostIp listenport=$Port connectaddress=$ConnectAddress connectport=$Port | Out-Null
Write-Host "  $hostIp`:$Port -> ${ConnectAddress}:$Port"

# 防火墙：只对本机子网放行，避免代理端口暴露到整个局域网
if (-not (Get-NetFirewallRule -DisplayName "WslProxy-$Port" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "WslProxy-$Port" -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort $Port -Profile Any -RemoteAddress LocalSubnet | Out-Null
  Write-Host "  防火墙已放行 TCP $Port（仅 LocalSubnet）"
}

netsh interface portproxy show v4tov4

$test = Test-NetConnection -ComputerName $hostIp -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
Write-Host ("从 Windows 侧自测 {0}:{1} -> {2}" -f $hostIp, $Port, $(if ($test) { "通" } else { "不通" }))
Write-Host ""
Write-Host "WSL 里验证（注意 WSL 的 127.0.0.1 是它自己，要用 $hostIp）："
Write-Host "  curl -x http://$hostIp`:$Port -s -o /dev/null -w '%{http_code}\n' https://www.google.com/generate_204"
