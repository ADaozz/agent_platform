# 列出当前用户「个人」里可用于 TLS 客户端认证的证书
$ErrorActionPreference = 'Continue'
Write-Host "=== CurrentUser\\My (个人) ===" -ForegroundColor Cyan
$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')
$store.Open('ReadOnly')
$clientOid = '1.3.6.1.5.5.7.3.2'
$count = 0
foreach ($c in $store.Certificates) {
  if (-not $c.HasPrivateKey) { continue }
  $hasClient = $false
  if ($c.EnhancedKeyUsageList.Count -eq 0) { $hasClient = $true }
  else {
    foreach ($e in $c.EnhancedKeyUsageList) {
      if ($e.Value -eq $clientOid) { $hasClient = $true; break }
    }
  }
  $count++
  Write-Host ""
  Write-Host ("Subject : " + $c.Subject)
  Write-Host ("Issuer  : " + $c.Issuer)
  Write-Host ("NotAfter: " + $c.NotAfter)
  Write-Host ("Thumb   : " + $c.Thumbprint)
  Write-Host ("ClientAuth EKU: " + $hasClient)
}
Write-Host ""
Write-Host ("有私钥的个人证书数量: $count") -ForegroundColor Yellow
$store.Close()

Write-Host ""
Write-Host "=== CurrentUser\\Root 里是否有 personalDemo Root CA ===" -ForegroundColor Cyan
$root = New-Object System.Security.Cryptography.X509Certificates.X509Store('Root','CurrentUser')
$root.Open('ReadOnly')
$root.Certificates | Where-Object { $_.Subject -like '*personalDemo*' -or $_.Subject -like '*Root CA*' } |
  ForEach-Object { Write-Host $_.Subject }
$root.Close()

Write-Host ""
Write-Host "=== CurrentUser\\CA (中间) 里是否有 Intermediate ===" -ForegroundColor Cyan
$ca = New-Object System.Security.Cryptography.X509Certificates.X509Store('CA','CurrentUser')
$ca.Open('ReadOnly')
$ca.Certificates | Where-Object { $_.Subject -like '*personalDemo*' -or $_.Subject -like '*Intermediate*' } |
  ForEach-Object { Write-Host $_.Subject }
$ca.Close()
