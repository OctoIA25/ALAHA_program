# ALAHA Program - Quick Install (PowerShell)
# Execute: irm https://raw.githubusercontent.com/.../quick_install.ps1 | iex
# Ou localmente: .\installer\quick_install.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ___   _      ___  _   _   ___" -ForegroundColor Cyan
Write-Host " / _ \ | |    / _ \| | | | / _ \" -ForegroundColor Cyan
Write-Host "| (_) || |   | (_) || |_| || (_) |" -ForegroundColor Cyan
Write-Host " \___/ ||___| \___/  \___/  \___/" -ForegroundColor Cyan
Write-Host " ALAHA Program - Quick Install" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
Write-Host "[1/4] Verificando Python..." -ForegroundColor Yellow
try {
    $pyver = python --version 2>&1
    Write-Host "  $pyver encontrado." -ForegroundColor Green
} catch {
    Write-Host "  ERRO: Python nao encontrado." -ForegroundColor Red
    Write-Host "  Baixe em: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Ir para a pasta do projeto
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath

Write-Host "[2/4] Criando ambiente virtual..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
}
Write-Host "  Ambiente pronto." -ForegroundColor Green

Write-Host "[3/4] Instalando dependencias..." -ForegroundColor Yellow
& ".\venv\Scripts\pip.exe" install --upgrade pip -q
& ".\venv\Scripts\pip.exe" install -r requirements.txt -q
Write-Host "  Dependencias instaladas." -ForegroundColor Green

Write-Host "[4/4] Instalando Playwright..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" -m playwright install chromium 2>$null
Write-Host "  Playwright instalado." -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " Instalacao concluida!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para executar:" -ForegroundColor White
Write-Host "  .\venv\Scripts\python.exe main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para executar em segundo plano:" -ForegroundColor White
Write-Host "  Start-Process -WindowStyle Hidden .\venv\Scripts\pythonw.exe main.py" -ForegroundColor Cyan
Write-Host ""

$start = Read-Host "Iniciar agora? (S/N)"
if ($start -eq "S" -or $start -eq "s") {
    Write-Host "Iniciando ALAHA Program..." -ForegroundColor Green
    & ".\venv\Scripts\python.exe" main.py
}
