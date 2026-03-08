Write-Host "Iniciando serviços do Docker..." -ForegroundColor Cyan

Start-Service com.docker.service -ErrorAction SilentlyContinue

Start-Sleep -Seconds 5

$process = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue

if (!$process) {
    Write-Host "Abrindo Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
}

Start-Sleep -Seconds 10

docker version
docker info

Write-Host "Docker iniciado." -ForegroundColor Green