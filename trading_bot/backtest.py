"""Motor de backtesting vectorizado para la estrategia."""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from .strategy import add_indicators, position_size


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp | None
    entry_price: float
    exit_price: float | None
    units: float
    pnl: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[Trade] = field(default_factory=list)
    final_value: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe: float = 0.0
    win_rate: float = 0.0
    n_trades: int = 0


def run(df: pd.DataFrame, strat_cfg, bt_cfg) -> BacktestResult:
    data = add_indicators(df, strat_cfg)
    cash = bt_cfg.initial_cash
    units = 0.0
    entry_price = None
    stop = take = None
    trades: list[Trade] = []
    equity = []

    for ts, row in data.iterrows():
        price = float(row["close"])
        atr = float(row["atr"])

        if units > 0:
            exit_reason = None
            if price <= stop:
                exit_reason = f"stop ({stop:.2f})"
            elif price >= take:
                exit_reason = f"take ({take:.2f})"
            elif bool(row["cross_dn"]):
                exit_reason = "EMA cross down"
            if exit_reason:
                fill = price * (1 - bt_cfg.slippage)
                proceeds = units * fill * (1 - bt_cfg.commission)
                cash += proceeds
                pnl = proceeds - (units * entry_price * (1 + bt_cfg.commission))
                trades[-1].exit_time = ts
                trades[-1].exit_price = fill
                trades[-1].pnl = pnl
                trades[-1].reason = exit_reason
                units = 0.0
                entry_price = None

        if units == 0 and bool(row["cross_up"]) and row["rsi"] < strat_cfg.rsi_buy_max:
            size = position_size(cash, price, atr, strat_cfg)
            if size > 0:
                fill = price * (1 + bt_cfg.slippage)
                cost = size * fill * (1 + bt_cfg.commission)
                if cost <= cash:
                    cash -= cost
                    units = size
                    entry_price = fill
                    stop = fill - strat_cfg.atr_stop_mult * atr
                    take = fill + strat_cfg.atr_take_mult * atr
                    trades.append(Trade(
                        entry_time=ts, exit_time=None,
                        entry_price=fill, exit_price=None, units=size,
                    ))

        equity.append(cash + units * price)

    eq = pd.Series(equity, index=data.index, name="equity")
    returns = eq.pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(365 * 24)) if returns.std() > 0 else 0.0
    drawdown = (eq / eq.cummax() - 1.0).min() * 100
    wins = [t for t in trades if t.exit_price is not None and t.pnl > 0]
    closed = [t for t in trades if t.exit_price is not None]

    return BacktestResult(
        equity_curve=eq,
        trades=trades,
        final_value=float(eq.iloc[-1]),
        total_return_pct=float((eq.iloc[-1] / bt_cfg.initial_cash - 1) * 100),
        max_drawdown_pct=float(drawdown),
        sharpe=float(sharpe),
        win_rate=float(len(wins) / len(closed) * 100) if closed else 0.0,
        n_trades=len(closed),
    )
