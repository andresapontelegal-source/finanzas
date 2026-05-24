"""Bot principal: corre la estrategia en vivo (paper o Alpaca)."""
from __future__ import annotations
import time
import argparse
from rich.console import Console
from rich.table import Table

from .config import CONFIG
from .data import load
from .strategy import add_indicators, generate_signal, position_size
from .broker import PaperBroker, AlpacaBroker
from .backtest import run as run_backtest
from .optimize import walk_forward

console = Console()


def _make_broker():
    if CONFIG.live.mode == "alpaca" and CONFIG.live.alpaca_key:
        console.print("[yellow]Conectando a Alpaca paper trading...[/yellow]")
        return AlpacaBroker(CONFIG.live.alpaca_key, CONFIG.live.alpaca_secret)
    return PaperBroker(cash=CONFIG.backtest.initial_cash)


def _print_signal(symbol, sig, broker):
    color = {"buy": "green", "sell": "red", "hold": "white"}[sig.action]
    console.print(
        f"[{color}]{symbol:>10}  {sig.action.upper():<4}  "
        f"@ {sig.price:>10.2f}  | {sig.reason}[/{color}]  "
        f"cash={broker.cash:.2f}" if hasattr(broker, "cash") else
        f"[{color}]{symbol:>10}  {sig.action.upper():<4}  @ {sig.price:>10.2f}  | {sig.reason}[/{color}]"
    )


def live_loop():
    broker = _make_broker()
    console.rule("[bold cyan]Bot en vivo (paper mode)")
    console.print(f"Simbolos: {CONFIG.symbols}  Timeframe: {CONFIG.timeframe}")
    while True:
        prices = {}
        for sym in CONFIG.symbols:
            try:
                df = load(sym, CONFIG.timeframe, days=CONFIG.lookback_days)
                df = add_indicators(df, CONFIG.strategy)
                pos = broker.position(sym)
                sig = generate_signal(
                    df, CONFIG.strategy,
                    in_position=pos is not None,
                    entry_price=pos.entry_price if pos else None,
                )
                prices[sym] = sig.price
                if sig.action == "buy":
                    atr = float(df.iloc[-1]["atr"])
                    cash = broker.cash if hasattr(broker, "cash") else 10_000.0
                    units = position_size(cash, sig.price, atr, CONFIG.strategy)
                    if units > 0:
                        broker.buy(sym, units, sig.price)
                elif sig.action == "sell":
                    broker.sell(sym, sig.price)
                _print_signal(sym, sig, broker)
            except Exception as e:
                console.print(f"[red]Error en {sym}: {e}[/red]")
        equity = broker.equity(prices)
        console.print(f"[bold]Equity total: {equity:.2f}[/bold]\n")
        time.sleep(CONFIG.live.poll_seconds)


def backtest_cmd(symbol: str):
    console.rule(f"[bold cyan]Backtest {symbol}")
    df = load(symbol, CONFIG.timeframe, days=CONFIG.lookback_days)
    res = run_backtest(df, CONFIG.strategy, CONFIG.backtest)

    table = Table(title="Resultados", show_header=False)
    table.add_row("Capital inicial", f"${CONFIG.backtest.initial_cash:,.2f}")
    table.add_row("Capital final",   f"${res.final_value:,.2f}")
    table.add_row("Retorno total",   f"{res.total_return_pct:+.2f}%")
    table.add_row("Max drawdown",    f"{res.max_drawdown_pct:.2f}%")
    table.add_row("Sharpe ratio",    f"{res.sharpe:.2f}")
    table.add_row("Operaciones",     str(res.n_trades))
    table.add_row("Win rate",        f"{res.win_rate:.1f}%")
    console.print(table)

    if res.trades:
        t = Table(title="Ultimas 10 operaciones")
        for col in ["Entrada", "Salida", "Precio In", "Precio Out", "PnL", "Motivo"]:
            t.add_column(col)
        for tr in res.trades[-10:]:
            t.add_row(
                str(tr.entry_time)[:16],
                str(tr.exit_time)[:16] if tr.exit_time else "abierta",
                f"{tr.entry_price:.2f}",
                f"{tr.exit_price:.2f}" if tr.exit_price else "-",
                f"{tr.pnl:+.2f}" if tr.exit_price else "-",
                tr.reason or "-",
            )
        console.print(t)


def optimize_cmd(symbol: str, timeframe: str, days: int):
    console.rule(f"[bold cyan]Optimizando {symbol} ({timeframe}, {days}d)")
    df = load(symbol, timeframe, days=days)
    grid = {
        "ema_fast":       [8, 12, 20],
        "ema_slow":       [30, 50, 80, 120],
        "rsi_buy_max":    [70, 80],
        "atr_stop_mult":  [1.5, 2.0, 3.0],
        "atr_take_mult":  [3.0, 5.0, 8.0],
        "risk_per_trade": [0.01, 0.02],
    }
    wf = walk_forward(df, grid, CONFIG.backtest, rank_by="sharpe")
    if not wf.get("best_params"):
        console.print("[red]Sin parametros validos[/red]")
        return
    console.print(f"\n[bold]Mejores parametros (train):[/bold] {wf['best_params']}")
    tm, te = wf["train_metrics"], wf["test_metrics"]
    t = Table(title="Train vs Test (out-of-sample)")
    for col in ["Set", "Retorno", "Sharpe", "Max DD", "Trades"]:
        t.add_column(col)
    t.add_row("Train", f"{tm['return_pct']:+.2f}%", f"{tm['sharpe']:.2f}",
              f"{tm['max_dd_pct']:.2f}%", str(tm["trades"]))
    t.add_row("Test",  f"{te['return_pct']:+.2f}%", f"{te['sharpe']:.2f}",
              f"{te['max_dd_pct']:.2f}%", str(te["trades"]))
    console.print(t)
    gap = tm["return_pct"] - te["return_pct"]
    msg = "[red]Probable OVERFIT[/red]" if gap > 30 else "[green]Razonable[/green]"
    console.print(f"Gap train-test: {gap:+.2f}%  {msg}")


def main():
    parser = argparse.ArgumentParser(description="Trading bot")
    sub = parser.add_subparsers(dest="cmd", required=True)
    bt = sub.add_parser("backtest", help="Correr backtest historico")
    bt.add_argument("symbol", help="ej: BTC-USD, AAPL, BTC/USDT")
    sub.add_parser("live", help="Correr bot en vivo (paper)")
    opt = sub.add_parser("optimize", help="Optimizar parametros via grid search")
    opt.add_argument("symbol")
    opt.add_argument("--timeframe", default="1d")
    opt.add_argument("--days", type=int, default=730)
    args = parser.parse_args()

    if args.cmd == "backtest":
        backtest_cmd(args.symbol)
    elif args.cmd == "live":
        live_loop()
    elif args.cmd == "optimize":
        optimize_cmd(args.symbol, args.timeframe, args.days)


if __name__ == "__main__":
    main()
