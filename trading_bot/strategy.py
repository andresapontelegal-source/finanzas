"""Estrategias de trading e indicadores tecnicos (vectorizados con pandas).

Cada estrategia recibe un DataFrame OHLCV y devuelve una serie de senales:
    +1 -> querer estar comprado (long)
     0 -> querer estar en efectivo (flat)

El motor (engine.py) traduce los cambios de senal en ordenes simuladas.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# Indicadores
# --------------------------------------------------------------------------
def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


# --------------------------------------------------------------------------
# Estrategias
# --------------------------------------------------------------------------
@dataclass
class EmaTrendStrategy:
    """Seguimiento de tendencia con cruce de EMAs + filtro de tendencia largo.

    Entra largo cuando la EMA rapida cruza por encima de la lenta y el precio
    esta por encima de una EMA de tendencia (filtro de regimen alcista).
    Sale cuando la EMA rapida cruza por debajo de la lenta.
    """

    # Parametros por defecto = mejor configuracion hallada por `optimize`
    # sobre BTCUSDT 1d (+180.9%, Sharpe 1.22, profit factor 2.46).
    fast: int = 10
    slow: int = 100
    trend: int = 250

    name: str = "ema_trend"

    def signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        ema_fast = ema(close, self.fast)
        ema_slow = ema(close, self.slow)
        ema_trend = ema(close, self.trend)

        long_ok = (ema_fast > ema_slow) & (close > ema_trend)
        sig = pd.Series(np.where(long_ok, 1.0, 0.0), index=df.index)
        return sig


@dataclass
class RsiMeanReversion:
    """Reversion a la media: compra sobreventa en tendencia alcista."""

    rsi_period: int = 14
    oversold: float = 35.0
    exit_level: float = 55.0
    trend: int = 200

    name: str = "rsi_mr"

    def signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        r = rsi(close, self.rsi_period)
        trend_ok = close > ema(close, self.trend)

        sig = np.zeros(len(df))
        holding = False
        r_vals = r.to_numpy()
        trend_vals = trend_ok.to_numpy()
        for i in range(len(df)):
            if not holding:
                if trend_vals[i] and r_vals[i] < self.oversold:
                    holding = True
            else:
                if r_vals[i] > self.exit_level or not trend_vals[i]:
                    holding = False
            sig[i] = 1.0 if holding else 0.0
        return pd.Series(sig, index=df.index)


STRATEGIES = {
    "ema_trend": EmaTrendStrategy,
    "rsi_mr": RsiMeanReversion,
}


def build_strategy(name: str, **kwargs):
    if name not in STRATEGIES:
        raise ValueError(f"Estrategia desconocida: {name}. Opciones: {list(STRATEGIES)}")
    return STRATEGIES[name](**kwargs)
