"""Estrategia: cruce de EMAs con filtro RSI y trailing stop por ATR.

Compra cuando:
  - EMA rapida cruza por encima de la EMA lenta (tendencia alcista)
  - RSI esta por debajo de rsi_buy_max (no sobrecomprado)

Vende cuando:
  - EMA rapida cruza por debajo de la EMA lenta, o
  - Precio toca stop loss (entry - ATR * stop_mult), o
  - Precio toca take profit (entry + ATR * take_mult)
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class Signal:
    action: str  # 'buy' | 'sell' | 'hold'
    price: float
    reason: str
    stop_loss: float | None = None
    take_profit: float | None = None


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = _ema(out["close"], cfg.ema_fast)
    out["ema_slow"] = _ema(out["close"], cfg.ema_slow)
    out["rsi"] = _rsi(out["close"], cfg.rsi_period)
    out["atr"] = _atr(out, cfg.atr_period)
    out["cross_up"] = (out["ema_fast"] > out["ema_slow"]) & (
        out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)
    )
    out["cross_dn"] = (out["ema_fast"] < out["ema_slow"]) & (
        out["ema_fast"].shift(1) >= out["ema_slow"].shift(1)
    )
    return out.dropna()


def generate_signal(df: pd.DataFrame, cfg, in_position: bool,
                    entry_price: float | None = None) -> Signal:
    """Genera la senal para la ultima vela cerrada."""
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last["atr"])

    if not in_position:
        if bool(last["cross_up"]) and last["rsi"] < cfg.rsi_buy_max:
            return Signal(
                action="buy", price=price,
                reason=f"EMA cross up + RSI={last['rsi']:.1f}",
                stop_loss=price - cfg.atr_stop_mult * atr,
                take_profit=price + cfg.atr_take_mult * atr,
            )
        return Signal(action="hold", price=price, reason="sin senal de entrada")

    if bool(last["cross_dn"]):
        return Signal(action="sell", price=price, reason="EMA cross down")
    if entry_price is not None:
        stop = entry_price - cfg.atr_stop_mult * atr
        take = entry_price + cfg.atr_take_mult * atr
        if price <= stop:
            return Signal(action="sell", price=price, reason=f"stop loss ({stop:.2f})")
        if price >= take:
            return Signal(action="sell", price=price, reason=f"take profit ({take:.2f})")
    return Signal(action="hold", price=price, reason="mantener posicion")


def position_size(cash: float, price: float, atr: float, cfg) -> float:
    """Tamano de posicion segun riesgo fijo por trade (1% por defecto)."""
    risk_amount = cash * cfg.risk_per_trade
    stop_distance = cfg.atr_stop_mult * atr
    if stop_distance <= 0:
        return 0.0
    units = risk_amount / stop_distance
    max_units = cash / price
    return min(units, max_units)
