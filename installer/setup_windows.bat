@echo off
title ALAHA Program - Setup Completo
color 0B
cls

echo.
echo   ___   _      ___  _   _   ___
echo  / _ \ ^| ^|    / _ \^| ^| ^| ^| / _ \
echo ^| ^(_^) ^|^| ^|   ^| ^(_^) ^|^| ^|_^| ^|^| ^(_^) ^|
echo  \__^_^_/^|^|___^| \__^_^_/ \__^_^_/  \__^_^_/
echo  ALAHA Program - Setup Completo Windows
echo.
echo  ==========================================
echo.

:: -----------------------------------------------
:: 1. Verificar se Python esta instalado
:: -----------------------------------------------
echo  [1/7] Verificando Python...
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
set "ALAHA_DIR=%CD%"
echo  Diretorio: %ALAHA_DIR%

:: -----------------------------------------------
:: 3. Criar ambiente virtual
:: -----------------------------------------------
echo.
echo  [2/7] Criando ambiente virtual...
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
echo  [3/7] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo.
echo  [4/7] Instalando dependencias (pode levar alguns minutos)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ERRO: Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo  Dependencias instaladas com sucesso.

:: -----------------------------------------------
:: 5. Instalar Playwright (browser automation)
:: -----------------------------------------------
echo.
echo  [5/7] Instalando navegador Playwright (chromium)...
python -m playwright install chromium >nul 2>&1
if errorlevel 1 (
    echo  AVISO: Playwright nao instalado.
) else (
    echo  Playwright chromium instalado.
)

:: -----------------------------------------------
:: 6. Build do executavel
:: -----------------------------------------------
echo.
echo  [6/7] Gerando executavel...
python installer\build_executable.py
if errorlevel 1 (
    echo  AVISO: Build do executavel falhou.
    echo  Voce pode usar o modo Python diretamente.
) else (
    echo  Executavel gerado em: dist\ALAHAProgram.exe
)

:: -----------------------------------------------
:: 7. Criar atalhos
:: -----------------------------------------------
echo.
echo  [7/7] Criando atalhos...

:: Criar pasta de dados no AppData
if not exist "%APPDATA%\ALAHAProgram" mkdir "%APPDATA%\ALAHAProgram"

:: Criar script de inicializacao em background
echo @echo off > "%ALAHA_DIR%\run_background.bat"
echo cd /d "%ALAHA_DIR%" >> "%ALAHA_DIR%\run_background.bat"
echo start /min "" venv\Scripts\pythonw.exe main.py >> "%ALAHA_DIR%\run_background.bat"

:: Criar script de inicializacao normal
echo @echo off > "%ALAHA_DIR%\run_alaha.bat"
echo cd /d "%ALAHA_DIR%" >> "%ALAHA_DIR%\run_alaha.bat"
echo venv\Scripts\python.exe main.py >> "%ALAHA_DIR%\run_alaha.bat"
echo pause >> "%ALAHA_DIR%\run_alaha.bat"

echo.
echo  ==========================================
echo   Instalacao concluida com sucesso!
echo  ==========================================
echo.
echo   Para executar normalmente:
echo     run_alaha.bat
echo.
echo   Para executar em segundo plano:
echo     run_background.bat
echo.
echo   Executavel (se gerado):
echo     dist\ALAHAProgram.exe
echo.
echo   Para iniciar com o Windows:
echo     Marque a opcao na interface do programa
echo     ou adicione run_background.bat ao Startup
echo.
echo  ==========================================
echo.

set /p RUNNOW="Deseja iniciar o programa agora? (S/N): "
if /i "%RUNNOW%"=="S" (
    echo  Iniciando ALAHA Program...
    start "" venv\Scripts\python.exe main.py
)

pause
