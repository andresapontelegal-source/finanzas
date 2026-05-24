"""Optimizador de parametros via grid search con validacion out-of-sample.

Estrategia anti-overfitting:
  - Dividir datos en train (70%) y test (30%)
  - Optimizar sobre train
  - Reportar performance del ganador en test
  - Si train >> test, es overfit
"""
from __future__ import annotations
from dataclasses import replace
from itertools import product
import pandas as pd

from .config import CONFIG, StrategyConfig
from .backtest import run as backtest


def _split(df: pd.DataFrame, train_frac: float = 0.7):
    n = int(len(df) * train_frac)
    return df.iloc[:n], df.iloc[n:]


def grid_search(df: pd.DataFrame, grid: dict, bt_cfg,
                rank_by: str = "sharpe", min_trades: int = 5) -> pd.DataFrame:
    """Prueba todas las combinaciones del grid y retorna ranking."""
    keys = list(grid.keys())
    rows = []
    total = 1
    for v in grid.values():
        total *= len(v)
    i = 0
    for values in product(*grid.values()):
        i += 1
        params = dict(zip(keys, values))
        if params.get("ema_fast", 0) >= params.get("ema_slow", 999):
            continue
        if params.get("atr_take_mult", 0) <= params.get("atr_stop_mult", 0):
            continue
        cfg = replace(CONFIG.strategy, **params)
        try:
            res = backtest(df, cfg, bt_cfg)
        except Exception:
            continue
        if res.n_trades < min_trades:
            continue
        rows.append({
            **params,
            "trades": res.n_trades,
            "return_pct": res.total_return_pct,
            "sharpe": res.sharpe,
            "max_dd_pct": res.max_drawdown_pct,
            "win_rate": res.win_rate,
            "calmar": (res.total_return_pct / abs(res.max_drawdown_pct))
                      if res.max_drawdown_pct != 0 else 0,
        })
    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return df_out
    return df_out.sort_values(rank_by, ascending=False).reset_index(drop=True)


def walk_forward(df: pd.DataFrame, grid: dict, bt_cfg,
                 rank_by: str = "sharpe") -> dict:
    """Optimiza sobre train, evalua sobre test."""
    train, test = _split(df, 0.7)
    train_results = grid_search(train, grid, bt_cfg, rank_by=rank_by)
    if train_results.empty:
        return {"train": train_results, "test": None, "best": None}

    best = train_results.iloc[0].to_dict()
    param_keys = [k for k in grid.keys()]
    best_params = {k: best[k] for k in param_keys}
    cfg = replace(CONFIG.strategy, **best_params)
    test_res = backtest(test, cfg, bt_cfg)
    return {
        "train_top": train_results.head(10),
        "best_params": best_params,
        "train_metrics": {
            "return_pct": best["return_pct"],
            "sharpe": best["sharpe"],
            "max_dd_pct": best["max_dd_pct"],
            "trades": int(best["trades"]),
        },
        "test_metrics": {
            "return_pct": test_res.total_return_pct,
            "sharpe": test_res.sharpe,
            "max_dd_pct": test_res.max_drawdown_pct,
            "trades": test_res.n_trades,
        },
    }
