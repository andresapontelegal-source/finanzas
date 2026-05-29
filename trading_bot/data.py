"""Cliente de datos de mercado de Binance (endpoint publico, sin clave de API).

Usa https://data-api.binance.vision que sirve datos de mercado publicos de
Binance sin autenticacion y sin geo-bloqueo. Solo lectura de precios; jamas
se envian ordenes desde aqui.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

BASE_URL = "https://data-api.binance.vision/api/v3"

# Milisegundos por unidad de intervalo de Binance.
_INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}

_CACHE_DIR = Path(__file__).resolve().parent.parent / "data"


def _http_get(url: str, retries: int = 4) -> list:
    """GET JSON con reintentos y backoff exponencial."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-bot/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover
            last_err = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"No se pudo obtener datos de {url}: {last_err}")


def get_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 1000,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Descarga `limit` velas (OHLCV) recientes, paginando si limit > 1000.

    Devuelve un DataFrame indexado por timestamp (UTC) con columnas:
    open, high, low, close, volume.
    """
    if interval not in _INTERVAL_MS:
        raise ValueError(f"Intervalo no soportado: {interval}")

    cache_file = _CACHE_DIR / f"{symbol}_{interval}_{limit}.csv"
    if use_cache and cache_file.exists():
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return df

    rows: list[list] = []
    end_time = int(time.time() * 1000)
    remaining = limit
    step_ms = _INTERVAL_MS[interval]

    while remaining > 0:
        batch = min(remaining, 1000)
        start_time = end_time - batch * step_ms
        url = (
            f"{BASE_URL}/klines?symbol={symbol}&interval={interval}"
            f"&startTime={start_time}&endTime={end_time}&limit={batch}"
        )
        data = _http_get(url)
        if not data:
            break
        rows = data + rows
        end_time = data[0][0] - 1
        remaining -= len(data)
        if len(data) < batch:
            break

    if not rows:
        raise RuntimeError(f"Binance no devolvio datos para {symbol} {interval}")

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades", "tbav", "tqav", "ignore",
        ],
    )
    df = df[["open_time", "open", "high", "low", "close", "volume"]].copy()
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop(columns=["open_time"]).set_index("timestamp")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file)
    return df


def get_latest_price(symbol: str) -> float:
    """Precio actual de mercado (ultima vela de 1m)."""
    url = f"{BASE_URL}/ticker/price?symbol={symbol}"
    data = _http_get(url)
    return float(data["price"]) if isinstance(data, dict) else float(data[0]["price"])
