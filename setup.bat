@echo off
REM Configuracion inicial del bot de paper trading (Windows).
REM Crea un entorno virtual e instala las dependencias.

cd /d "%~dp0"

echo ^>^> Creando entorno virtual (.venv)...
python -m venv .venv
call .venv\Scripts\activate.bat

echo ^>^> Instalando dependencias...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo ^>^> Verificando con un backtest de demostracion...
python run_bot.py backtest --symbol BTCUSDT --interval 1d

echo.
echo ================================================================
echo  Listo. Para activar el entorno en el futuro:  .venv\Scripts\activate.bat
echo.
echo  Comandos utiles:
echo    python run_bot.py backtest --symbol BTCUSDT --interval 1d --plot
echo    python run_bot.py optimize --symbol ETHUSDT --interval 1d
echo    python run_bot.py paper --symbol BTCUSDT --interval 1h --iterations 10 --poll 60
echo.
echo  Para un ciclo en vivo:  run_live.bat
echo  Programalo con el Programador de tareas (ver README_BOT.md).
echo ================================================================
pause
