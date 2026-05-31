#!/usr/bin/env bash
# Instala el bot como LaunchAgent en TU Mac.
# Arranca al iniciar sesion y corre 1 vez al dia.
#
# Uso:    ./autostart/install_mac.sh
# Quitar: launchctl unload ~/Library/LaunchAgents/com.paperbot.*.plist
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$AGENTS_DIR"

echo ">> Proyecto: $PROJECT_DIR"

if [ ! -d "$PROJECT_DIR/.venv" ]; then
  echo ">> Creando entorno virtual..."
  python3 -m venv "$PROJECT_DIR/.venv"
fi
"$PROJECT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"
chmod +x "$PROJECT_DIR/run_live.sh" "$PROJECT_DIR/watch.sh"

# --- LaunchAgent: ciclo de trading diario (00:10) ---
cat > "$AGENTS_DIR/com.paperbot.trade.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.paperbot.trade</string>
  <key>ProgramArguments</key>
  <array><string>$PROJECT_DIR/run_live.sh</string></array>
  <key>WorkingDirectory</key><string>$PROJECT_DIR</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>10</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$PROJECT_DIR/state/trade.log</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/state/trade.log</string>
</dict>
</plist>
EOF

# --- LaunchAgent: vigilante de senales (00:15) ---
cat > "$AGENTS_DIR/com.paperbot.watch.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.paperbot.watch</string>
  <key>ProgramArguments</key>
  <array><string>$PROJECT_DIR/watch.sh</string></array>
  <key>WorkingDirectory</key><string>$PROJECT_DIR</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>15</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$PROJECT_DIR/state/watch.log</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR/state/watch.log</string>
</dict>
</plist>
EOF

launchctl unload "$AGENTS_DIR/com.paperbot.trade.plist" 2>/dev/null || true
launchctl unload "$AGENTS_DIR/com.paperbot.watch.plist" 2>/dev/null || true
launchctl load "$AGENTS_DIR/com.paperbot.trade.plist"
launchctl load "$AGENTS_DIR/com.paperbot.watch.plist"

echo ""
echo "================================================================"
echo " Bot instalado como LaunchAgent. Arranca al iniciar sesion y"
echo " corre 1x/dia (y al cargar)."
echo ""
echo " Ver:        launchctl list | grep paperbot"
echo " Logs:       cat state/trade.log  /  cat state/watch.log"
echo " Desinstalar: launchctl unload ~/Library/LaunchAgents/com.paperbot.*.plist"
echo "================================================================"
