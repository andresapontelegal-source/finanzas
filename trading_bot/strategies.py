"""Catalogo de estrategias de trading.

Cada estrategia retorna un DataFrame con al menos las columnas:
    close, atr, entry (bool), exit (bool)
para que el motor de backtest sea agnostico a la estrategia.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def ema_cross(df: pd.DataFrame, fast: int = 20, slow: int = 50,
              rsi_max: float = 70.0) -> pd.DataFrame:
    """Cruce de EMAs con filtro RSI. Tendencia."""
    out = df.copy()
    out["ema_fast"] = _ema(out["close"], fast)
    out["ema_slow"] = _ema(out["close"], slow)
    out["rsi"] = _rsi(out["close"])
    out["atr"] = _atr(out)
    cu = (out["ema_fast"] > out["ema_slow"]) & (out["ema_fast"].shift() <= out["ema_slow"].shift())
    cd = (out["ema_fast"] < out["ema_slow"]) & (out["ema_fast"].shift() >= out["ema_slow"].shift())
    out["entry"] = cu & (out["rsi"] < rsi_max)
    out["exit"]  = cd
    return out.dropna()


def mean_reversion(df: pd.DataFrame, rsi_buy: float = 30.0,
                   rsi_sell: float = 55.0, trend_ma: int = 200) -> pd.DataFrame:
    """Compra sobreventa solo si esta sobre la media de 200d (filtro de tendencia)."""
    out = df.copy()
    out["rsi"] = _rsi(out["close"])
    out["trend"] = _sma(out["close"], trend_ma)
    out["atr"] = _atr(out)
    above_trend = out["close"] > out["trend"]
    out["entry"] = (out["rsi"] < rsi_buy) & above_trend & (out["rsi"].shift() >= rsi_buy)
    out["exit"]  = out["rsi"] > rsi_sell
    return out.dropna()


def bollinger_breakout(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Compra cuando el precio rompe la banda superior. Momentum."""
    out = df.copy()
    mid = _sma(out["close"], n)
    std = out["close"].rolling(n).std()
    out["bb_up"] = mid + k * std
    out["bb_mid"] = mid
    out["atr"] = _atr(out)
    out["entry"] = (out["close"] > out["bb_up"]) & (out["close"].shift() <= out["bb_up"].shift())
    out["exit"]  = out["close"] < out["bb_mid"]
    return out.dropna()


def donchian_breakout(df: pd.DataFrame, entry_n: int = 20, exit_n: int = 10) -> pd.DataFrame:
    """Turtle Trading clasico: maximo de N dias entra, minimo de M dias sale."""
    out = df.copy()
    out["don_hi"] = out["high"].rolling(entry_n).max().shift(1)
    out["don_lo"] = out["low"].rolling(exit_n).min().shift(1)
    out["atr"] = _atr(out)
    out["entry"] = out["close"] > out["don_hi"]
    out["exit"]  = out["close"] < out["don_lo"]
    return out.dropna()


def macd_cross(df: pd.DataFrame, fast: int = 12, slow: int = 26,
               signal: int = 9) -> pd.DataFrame:
    """MACD: histograma cruza cero al alza/baja."""
    out = df.copy()
    macd_line = _ema(out["close"], fast) - _ema(out["close"], slow)
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    out["macd_hist"] = hist
    out["atr"] = _atr(out)
    out["entry"] = (hist > 0) & (hist.shift() <= 0)
    out["exit"]  = (hist < 0) & (hist.shift() >= 0)
    return out.dropna()


REGISTRY = {
    "ema_cross":          ema_cross,
    "mean_reversion":     mean_reversion,
    "bollinger_breakout": bollinger_breakout,
    "donchian_breakout":  donchian_breakout,
    "macd_cross":         macd_cross,
}
