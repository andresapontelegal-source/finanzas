# Trading Bot

Bot modular de trading algoritmico para acciones y cripto.

## Estrategia

Cruce de medias exponenciales (EMA 20 / EMA 50) con filtro RSI y salida por
ATR (stop loss y take profit dinamicos). Riesgo fijo de 1% del capital por trade.

## Instalacion

```bash
cd trading_bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Uso

### Backtest

```bash
python -m trading_bot.bot backtest BTC-USD
python -m trading_bot.bot backtest AAPL
python -m trading_bot.bot backtest BTC/USDT     # via Binance
```

### Live (paper)

Modo simulado en memoria (por defecto):

```bash
python -m trading_bot.bot live
```

Modo Alpaca paper trading (dinero ficticio real):

```bash
# En .env: MODE=alpaca + credenciales
python -m trading_bot.bot live
```

## Estructura

| Archivo        | Que hace                                          |
|----------------|---------------------------------------------------|
| `config.py`    | Parametros de estrategia, backtest y broker       |
| `data.py`      | Descarga OHLCV de Yahoo Finance o exchanges cripto|
| `strategy.py`  | Indicadores y logica de senales                   |
| `backtest.py`  | Motor de backtesting con metricas                 |
| `broker.py`    | Broker simulado y wrapper de Alpaca               |
| `bot.py`       | CLI: backtest / live                              |

## Personalizacion

Edita `config.py` para cambiar simbolos, timeframe, parametros de la EMA,
RSI, ATR o el riesgo por operacion.

## Advertencia

Este bot es educativo. No es asesoria financiera. El trading conlleva riesgo
de perdida total del capital. Usa primero en modo paper durante varios meses
antes de considerar dinero real, y nunca arriesgues mas de lo que puedes
permitirte perder.
