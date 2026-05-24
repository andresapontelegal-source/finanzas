"""Descarga de datos de mercado desde Yahoo Finance y exchanges cripto."""
from __future__ import annotations
import pandas as pd
from datetime import datetime, timedelta


_INTERVAL_MAP_YF = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "60m", "4h": "1h", "1d": "1d", "1w": "1wk",
}


def fetch_yahoo(symbol: str, timeframe: str, days: int) -> pd.DataFrame:
    import yfinance as yf
    interval = _INTERVAL_MAP_YF.get(timeframe, "1d")
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    df = yf.download(
        symbol, start=start, end=end, interval=interval,
        auto_adjust=True, progress=False,
    )
    if df.empty:
        raise ValueError(f"Sin datos para {symbol} ({timeframe})")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index.name = "datetime"
    return df[["open", "high", "low", "close", "volume"]].dropna()


def fetch_ccxt(symbol: str, timeframe: str, days: int,
               exchange_id: str = "binance") -> pd.DataFrame:
    import ccxt
    exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    since = exchange.parse8601((datetime.utcnow() - timedelta(days=days)).isoformat())
    all_rows = []
    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        all_rows.extend(batch)
        since = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    df = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
    return df.set_index("datetime").drop(columns=["ts"])


def load(symbol: str, timeframe: str = "1h", days: int = 365) -> pd.DataFrame:
    """Carga precios. Usa ccxt si el simbolo es BASE/QUOTE, si no Yahoo."""
    if "/" in symbol:
        return fetch_ccxt(symbol, timeframe, days)
    return fetch_yahoo(symbol, timeframe, days)
