# SCRIPT PARA INICIAR EL SERVIDOR DEL RESTAURANTE (MODO RED LOCAL)
# Inicia el servidor Node.js y muestra la IP para conectar otros dispositivos

$dir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if ([string]::IsNullOrEmpty($dir)) { $dir = Get-Location }
Set-Location $dir

# Obtener la IP local de la PC
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPv4Address -notlike "169.254.*" }).IPv4Address | Select-Object -First 1

Write-Host "--------------------------------------------------" -ForegroundColor Gray
Write-Host ">>> Iniciando Servidor del Restaurante..." -ForegroundColor Cyan
Write-Host ">>> Tu IP local es: $localIP" -ForegroundColor Yellow
Write-Host "--------------------------------------------------" -ForegroundColor Gray

# 1. Iniciar el servidor Node.js en una nueva ventana
Start-Process "node" "server.js" -WindowStyle Normal

# 2. Esperar un momento a que el servidor levante
Start-Sleep -Seconds 2

# 3. Abrir la interfaz principal en Chrome usando la IP (para probar conectividad)
Write-Host ">>> Abriendo Interfaz en: http://$localIP:3000" -ForegroundColor Green
Start-Process "chrome.exe" "http://$localIP:3000"

Write-Host "`n>>> Listo! Ahora puedes entrar desde tu Tablet de Cocina usando:" -ForegroundColor White
Write-Host ">>> http://$localIP:3000/kds_demo.html" -ForegroundColor Yellow
