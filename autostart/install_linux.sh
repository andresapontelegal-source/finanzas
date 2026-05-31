#!/usr/bin/env bash
# Instala el bot como servicio de usuario systemd en TU PC Linux.
# Crea un timer que ejecuta un ciclo diario y arranca solo al reiniciar.
#
# Uso:   ./autostart/install_linux.sh
# Quitar: systemctl --user disable --now paper-bot.timer paper-bot-watch.timer
set -e

# Carpeta raiz del proyecto (un nivel arriba de este script).
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

echo ">> Proyecto: $PROJECT_DIR"

# Asegurar entorno virtual y dependencias.
if [ ! -d "$PROJECT_DIR/.venv" ]; then
  echo ">> Creando entorno virtual..."
  python3 -m venv "$PROJECT_DIR/.venv"
fi
"$PROJECT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

# --- Servicio: un ciclo de trading ---
cat > "$UNIT_DIR/paper-bot.service" <<EOF
[Unit]
Description=Paper Trading Bot (un ciclo, simulado)
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/run_live.sh
EOF

# --- Timer: ejecutar 1 vez al dia y al arrancar ---
cat > "$UNIT_DIR/paper-bot.timer" <<EOF
[Unit]
Description=Ejecuta el Paper Trading Bot diariamente

[Timer]
OnBootSec=2min
OnCalendar=*-*-* 00:10:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# --- Servicio + timer del vigilante de senales ---
cat > "$UNIT_DIR/paper-bot-watch.service" <<EOF
[Unit]
Description=Vigilante de senales del Paper Trading Bot
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/watch.sh
EOF

cat > "$UNIT_DIR/paper-bot-watch.timer" <<EOF
[Unit]
Description=Vigila senales de compra validas diariamente

[Timer]
OnBootSec=3min
OnCalendar=*-*-* 00:15:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

chmod +x "$PROJECT_DIR/run_live.sh" "$PROJECT_DIR/watch.sh"

systemctl --user daemon-reload
systemctl --user enable --now paper-bot.timer
systemctl --user enable --now paper-bot-watch.timer

# Permitir que los timers corran aunque no haya sesion iniciada (al reiniciar).
loginctl enable-linger "$USER" 2>/dev/null || \
  echo "   (Nota: ejecuta 'sudo loginctl enable-linger $USER' para que corra sin login)"

echo ""
echo "================================================================"
echo " Bot instalado como servicio systemd de usuario."
echo " Arranca solo al reiniciar y corre 1x/dia."
echo ""
echo " Ver estado:   systemctl --user list-timers 'paper-bot*'"
echo " Ver logs:     journalctl --user -u paper-bot.service -n 50"
echo " Forzar ahora: systemctl --user start paper-bot.service"
echo " Desinstalar:  systemctl --user disable --now paper-bot.timer paper-bot-watch.timer"
echo "================================================================"
