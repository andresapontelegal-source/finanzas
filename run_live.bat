@echo off
REM Ejecuta UN ciclo del bot de paper trading en vivo (simulado) y guarda el
REM resultado en state\live_*. Pensado para el Programador de tareas de Windows.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

REM Configuracion del bot (editable aqui).
if not defined BOT_SYMBOL   set BOT_SYMBOL=BTCUSDT
if not defined BOT_INTERVAL set BOT_INTERVAL=1h
if not defined BOT_STRATEGY set BOT_STRATEGY=ema_trend
if not defined BOT_PARAMS   set BOT_PARAMS={"fast":30,"slow":50,"trend":250}
if not defined BOT_CASH     set BOT_CASH=10000
if not defined BOT_FEE      set BOT_FEE=0.001
if not defined BOT_SLIPPAGE set BOT_SLIPPAGE=0.0005

python -m trading_bot.live_runner
