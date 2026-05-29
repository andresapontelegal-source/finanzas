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

## ⚠️ Aviso importante

- Esto es **paper trading**: dinero **virtual**. No hay riesgo de capital real.
- Los resultados de un **backtest son históricos**; rentabilidad pasada **no
  garantiza** rentabilidad futura. Ningún bot puede garantizar ganancias en
  mercados reales.
- No es asesoramiento financiero. Antes de arriesgar dinero real, valida en
  papel durante un periodo prolongado y entiende los riesgos.
