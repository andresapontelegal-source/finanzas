"""Runner de paper trading persistente (un ciclo por ejecucion).

Pensado para ejecutarse de forma programada (p. ej. GitHub Actions cron):
cada ejecucion descarga el precio mas reciente, evalua la senal sobre la
ULTIMA VELA CERRADA y actualiza la cartera simulada. El estado (efectivo,
posicion, operaciones, historial de equity) se guarda en disco para que la
siguiente ejecucion continue donde lo dejo. 100% simulado: dinero virtual.

Es idempotente por vela: si se ejecuta dos veces dentro de la misma vela, no
duplica operaciones (recuerda el timestamp de la ultima vela procesada).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import data as data_mod
from .portfolio import PaperBroker, Trade
from .strategy import build_strategy

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_FILE = STATE_DIR / "live_state.json"
JOURNAL_FILE = STATE_DIR / "live_journal.csv"
EQUITY_FILE = STATE_DIR / "live_equity.csv"


def _default_state(cfg: dict) -> dict:
    return {
        "config": cfg,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cash": cfg["cash"],
        "position_qty": 0.0,
        "entry_price": 0.0,
        "last_candle": None,      # timestamp ISO de la ultima vela cerrada procesada
        "trades": [],             # historial de operaciones simuladas
        "iterations": 0,
    }


def _load_state(cfg: dict) -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as fh:
            return json.load(fh)
    return _default_state(cfg)


def _save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as fh:
        json.dump(state, fh, indent=2)


def _append_line(path: Path, header: str, line: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a") as fh:
        if new:
            fh.write(header + "\n")
        fh.write(line + "\n")


def run_once(cfg: dict) -> dict:
    """Ejecuta un ciclo de paper trading y persiste el estado. Devuelve un resumen."""
    state = _load_state(cfg)

    strategy = build_strategy(cfg["strategy"], **cfg.get("params", {}))
    df = data_mod.get_klines(cfg["symbol"], cfg["interval"], limit=300, use_cache=False)

    # Reconstruir el broker desde el estado guardado.
    broker = PaperBroker(cash=state["cash"], fee_rate=cfg["fee"], slippage=cfg["slippage"])
    broker.position_qty = state["position_qty"]
    broker.entry_price = state["entry_price"]

    signals = strategy.signals(df)
    last_closed_ts = df.index[-2]                 # ultima vela CERRADA
    want_long = signals.iloc[-2] > 0
    price = float(df["close"].iloc[-2])           # cierre de esa vela
    live_price = float(df["close"].iloc[-1])      # precio mas reciente (vela en curso)
    candle_id = last_closed_ts.isoformat()

    action = "HOLD"
    already_done = state["last_candle"] == candle_id

    if not already_done:
        if want_long and not broker.in_position:
            broker.buy(last_closed_ts, price, reason="signal_live")
            action = "BUY"
        elif not want_long and broker.in_position:
            broker.sell(last_closed_ts, price, reason="signal_live")
            action = "SELL"
        state["last_candle"] = candle_id

    # Persistir trades nuevos.
    for t in broker.trades:
        rec = {
            "timestamp": str(t.timestamp), "side": t.side, "price": t.price,
            "qty": t.qty, "fee": t.fee, "cash_after": t.cash_after, "reason": t.reason,
        }
        state["trades"].append(rec)
        _append_line(
            JOURNAL_FILE,
            "timestamp,side,price,qty,fee,cash_after,reason",
            f"{t.timestamp},{t.side},{t.price:.2f},{t.qty:.8f},{t.fee:.2f},{t.cash_after:.2f},{t.reason}",
        )

    # Actualizar estado.
    state["cash"] = broker.cash
    state["position_qty"] = broker.position_qty
    state["entry_price"] = broker.entry_price
    state["iterations"] += 1

    equity = broker.equity(live_price)
    pnl = equity / cfg["cash"] - 1.0
    now = datetime.now(timezone.utc).isoformat()
    pos = "LONG" if broker.in_position else "FLAT"
    _append_line(
        EQUITY_FILE,
        "time,candle,price,position,equity,pnl_pct,action",
        f"{now},{candle_id},{live_price:.2f},{pos},{equity:.2f},{pnl*100:.4f},{action}",
    )

    _save_state(state)

    return {
        "time": now, "symbol": cfg["symbol"], "interval": cfg["interval"],
        "price": live_price, "position": pos, "action": action,
        "equity": equity, "pnl_pct": pnl * 100, "iterations": state["iterations"],
        "num_trades": len(state["trades"]),
    }


def _config_from_env() -> dict:
    return {
        "symbol": os.environ.get("BOT_SYMBOL", "BTCUSDT"),
        "interval": os.environ.get("BOT_INTERVAL", "1h"),
        "strategy": os.environ.get("BOT_STRATEGY", "ema_trend"),
        "params": json.loads(os.environ.get("BOT_PARAMS", "{}")),
        "cash": float(os.environ.get("BOT_CASH", "10000")),
        "fee": float(os.environ.get("BOT_FEE", "0.001")),
        "slippage": float(os.environ.get("BOT_SLIPPAGE", "0.0005")),
    }


def main() -> None:
    cfg = _config_from_env()
    summary = run_once(cfg)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
