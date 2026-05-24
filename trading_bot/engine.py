"""Motor de backtest agnostico a la estrategia.

Acepta cualquier DataFrame con columnas: close, atr, entry, exit.
Aplica stop loss / take profit por ATR y sizing por riesgo fijo.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp | None = None
    entry_price: float = 0.0
    exit_price: float | None = None
    units: float = 0.0
    pnl: float = 0.0
    reason: str = ""


@dataclass
class Result:
    equity: pd.Series
    trades: list[Trade] = field(default_factory=list)
    final: float = 0.0
    return_pct: float = 0.0
    max_dd_pct: float = 0.0
    sharpe: float = 0.0
    win_rate: float = 0.0
    n_trades: int = 0


def run(signals: pd.DataFrame, cash: float = 10_000.0,
        commission: float = 0.001, slippage: float = 0.0005,
        risk: float = 0.01, stop_mult: float = 2.0,
        take_mult: float = 4.0, bars_per_year: int = 252) -> Result:
    bal = cash
    units = 0.0
    entry = stop = take = None
    trades: list[Trade] = []
    eq = []

    for ts, row in signals.iterrows():
        price = float(row["close"])
        atr = float(row["atr"])

        if units > 0:
            reason = None
            if price <= stop: reason = f"stop ({stop:.2f})"
            elif price >= take: reason = f"take ({take:.2f})"
            elif bool(row["exit"]): reason = "exit signal"
            if reason:
                fill = price * (1 - slippage)
                proceeds = units * fill * (1 - commission)
                bal += proceeds
                trades[-1].exit_time = ts
                trades[-1].exit_price = fill
                trades[-1].pnl = proceeds - units * entry * (1 + commission)
                trades[-1].reason = reason
                units = 0.0
                entry = None

        if units == 0 and bool(row["entry"]):
            stop_dist = stop_mult * atr
            if stop_dist > 0:
                size = min((bal * risk) / stop_dist, bal / price)
                if size > 0:
                    fill = price * (1 + slippage)
                    cost = size * fill * (1 + commission)
                    if cost <= bal:
                        bal -= cost
                        units = size
                        entry = fill
                        stop = fill - stop_mult * atr
                        take = fill + take_mult * atr
                        trades.append(Trade(
                            entry_time=ts, entry_price=fill, units=size,
                        ))
        eq.append(bal + units * price)

    e = pd.Series(eq, index=signals.index)
    rets = e.pct_change().dropna()
    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0
    dd = (e / e.cummax() - 1).min() * 100
    closed = [t for t in trades if t.exit_price is not None]
    wins = [t for t in closed if t.pnl > 0]
    return Result(
        equity=e, trades=trades,
        final=float(e.iloc[-1]),
        return_pct=float((e.iloc[-1] / cash - 1) * 100),
        max_dd_pct=float(dd),
        sharpe=float(sharpe),
        win_rate=float(len(wins) / len(closed) * 100) if closed else 0.0,
        n_trades=len(closed),
    )
