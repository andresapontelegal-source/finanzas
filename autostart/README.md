# 🔌 Arranque automático en tu PC

Estos instaladores dejan el bot corriendo **en tu propia computadora**, de forma
que **arranca solo al reiniciar** y ejecuta un ciclo diario (más el vigilante de
señales). Es 100% simulado: dinero virtual.

> ⚠️ Debes ejecutar esto **en tu PC**, no en un contenedor temporal. El bot
> estará activo **mientras tu computadora esté encendida**. Si la apagas, el bot
> se pausa y vuelve a arrancar solo cuando la enciendas de nuevo.

## Linux (systemd)

```bash
cd <carpeta-del-proyecto>
./autostart/install_linux.sh
```

Crea servicios de usuario systemd + timers. Arranca al reiniciar (gracias a
`enable-linger`). Comprobar:
```bash
systemctl --user list-timers 'paper-bot*'
journalctl --user -u paper-bot.service -n 50
```

## macOS (LaunchAgent)

```bash
cd <carpeta-del-proyecto>
./autostart/install_mac.sh
```

Crea LaunchAgents que arrancan al iniciar sesión y corren a diario. Comprobar:
```bash
launchctl list | grep paperbot
cat state/trade.log
```

## Windows (Tarea programada)

Doble clic en `autostart\install_windows.bat` (o ejecútalo desde cmd). Crea
tareas que arrancan al iniciar sesión y corren a diario. Comprobar:
```bat
schtasks /query /tn PaperBotTrade
schtasks /run /tn PaperBotTrade
```

## ¿Qué hace cada ciclo?

1. `run_live.sh` / `run_live.bat` → ejecuta un ciclo de trading (BTC diario) y
   actualiza `state/live_*`.
2. `watch.sh` / `watch.bat` → escanea pares y avisa si hay señal de compra
   **válida** (con buen historial), registrando en `state/alerts.log`.

## Desinstalar

- **Linux:** `systemctl --user disable --now paper-bot.timer paper-bot-watch.timer`
- **macOS:** `launchctl unload ~/Library/LaunchAgents/com.paperbot.*.plist`
- **Windows:** `schtasks /delete /tn PaperBotTrade /f` (y las demás `PaperBot*`)

## Nota sobre "estar activo 24/7"

Estos métodos mantienen el bot activo **siempre que tu PC esté encendido**. Para
trading diario es suficiente (solo necesita correr 1×/día). Si quieres actividad
real 24/7 sin depender de tu PC, necesitarías un servidor en la nube siempre
encendido (pídemelo y te guío).
