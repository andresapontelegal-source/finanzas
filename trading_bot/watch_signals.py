"""Vigilante de senales: escanea pares y avisa cuando hay COMPRA valida.

"Valida" = no solo que exista senal hoy, sino que la combinacion
par+marco+estrategia tenga un historial rentable (filtro de calidad). Asi se
evita entrar en setups historicamente perdedores (como BNB 4h, que pierde).

Uso:
    python -m trading_bot.watch_signals
    python -m trading_bot.watch_signals --pairs BTCUSDT,ETHUSDT --interval 1d

Salida: imprime una tabla y, si hay alertas, escribe state/alerts.log y
devuelve codigo de salida 10 (util para encadenar notificaciones en cron).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import data as data_mod
from .engine import backtest
from .strategy import build_strategy

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
ALERTS_FILE = STATE_DIR / "alerts.log"

DEFAULT_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "LINKUSDT", "LTCUSDT", "ADAUSDT", "AVAXUSDT",
]

# Umbrales de calidad: solo alertamos si el historial de ESA combinacion es bueno.
MIN_RETURN_PCT = 20.0      # retorno historico total minimo
MIN_PROFIT_FACTOR = 1.3    # ganancias/perdidas minimo


def scan(pairs, interval, strategy_name, params) -> list[dict]:
    strat = build_strategy(strategy_name, **params)
    results = []
    for p in pairs:
        try:
            df = data_mod.get_klines(p, interval, limit=600, use_cache=False)
        except Exception as exc:  # par inexistente, red, etc.
            results.append({"pair": p, "error": str(exc)[:40]})
            continue

        sig = strat.signals(df)
        has_signal = bool(sig.iloc[-2] > 0)          # ultima vela cerrada
        price = float(df["close"].iloc[-1])

        # Calidad historica de la combinacion.
        res = backtest(df, strat)
        m = res.metrics
        quality_ok = (
            m["total_return_pct"] >= MIN_RETURN_PCT
            and m["profit_factor"] >= MIN_PROFIT_FACTOR
        )
        alert = has_signal and quality_ok

        results.append({
            "pair": p, "price": price, "signal": has_signal,
            "ret": m["total_return_pct"], "pf": m["profit_factor"],
            "quality_ok": quality_ok, "alert": alert,
        })
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Vigilante de senales de compra.")
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--strategy", default="ema_trend", choices=["ema_trend", "rsi_mr"])
    parser.add_argument("--params", default='{"fast":10,"slow":100,"trend":250}')
    args = parser.parse_args(argv)

    import json
    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    params = json.loads(args.params) if args.params else {}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== Vigilante de senales — {now} ({args.interval}, {args.strategy}) ===")
    rows = scan(pairs, args.interval, args.strategy, params)

    print(f"{'PAR':10s} {'SENAL':6s} {'CALIDAD':8s} {'RET.HIST':>9s} {'PF':>5s} {'PRECIO':>12s}")
    print("-" * 56)
    alerts = []
    for r in rows:
        if "error" in r:
            print(f"{r['pair']:10s} ERROR {r['error']}")
            continue
        sig = "SI" if r["signal"] else "-"
        qual = "ok" if r["quality_ok"] else "evitar"
        flag = "  <== ALERTA COMPRA" if r["alert"] else ""
        print(
            f"{r['pair']:10s} {sig:6s} {qual:8s} {r['ret']:+8.1f}% "
            f"{r['pf']:5.2f} {r['price']:>12.4f}{flag}"
        )
        if r["alert"]:
            alerts.append(r)

    print()
    if alerts:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_FILE, "a") as fh:
            for a in alerts:
                line = (
                    f"{now}  COMPRA {a['pair']} {args.interval} "
                    f"precio={a['price']} ret_hist={a['ret']:+.1f}% pf={a['pf']:.2f}"
                )
                fh.write(line + "\n")
                print(f"🔔 {line}")
        print(f"\n{len(alerts)} alerta(s) guardada(s) en {ALERTS_FILE}")
        return 10  # codigo distinto para encadenar notificaciones en cron
    else:
        print("Sin senales de compra validas ahora mismo. El bot sigue en efectivo.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
