#!/usr/bin/env python3
"""Punto de entrada del bot de paper trading.

Ejemplos:
  python run_bot.py backtest --symbol BTCUSDT --interval 4h --strategy ema_trend
  python run_bot.py optimize --symbol ETHUSDT --interval 4h
  python run_bot.py paper --symbol BTCUSDT --interval 1h --iterations 10 --poll 5
"""
from trading_bot.cli import main

if __name__ == "__main__":
    main()
