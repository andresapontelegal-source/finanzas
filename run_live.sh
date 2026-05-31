#!/usr/bin/env bash
# Ejecuta UN ciclo del bot de paper trading en vivo (simulado) y guarda el
# resultado en state/live_*. Pensado para llamarse desde cron cada hora.
#
# Ejemplo de linea de cron (cada hora, al minuto 5):
#   5 * * * * /ruta/al/proyecto/run_live.sh >> /ruta/al/proyecto/state/cron.log 2>&1
set -e

cd "$(dirname "$0")"

# Usa el entorno virtual si existe.
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Configuracion del bot (editable aqui).
export BOT_SYMBOL="${BOT_SYMBOL:-BTCUSDT}"
export BOT_INTERVAL="${BOT_INTERVAL:-1d}"
export BOT_STRATEGY="${BOT_STRATEGY:-ema_trend}"
export BOT_PARAMS="${BOT_PARAMS:-{\"fast\":10,\"slow\":100,\"trend\":250}}"
export BOT_CASH="${BOT_CASH:-10000}"
export BOT_FEE="${BOT_FEE:-0.001}"
export BOT_SLIPPAGE="${BOT_SLIPPAGE:-0.0005}"

python -m trading_bot.live_runner
