#!/usr/bin/env bash
# Configuracion inicial del bot de paper trading (Linux / macOS).
# Crea un entorno virtual e instala las dependencias.
set -e

cd "$(dirname "$0")"

echo ">> Creando entorno virtual (.venv)..."
python3 -m venv .venv
source .venv/bin/activate

echo ">> Instalando dependencias..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ">> Verificando con un backtest de demostracion..."
python run_bot.py backtest --symbol BTCUSDT --interval 1d

echo ""
echo "================================================================"
echo " Listo. Para activar el entorno en el futuro:  source .venv/bin/activate"
echo ""
echo " Comandos utiles:"
echo "   python run_bot.py backtest --symbol BTCUSDT --interval 1d --plot"
echo "   python run_bot.py optimize --symbol ETHUSDT --interval 1d"
echo "   python run_bot.py paper --symbol BTCUSDT --interval 1h --iterations 10 --poll 60"
echo ""
echo " Para dejarlo corriendo continuo cada hora, usa:  ./run_live.sh"
echo " y programalo con cron (ver README_BOT.md)."
echo "================================================================"
