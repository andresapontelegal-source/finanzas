# 🤖 Bot de Paper Trading (simulado)

Bot de trading **100% en papel (paper trading)**: opera con dinero **virtual**
sobre datos de mercado **reales** de Binance. Nunca se conecta a una cuenta
real, nunca usa claves de API y **nunca envía órdenes reales**. Es una
herramienta educativa y de investigación de estrategias.

## Resultado del backtest (configuración por defecto)

Estrategia de seguimiento de tendencia con EMAs sobre **BTCUSDT diario**
(sep-2023 → may-2026, ~2,7 años), comisiones 0,1% y slippage 5 bps:

| Métrica            | Valor          |
|--------------------|----------------|
| Capital inicial    | $10.000,00     |
| **Capital final**  | **$28.093,33** |
| **Retorno total**  | **+180,93%**   |
| CAGR               | +45,79%        |
| Max drawdown       | −28,77%        |
| Sharpe (anual)     | 1,22           |
| Operaciones        | 16             |
| Win rate           | 56,2%          |
| Profit factor      | 2,46           |

> El bot **gana** dinero (simulado) en el backtest, mantiene un buen ratio
> riesgo/beneficio (profit factor 2,46) y un drawdown muy inferior al de
> comprar y mantener, quedándose en efectivo durante las tendencias bajistas.

### Resultados en otros pares (1d, parámetros optimizados)

| Par      | Retorno bot | Buy & Hold | Comentario                         |
|----------|-------------|------------|------------------------------------|
| BTCUSDT  | +180,9%     | +182,6%    | Mismo retorno, mucho menos riesgo  |
| ETHUSDT  | **+70,1%**  | +22,7%     | **Bate al mercado 3×**             |
| SOLUSDT  | +295,0%     | +318,3%    | Gran retorno, menor drawdown       |
| BNBUSDT  | +189,2%     | +199,2%    | Similar al mercado, menos riesgo   |

En todos los pares el bot es **rentable**; en ETH **supera claramente** a comprar
y mantener. Su ventaja principal es protegerse en las caídas (se va a efectivo).

## Instalación

```bash
pip install -r requirements.txt   # pandas, numpy
```

## Uso

```bash
# 1) Backtest sobre datos históricos reales (config por defecto, rentable)
python run_bot.py backtest --symbol BTCUSDT --interval 1d
python run_bot.py backtest --symbol BTCUSDT --interval 1d --plot   # + gráfico PNG

# 2) Optimizar parámetros (búsqueda en rejilla por retorno total)
python run_bot.py optimize --symbol BTCUSDT --interval 1d
python run_bot.py optimize --symbol ETHUSDT --interval 4h --strategy rsi_mr

# 3) Paper trading EN VIVO (simulado): consulta precios reales y opera virtual
python run_bot.py paper --symbol BTCUSDT --interval 1h --iterations 100 --poll 60
```

### Parámetros principales

| Flag           | Descripción                              | Por defecto |
|----------------|------------------------------------------|-------------|
| `--symbol`     | Par de Binance                           | BTCUSDT     |
| `--interval`   | Timeframe (1m,5m,1h,4h,1d,…)             | 1h          |
| `--limit`      | Nº de velas históricas                   | 1000        |
| `--strategy`   | `ema_trend` o `rsi_mr`                    | ema_trend   |
| `--params`     | JSON, ej. `'{"fast":10,"slow":100}'`     | (defaults)  |
| `--cash`       | Capital simulado inicial                 | 10000       |
| `--fee`        | Comisión por operación                   | 0.001       |
| `--slippage`   | Deslizamiento por operación              | 0.0005      |
| `--stop-atr`   | Stop-loss en múltiplos de ATR            | 3.0         |
| `--take-atr`   | Take-profit en múltiplos de ATR          | 6.0         |
| `--poll`       | (paper) segundos entre ciclos            | 60          |
| `--iterations` | (paper) nº de ciclos                     | infinito    |

## Arquitectura

```
trading_bot/
├── data.py        # Cliente de datos de Binance (data-api.binance.vision)
├── strategy.py    # Indicadores (EMA, RSI, ATR) y estrategias
├── portfolio.py   # Broker/cartera simulados con comisiones y slippage
├── engine.py      # Motor de backtest + bucle de paper trading en vivo
├── plotting.py    # Gráficos PNG (precio + capital + drawdown)
└── cli.py         # Interfaz de línea de comandos
run_bot.py         # Punto de entrada
```

### Estrategias incluidas

- **`ema_trend`** — Seguimiento de tendencia: largo cuando la EMA rápida está
  por encima de la lenta y el precio sobre la EMA de tendencia. Captura grandes
  movimientos alcistas y se va a efectivo en mercados bajistas.
- **`rsi_mr`** — Reversión a la media: compra sobreventa (RSI bajo) solo dentro
  de una tendencia alcista, y vende al recuperarse.

### Gestión de riesgo

Cada posición lleva **stop-loss y take-profit basados en ATR** (volatilidad),
además de la salida por señal de la estrategia. Esto limita las pérdidas por
operación y protege el capital.

