"""Cartera y broker simulados (paper trading puro).

Mantiene efectivo, una posicion long y un libro de operaciones. Aplica
comisiones y slippage realistas a cada fill. No existe conexion a ningun
exchange real: todos los fills son simulados a partir de precios de mercado.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Trade:
    timestamp: pd.Timestamp
    side: str            # "BUY" / "SELL"
    price: float         # precio de ejecucion (ya con slippage)
    qty: float
    fee: float
    cash_after: float
    reason: str = ""     # señal, stop, take-profit, fin de backtest


@dataclass
class PaperBroker:
    """Broker de simulacion con una sola posicion long por activo."""

    cash: float = 10_000.0
    fee_rate: float = 0.001      # 0.1% por operacion (taker de Binance)
    slippage: float = 0.0005     # 5 bps de deslizamiento adverso

    position_qty: float = 0.0
    entry_price: float = 0.0
    trades: list[Trade] = field(default_factory=list)

    @property
    def in_position(self) -> bool:
        return self.position_qty > 0

    def equity(self, price: float) -> float:
        return self.cash + self.position_qty * price

    def buy(self, ts: pd.Timestamp, price: float, reason: str = "signal") -> None:
        """Compra con todo el efectivo disponible (all-in long)."""
        if self.in_position or self.cash <= 0:
            return
        fill = price * (1 + self.slippage)
        qty = (self.cash / fill) * (1 - self.fee_rate)
        fee = self.cash * self.fee_rate
        self.position_qty = qty
        self.entry_price = fill
        self.cash = 0.0
        self.trades.append(
            Trade(ts, "BUY", fill, qty, fee, self.cash, reason)
        )

    def sell(self, ts: pd.Timestamp, price: float, reason: str = "signal") -> None:
        """Liquida la posicion completa a efectivo."""
        if not self.in_position:
            return
        fill = price * (1 - self.slippage)
        gross = self.position_qty * fill
        fee = gross * self.fee_rate
        self.cash = gross - fee
        qty = self.position_qty
        self.position_qty = 0.0
        self.entry_price = 0.0
        self.trades.append(
            Trade(ts, "SELL", fill, qty, fee, self.cash, reason)
        )

    def trades_df(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(
                columns=["timestamp", "side", "price", "qty", "fee", "cash_after", "reason"]
            )
        return pd.DataFrame([t.__dict__ for t in self.trades])
