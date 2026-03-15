@echo off
title ALAHA Program - Instalador
color 0B
cls

echo.
echo   ___   _      ___  _   _   ___
echo  / _ \ ^| ^|    / _ \^| ^| ^| ^| / _ \
echo ^| ^(_^) ^|^| ^|   ^| ^(_^) ^|^| ^|_^| ^|^| ^(_^) ^|
echo  \__^_^_/^|^|___^| \__^_^_/ \__^_^_/  \__^_^_/
echo  ALAHA Program - Instalador Windows
echo.
echo  ==========================================
echo.

:: -----------------------------------------------
:: 1. Verificar se Python esta instalado
:: -----------------------------------------------
echo  [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERRO: Python nao encontrado no PATH.
    echo  Baixe em: https://www.python.org/downloads/
    echo  Marque "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Python %PYVER% encontrado.

:: -----------------------------------------------
:: 2. Entrar na pasta do projeto
:: -----------------------------------------------
cd /d "%~dp0\.."
echo  Diretorio: %CD%

:: -----------------------------------------------
:: 3. Criar ambiente virtual
:: -----------------------------------------------
echo.
echo  [2/6] Criando ambiente virtual...
if exist venv (
    echo  Ambiente virtual ja existe, pulando...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo  ERRO: Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

:: -----------------------------------------------
:: 4. Ativar e instalar dependencias
:: -----------------------------------------------
echo.
echo  [3/6] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo.
echo  [4/6] Instalando dependencias (pode levar alguns minutos)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ERRO: Falha ao instalar dependencias.
    echo  Verifique sua conexao com a internet.
    pause
    exit /b 1
)
echo  Dependencias instaladas com sucesso.

:: -----------------------------------------------
:: 5. Instalar Playwright (browser automation)
:: -----------------------------------------------
echo.
echo  [5/6] Instalando navegador Playwright (chromium)...
python -m playwright install chromium >nul 2>&1
if errorlevel 1 (
    echo  AVISO: Playwright nao instalado. Acoes de browser nao funcionarao.
) else (
    echo  Playwright chromium instalado.
)

:: -----------------------------------------------
:: 6. Primeira execucao
:: -----------------------------------------------
echo.
echo  [6/6] Executando ALAHA Program pela primeira vez...
echo.
echo  ==========================================
echo   Instalacao concluida com sucesso!
echo  ==========================================
echo.
echo   Para executar novamente:
echo     cd "%CD%"
echo     venv\Scripts\python.exe main.py
echo.
echo   Ou simplesmente execute este arquivo:
echo     installer\install_windows.bat
echo.
echo  Iniciando o programa...
echo.

venv\Scripts\python.exe main.py
pause
