#!/usr/bin/env bash
# Vigila senales de compra validas y avisa. Pensado para cron (1/dia).
# Si encuentra una alerta, la registra en state/alerts.log y (si tienes
# 'notify-send' o 'osascript') lanza una notificacion de escritorio.
#
# Ejemplo de cron (cada dia a las 00:15 UTC):
#   15 0 * * * /ruta/al/proyecto/watch.sh >> /ruta/al/proyecto/state/watch.log 2>&1
set -e

cd "$(dirname "$0")"
if [ -d ".venv" ]; then source .venv/bin/activate; fi

export BOT_INTERVAL="${BOT_INTERVAL:-1d}"
export BOT_STRATEGY="${BOT_STRATEGY:-ema_trend}"

set +e
OUTPUT=$(python -m trading_bot.watch_signals --interval "$BOT_INTERVAL" --strategy "$BOT_STRATEGY")
CODE=$?
set -e
echo "$OUTPUT"

# Codigo 10 = hay alerta de compra valida.
if [ "$CODE" -eq 10 ]; then
  MSG="Bot trading: senal de COMPRA valida detectada. Revisa state/alerts.log"
  command -v notify-send >/dev/null 2>&1 && notify-send "Trading Bot" "$MSG" || true
  command -v osascript   >/dev/null 2>&1 && osascript -e "display notification \"$MSG\" with title \"Trading Bot\"" || true
fi
