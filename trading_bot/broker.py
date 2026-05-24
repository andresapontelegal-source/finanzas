"""Abstraccion de broker: paper simulado o Alpaca paper trading real."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Position:
    symbol: str
    units: float
    entry_price: float
    entry_time: datetime


@dataclass
class PaperBroker:
    """Broker simulado en memoria. No conecta a internet."""
    cash: float = 10_000.0
    positions: dict[str, Position] = field(default_factory=dict)
    commission: float = 0.001
    history: list[dict] = field(default_factory=list)

    def buy(self, symbol: str, units: float, price: float) -> None:
        cost = units * price * (1 + self.commission)
        if cost > self.cash:
            return
        self.cash -= cost
        self.positions[symbol] = Position(
            symbol=symbol, units=units, entry_price=price,
            entry_time=datetime.utcnow(),
        )
        self.history.append({
            "ts": datetime.utcnow(), "action": "buy",
            "symbol": symbol, "units": units, "price": price,
        })

    def sell(self, symbol: str, price: float) -> float:
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return 0.0
        proceeds = pos.units * price * (1 - self.commission)
        self.cash += proceeds
        pnl = proceeds - pos.units * pos.entry_price * (1 + self.commission)
        self.history.append({
            "ts": datetime.utcnow(), "action": "sell",
            "symbol": symbol, "units": pos.units, "price": price, "pnl": pnl,
        })
        return pnl

    def position(self, symbol: str) -> Position | None:
        return self.positions.get(symbol)

    def equity(self, prices: dict[str, float]) -> float:
        value = self.cash
        for sym, pos in self.positions.items():
            value += pos.units * prices.get(sym, pos.entry_price)
        return value


class AlpacaBroker:
    """Wrapper sobre alpaca-py para paper trading real con dinero ficticio.

    Requiere ALPACA_API_KEY y ALPACA_API_SECRET en el entorno.
    Crea tu cuenta gratis en https://alpaca.markets
    """

    def __init__(self, key: str, secret: str):
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        self._client = TradingClient(key, secret, paper=True)
        self._OrderReq = MarketOrderRequest
        self._Side = OrderSide
        self._TIF = TimeInForce

    def buy(self, symbol: str, units: float, price: float) -> None:
        req = self._OrderReq(
            symbol=symbol, qty=units,
            side=self._Side.BUY, time_in_force=self._TIF.GTC,
        )
        self._client.submit_order(req)

    def sell(self, symbol: str, price: float) -> float:
        try:
            pos = self._client.get_open_position(symbol)
            qty = float(pos.qty)
        except Exception:
            return 0.0
        req = self._OrderReq(
            symbol=symbol, qty=qty,
            side=self._Side.SELL, time_in_force=self._TIF.GTC,
        )
        self._client.submit_order(req)
        return 0.0

    def position(self, symbol: str):
        try:
            p = self._client.get_open_position(symbol)
            return Position(
                symbol=symbol, units=float(p.qty),
                entry_price=float(p.avg_entry_price),
                entry_time=datetime.utcnow(),
            )
        except Exception:
            return None

    def equity(self, prices: dict[str, float]) -> float:
        return float(self._client.get_account().equity)
