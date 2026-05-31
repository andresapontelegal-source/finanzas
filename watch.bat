@echo off
REM Vigila senales de compra validas y avisa. Para el Programador de tareas.
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

if not defined BOT_INTERVAL set BOT_INTERVAL=1d
if not defined BOT_STRATEGY set BOT_STRATEGY=ema_trend

python -m trading_bot.watch_signals --interval %BOT_INTERVAL% --strategy %BOT_STRATEGY%
if %ERRORLEVEL%==10 (
  msg * "Trading Bot: senal de COMPRA valida detectada. Revisa state\alerts.log"
)
