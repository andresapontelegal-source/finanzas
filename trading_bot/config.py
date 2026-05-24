"""Configuracion central del bot."""
import os
from dataclasses import dataclass, field
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class StrategyConfig:
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_period: int = 14
    rsi_buy_max: float = 70.0
    rsi_sell_min: float = 30.0
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    atr_take_mult: float = 4.0
    risk_per_trade: float = 0.01


@dataclass
class BacktestConfig:
    initial_cash: float = 10_000.0
    commission: float = 0.001
    slippage: float = 0.0005


@dataclass
class LiveConfig:
    mode: str = os.getenv("MODE", "paper")
    alpaca_key: str = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret: str = os.getenv("ALPACA_API_SECRET", "")
    poll_seconds: int = 60


@dataclass
class BotConfig:
    symbols: list[str] = field(default_factory=lambda: ["BTC-USD", "ETH-USD"])
    timeframe: str = "1h"
    lookback_days: int = 365
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    live: LiveConfig = field(default_factory=LiveConfig)


CONFIG = BotConfig()
