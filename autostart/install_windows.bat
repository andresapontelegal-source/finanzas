@echo off
REM Instala el bot como tarea programada en TU PC Windows.
REM Arranca al iniciar sesion y corre 1 vez al dia.
REM
REM Ejecutar haciendo doble clic (puede pedir permisos).
REM Desinstalar:  schtasks /delete /tn PaperBotTrade /f  y  /tn PaperBotWatch /f

cd /d "%~dp0\.."
set PROJECT_DIR=%CD%
echo ^>^> Proyecto: %PROJECT_DIR%

REM Crear entorno virtual e instalar dependencias.
if not exist ".venv\Scripts\python.exe" (
  echo ^>^> Creando entorno virtual...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

REM --- Tarea 1: ciclo de trading (al iniciar sesion + diario 00:10) ---
schtasks /create /tn "PaperBotTrade" /tr "\"%PROJECT_DIR%\run_live.bat\"" /sc daily /st 00:10 /f
schtasks /create /tn "PaperBotTradeBoot" /tr "\"%PROJECT_DIR%\run_live.bat\"" /sc onlogon /f

REM --- Tarea 2: vigilante de senales (al iniciar sesion + diario 00:15) ---
schtasks /create /tn "PaperBotWatch" /tr "\"%PROJECT_DIR%\watch.bat\"" /sc daily /st 00:15 /f
schtasks /create /tn "PaperBotWatchBoot" /tr "\"%PROJECT_DIR%\watch.bat\"" /sc onlogon /f

echo.
echo ================================================================
echo  Bot instalado como tareas programadas.
echo  Arranca al iniciar sesion y corre 1x/dia.
echo.
echo  Ver tareas:   schtasks /query /tn PaperBotTrade
echo  Forzar ahora: schtasks /run /tn PaperBotTrade
echo  Desinstalar:  schtasks /delete /tn PaperBotTrade /f
echo                schtasks /delete /tn PaperBotWatch /f
echo                schtasks /delete /tn PaperBotTradeBoot /f
echo                schtasks /delete /tn PaperBotWatchBoot /f
echo ================================================================
pause
