"""Trading bot modular: datos, estrategia, backtest y broker."""
from .config import CONFIG
from .strategy import generate_signal, add_indicators
from .backtest import run as backtest

__all__ = ["CONFIG", "generate_signal", "add_indicators", "backtest"]