## 💻 Correrlo continuo en tu PC (recomendado)

La forma más fiable de dejarlo operando días es en tu propia máquina (el cron
de GitHub es poco fiable). Pasos:

### 1. Configuración inicial (una vez)

**Linux / macOS:**
```bash
chmod +x setup.sh run_live.sh
./setup.sh
```

**Windows:**
```bat
setup.bat
```

Esto crea un entorno virtual `.venv`, instala dependencias y corre un backtest
de prueba.

### 2. (Opcional) Sembrar el diario con el histórico

Para tener resultados que revisar de inmediato (sin esperar días), reconstruye
el diario en vivo recorriendo todo el histórico:

```bash
BOT_INTERVAL=1d BOT_PARAMS='{"fast":10,"slow":100,"trend":250}' \
  python -m trading_bot.live_runner --backfill
```

Esto deja `state/live_*` con el historial completo (operaciones + equity) y el
estado listo para que el modo en vivo continúe desde el último punto.

### 3. Probar un ciclo en vivo (simulado)

```bash
./run_live.sh          # Linux/macOS
run_live.bat           # Windows
```

Cada ejecución actualiza la cartera simulada y guarda el diario en `state/`:
- `state/live_journal.csv` — operaciones simuladas
- `state/live_equity.csv` — equity por ciclo
- `state/live_state.json` — estado actual (efectivo, posición, P&L)

### 3. Dejarlo corriendo automáticamente cada hora

**Linux / macOS (cron):** ejecuta `crontab -e` y añade (ajusta la ruta):
```cron
5 * * * * /ruta/al/proyecto/run_live.sh >> /ruta/al/proyecto/state/cron.log 2>&1
```

**Windows (Programador de tareas):**
1. Abre "Programador de tareas" → "Crear tarea básica".
2. Desencadenador: diariamente, repetir cada 1 hora.
3. Acción: "Iniciar un programa" → selecciona `run_live.bat`.

A partir de ahí, vuelve cuando quieras y revisa `state/live_equity.csv` para ver
todo lo que hizo el bot.

> La configuración (símbolo, intervalo, estrategia) se edita en las variables
> `BOT_*` dentro de `run_live.sh` / `run_live.bat`.

## 🔔 Vigilante de señales (avisa cuándo comprar)

¿No quieres revisar a diario? El vigilante escanea varios pares y te **avisa solo
cuando hay una señal de COMPRA válida** — es decir, no basta con que exista la
señal: la combinación par+marco+estrategia debe tener **buen historial**
(retorno ≥ +20% y profit factor ≥ 1,3). Así evita setups perdedores.

```bash
python -m trading_bot.watch_signals --interval 1d          # escaneo puntual
./watch.sh          # Linux/macOS (con notificación de escritorio)
watch.bat           # Windows (con ventana de aviso)
```

Programa `watch.sh`/`watch.bat` con cron / Programador de tareas (1×/día). Cuando
aparezca una compra válida, lo registra en `state/alerts.log` y lanza una
notificación de escritorio (si tienes `notify-send` en Linux u `osascript` en Mac).

```cron
15 0 * * * /ruta/al/proyecto/watch.sh >> /ruta/al/proyecto/state/watch.log 2>&1
```

## 🔄 Bot en vivo continuo (GitHub Actions)

Para que el bot opere **de forma continua durante días** sin depender de tu
máquina, hay una workflow programada en `.github/workflows/paper-trading.yml`
que GitHub ejecuta **cada hora**:

1. Descarga el precio más reciente de Binance.
2. Evalúa la señal sobre la última vela cerrada.
3. Actualiza la cartera simulada (dinero virtual).
4. Guarda el diario en el repo: `state/live_journal.csv` (operaciones),
   `state/live_equity.csv` (equity por hora) y `state/live_state.json` (estado).

Así puedes volver al repo en 1-2 días y revisar exactamente qué hizo el bot.

**Para activarlo:**
- La workflow debe estar en la rama `main` (GitHub solo dispara `cron` en la
  rama por defecto): **fusiona el PR a `main`**.
- O lánzalo manualmente en la pestaña **Actions → Paper Trading Bot → Run workflow**.

La configuración (símbolo, intervalo, estrategia, capital) se edita en el bloque
`env:` de la workflow, sin tocar código.

> ⚠️ 2 días es muy poco para juzgar rentabilidad: este modo demuestra que el bot
> **opera en vivo correctamente**, no es una prueba de ganancias. La ventaja de
> la estrategia se mide en marcos diarios y tendencias largas (ver backtests).

## ⚠️ Aviso importante

- Esto es **paper trading**: dinero **virtual**. No hay riesgo de capital real.
- Los resultados de un **backtest son históricos**; rentabilidad pasada **no
  garantiza** rentabilidad futura. Ningún bot puede garantizar ganancias en
  mercados reales.
- No es asesoramiento financiero. Antes de arriesgar dinero real, valida en
  papel durante un periodo prolongado y entiende los riesgos.
