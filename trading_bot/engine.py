"""Motor de backtest y de paper trading en vivo.

- backtest(): recorre datos historicos vela a vela aplicando la estrategia,
  con gestion de riesgo por stop-loss y take-profit basados en ATR.
- run_live_paper(): bucle en tiempo (casi) real que consulta el precio actual
  y opera en simulacion. Tambien 100% paper.

Reglas anti-sesgo (look-ahead):
- La senal de la vela i se ejecuta al cierre de la vela i (precio conocido).
- Stops/TP se evaluan con el high/low de la vela siguiente.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .portfolio import PaperBroker
from .strategy import atr


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: pd.DataFrame
    metrics: dict

    def summary(self) -> str:
        m = self.metrics
        return (
            f"  Capital inicial : ${m['initial']:,.2f}\n"
            f"  Capital final   : ${m['final']:,.2f}\n"
            f"  Retorno total   : {m['total_return_pct']:+.2f}%\n"
            f"  Buy & Hold      : {m['buy_hold_pct']:+.2f}%\n"
            f"  CAGR            : {m['cagr_pct']:+.2f}%\n"
            f"  Max drawdown    : {m['max_drawdown_pct']:.2f}%\n"
            f"  Sharpe (anual)  : {m['sharpe']:.2f}\n"
            f"  Operaciones     : {m['num_trades']}\n"
            f"  Win rate        : {m['win_rate_pct']:.1f}%\n"
            f"  Profit factor   : {m['profit_factor']:.2f}\n"
        )


def _periods_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return 365.0
    # Independiente de la resolucion del indice (ns/us/ms).
    deltas_sec = index.to_series().diff().dropna().dt.total_seconds()
    median_sec = float(deltas_sec.median())
    return (365.0 * 24 * 3600) / max(median_sec, 1.0)


def _compute_metrics(
    equity: pd.Series, trades: pd.DataFrame, close: pd.Series
) -> dict:
    initial = float(equity.iloc[0])
    final = float(equity.iloc[-1])
    total_return = final / initial - 1.0

    ppy = _periods_per_year(equity.index)
    years = len(equity) / ppy
    cagr = (final / initial) ** (1 / years) - 1.0 if years > 0 else 0.0

    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1.0
    max_dd = float(drawdown.min())

    rets = equity.pct_change().dropna()
    sharpe = 0.0
    if rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(ppy))

    # Estadisticas por operacion (pares compra->venta).
    pnls: list[float] = []
    buys = trades[trades["side"] == "BUY"].reset_index(drop=True)
    sells = trades[trades["side"] == "SELL"].reset_index(drop=True)
    for i in range(min(len(buys), len(sells))):
        cost = buys.loc[i, "price"] * buys.loc[i, "qty"]
        proceeds = sells.loc[i, "price"] * sells.loc[i, "qty"] - sells.loc[i, "fee"]
        pnls.append(proceeds - cost)
    pnls_arr = np.array(pnls)
    wins = pnls_arr[pnls_arr > 0]
    losses = pnls_arr[pnls_arr < 0]
    win_rate = (len(wins) / len(pnls_arr) * 100) if len(pnls_arr) else 0.0
    profit_factor = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf")

    buy_hold = float(close.iloc[-1] / close.iloc[0] - 1.0)

    return {
        "initial": initial,
        "final": final,
        "total_return_pct": total_return * 100,
        "buy_hold_pct": buy_hold * 100,
        "cagr_pct": cagr * 100,
        "max_drawdown_pct": max_dd * 100,
        "sharpe": sharpe,
        "num_trades": int(len(pnls_arr)),
        "win_rate_pct": win_rate,
        "profit_factor": float(profit_factor),
    }


def backtest(
    df: pd.DataFrame,
    strategy,
    initial_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage: float = 0.0005,
    atr_period: int = 14,
    stop_atr: float = 3.0,
    take_atr: float = 6.0,
) -> BacktestResult:
    """Ejecuta un backtest vela a vela con gestion de riesgo ATR."""
    signals = strategy.signals(df).to_numpy()
    atr_vals = atr(df, atr_period).to_numpy()
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    index = df.index

    broker = PaperBroker(cash=initial_cash, fee_rate=fee_rate, slippage=slippage)
    equity = np.empty(len(df))
    stop_price = take_price = 0.0

    for i in range(len(df)):
        ts = index[i]
        price = close[i]

        # 1) Gestion de riesgo intra-vela (usa el rango de la vela actual).
        if broker.in_position:
            if low[i] <= stop_price:
                broker.sell(ts, stop_price, reason="stop_loss")
            elif high[i] >= take_price:
                broker.sell(ts, take_price, reason="take_profit")

        # 2) Ejecucion de la senal al cierre de la vela.
        want_long = signals[i] > 0
        if want_long and not broker.in_position:
            broker.buy(ts, price, reason="signal")
            a = atr_vals[i] if not np.isnan(atr_vals[i]) else price * 0.02
            stop_price = broker.entry_price - stop_atr * a
            take_price = broker.entry_price + take_atr * a
        elif not want_long and broker.in_position:
            broker.sell(ts, price, reason="signal")

        equity[i] = broker.equity(price)

    # Cierre forzado al final para contabilizar la posicion abierta.
    if broker.in_position:
        broker.sell(index[-1], close[-1], reason="fin_backtest")
        equity[-1] = broker.equity(close[-1])

    equity_series = pd.Series(equity, index=index, name="equity")
    trades_df = broker.trades_df()
    metrics = _compute_metrics(equity_series, trades_df, df["close"])
    return BacktestResult(equity_series, trades_df, metrics)


def run_live_paper(
    symbol: str,
    interval: str,
    strategy,
    poll_seconds: int = 60,
    initial_cash: float = 10_000.0,
    fee_rate: float = 0.001,
    slippage: float = 0.0005,
    max_iterations: int | None = None,
    on_update=None,
):
    """Bucle de paper trading en vivo (simulado).

    Cada ciclo descarga las velas recientes, recalcula la senal sobre la ultima
    vela cerrada y opera en simulacion. Devuelve el broker al terminar.
    """
    from . import data as data_mod

    broker = PaperBroker(cash=initial_cash, fee_rate=fee_rate, slippage=slippage)
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        df = data_mod.get_klines(symbol, interval, limit=300, use_cache=False)
        sig = strategy.signals(df)
        last_closed = sig.iloc[-2]  # ultima vela cerrada (evita la vela en curso)
        price = float(df["close"].iloc[-1])
        ts = df.index[-1]

        if last_closed > 0 and not broker.in_position:
            broker.buy(ts, price, reason="signal_live")
        elif last_closed <= 0 and broker.in_position:
            broker.sell(ts, price, reason="signal_live")

        if on_update:
            on_update(iteration, ts, price, broker)

        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(poll_seconds)
    return broker
