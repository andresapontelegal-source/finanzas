"""Interfaz de linea de comandos del bot de paper trading.

Subcomandos:
  backtest   Prueba la estrategia sobre datos historicos reales.
  optimize   Busca en rejilla los parametros mas rentables.
  paper      Ejecuta paper trading en vivo (simulado, sin dinero real).
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import pandas as pd

from . import data as data_mod
from .engine import backtest, run_live_paper
from .strategy import build_strategy

STATE_DIR = Path(__file__).resolve().parent.parent / "state"


def _load_data(args) -> pd.DataFrame:
    return data_mod.get_klines(
        args.symbol, args.interval, limit=args.limit, use_cache=not args.no_cache
    )


def cmd_backtest(args) -> None:
    df = _load_data(args)
    strat_kwargs = json.loads(args.params) if args.params else {}
    strategy = build_strategy(args.strategy, **strat_kwargs)
    result = backtest(
        df,
        strategy,
        initial_cash=args.cash,
        fee_rate=args.fee,
        slippage=args.slippage,
        stop_atr=args.stop_atr,
        take_atr=args.take_atr,
    )
    print(f"\n=== BACKTEST {args.symbol} {args.interval} ({len(df)} velas) ===")
    print(f"Estrategia: {strategy.name}  {strat_kwargs}")
    print(f"Periodo: {df.index[0]}  ->  {df.index[-1]}\n")
    print(result.summary())

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    result.equity_curve.to_csv(STATE_DIR / "equity_curve.csv")
    result.trades.to_csv(STATE_DIR / "trades.csv", index=False)
    with open(STATE_DIR / "metrics.json", "w") as fh:
        json.dump(result.metrics, fh, indent=2)
    print(f"Resultados guardados en {STATE_DIR}/")

    if args.plot:
        from .plotting import plot_backtest

        out = STATE_DIR / f"backtest_{args.symbol}_{args.interval}.png"
        title = f"Backtest {args.symbol} {args.interval} - {strategy.name} {strat_kwargs}"
        path = plot_backtest(df, result.equity_curve, result.trades, result.metrics, title, out)
        print(f"Grafico guardado en {path}")


def cmd_optimize(args) -> None:
    df = _load_data(args)
    print(f"\n=== OPTIMIZACION {args.symbol} {args.interval} ({len(df)} velas) ===")

    if args.strategy == "ema_trend":
        grid = {
            "fast": [10, 15, 20, 30],
            "slow": [40, 50, 60, 100],
            "trend": [150, 200, 250],
        }
    else:
        grid = {
            "rsi_period": [10, 14],
            "oversold": [25, 30, 35],
            "exit_level": [50, 55, 60],
            "trend": [150, 200],
        }

    keys = list(grid)
    best = None
    results = []
    for combo in itertools.product(*grid.values()):
        params = dict(zip(keys, combo))
        if args.strategy == "ema_trend" and params["fast"] >= params["slow"]:
            continue
        strategy = build_strategy(args.strategy, **params)
        res = backtest(
            df, strategy, initial_cash=args.cash, fee_rate=args.fee,
            slippage=args.slippage, stop_atr=args.stop_atr, take_atr=args.take_atr,
        )
        score = res.metrics["total_return_pct"]
        results.append((score, params, res.metrics))
        if best is None or score > best[0]:
            best = (score, params, res.metrics)

    results.sort(key=lambda x: x[0], reverse=True)
    print("\nTop 5 configuraciones por retorno total:")
    for score, params, m in results[:5]:
        print(
            f"  ret={score:+7.2f}%  sharpe={m['sharpe']:5.2f}  "
            f"dd={m['max_drawdown_pct']:6.2f}%  trades={m['num_trades']:3d}  {params}"
        )
    print(f"\nMejor configuracion: {best[1]}")
    print(f"Retorno: {best[0]:+.2f}%  (Buy&Hold: {best[2]['buy_hold_pct']:+.2f}%)")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "best_params.json", "w") as fh:
        json.dump({"strategy": args.strategy, "params": best[1], "metrics": best[2]}, fh, indent=2)
    print(f"\nGuardado en {STATE_DIR}/best_params.json")


def cmd_paper(args) -> None:
    strat_kwargs = json.loads(args.params) if args.params else {}
    strategy = build_strategy(args.strategy, **strat_kwargs)
    print(f"\n=== PAPER TRADING EN VIVO (SIMULADO) {args.symbol} {args.interval} ===")
    print(f"Estrategia: {strategy.name}  {strat_kwargs}")
    print(f"Capital inicial simulado: ${args.cash:,.2f}\n")

    def on_update(it, ts, price, broker):
        eq = broker.equity(price)
        pnl = eq / args.cash - 1.0
        pos = "LONG" if broker.in_position else "FLAT"
        print(
            f"[{it:04d}] {ts}  precio={price:,.2f}  {pos:4s}  "
            f"equity=${eq:,.2f}  pnl={pnl:+.2%}"
        )

    broker = run_live_paper(
        args.symbol, args.interval, strategy,
        poll_seconds=args.poll, initial_cash=args.cash,
        fee_rate=args.fee, slippage=args.slippage,
        max_iterations=args.iterations, on_update=on_update,
    )
    print("\n--- Operaciones simuladas ---")
    print(broker.trades_df().to_string(index=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Bot de paper trading (simulado).")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--symbol", default="BTCUSDT")
        sp.add_argument("--interval", default="1h")
        sp.add_argument("--limit", type=int, default=1000)
        sp.add_argument("--strategy", default="ema_trend", choices=["ema_trend", "rsi_mr"])
        sp.add_argument("--params", default="", help='JSON, ej: \'{"fast":15,"slow":50}\'')
        sp.add_argument("--cash", type=float, default=10_000.0)
        sp.add_argument("--fee", type=float, default=0.001)
        sp.add_argument("--slippage", type=float, default=0.0005)
        sp.add_argument("--stop-atr", dest="stop_atr", type=float, default=3.0)
        sp.add_argument("--take-atr", dest="take_atr", type=float, default=6.0)
        sp.add_argument("--no-cache", action="store_true")

    bt = sub.add_parser("backtest", help="Backtest sobre datos historicos.")
    common(bt)
    bt.add_argument("--plot", action="store_true", help="Genera grafico PNG de resultados.")
    bt.set_defaults(func=cmd_backtest)

    op = sub.add_parser("optimize", help="Busqueda en rejilla de parametros.")
    common(op)
    op.set_defaults(func=cmd_optimize)

    pp = sub.add_parser("paper", help="Paper trading en vivo (simulado).")
    common(pp)
    pp.add_argument("--poll", type=int, default=60, help="Segundos entre ciclos.")
    pp.add_argument("--iterations", type=int, default=None, help="Numero de ciclos.")
    pp.set_defaults(func=cmd_paper)
    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
