"""Generacion de graficos para los resultados del backtest.

Usa matplotlib con backend 'Agg' (sin pantalla) para guardar PNG.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


def plot_backtest(
    df: pd.DataFrame,
    equity: pd.Series,
    trades: pd.DataFrame,
    metrics: dict,
    title: str,
    out_path: str | Path,
) -> Path:
    """Dibuja precio con operaciones, curva de capital y drawdown."""
    out_path = Path(out_path)
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(13, 11), sharex=True,
        gridspec_kw={"height_ratios": [2, 2, 1]},
    )

    # --- Panel 1: precio + marcadores de compra/venta ---
    ax1.plot(df.index, df["close"], color="#444", lw=1.0, label="Precio")
    if not trades.empty:
        buys = trades[trades["side"] == "BUY"]
        sells = trades[trades["side"] == "SELL"]
        ax1.scatter(buys["timestamp"], buys["price"], marker="^",
                    color="#2ca02c", s=70, zorder=5, label="Compra")
        ax1.scatter(sells["timestamp"], sells["price"], marker="v",
                    color="#d62728", s=70, zorder=5, label="Venta")
    ax1.set_ylabel("Precio (USDT)")
    ax1.set_title(title, fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)

    # --- Panel 2: curva de capital vs buy & hold ---
    initial = float(equity.iloc[0])
    buy_hold = initial * df["close"] / float(df["close"].iloc[0])
    ax2.plot(equity.index, equity.values, color="#1f77b4", lw=1.6,
             label=f"Bot ({metrics['total_return_pct']:+.1f}%)")
    ax2.plot(buy_hold.index, buy_hold.values, color="#ff7f0e", lw=1.2,
             ls="--", label=f"Buy & Hold ({metrics['buy_hold_pct']:+.1f}%)")
    ax2.axhline(initial, color="#999", lw=0.8, ls=":")
    ax2.set_ylabel("Capital (USDT)")
    ax2.legend(loc="upper left")
    ax2.grid(alpha=0.3)

    # --- Panel 3: drawdown ---
    dd = (equity / equity.cummax() - 1.0) * 100
    ax3.fill_between(dd.index, dd.values, 0, color="#d62728", alpha=0.4)
    ax3.set_ylabel("Drawdown (%)")
    ax3.set_xlabel("Fecha")
    ax3.grid(alpha=0.3)

    # Caja de metricas
    txt = (
        f"Final: ${metrics['final']:,.0f}   "
        f"CAGR: {metrics['cagr_pct']:+.1f}%   "
        f"Sharpe: {metrics['sharpe']:.2f}   "
        f"MaxDD: {metrics['max_drawdown_pct']:.1f}%   "
        f"WinRate: {metrics['win_rate_pct']:.0f}%   "
        f"PF: {metrics['profit_factor']:.2f}   "
        f"Trades: {metrics['num_trades']}"
    )
    fig.text(0.5, 0.005, txt, ha="center", fontsize=9,
             bbox=dict(boxstyle="round", facecolor="#f0f0f0"))

    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path
