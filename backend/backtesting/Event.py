from abc import ABC
from dataclasses import dataclass
import datetime
from typing import Literal

SignalType = Literal["BUY", "SELL", "HOLD", "EXIT"]
OrderType = Literal["MARKET", "LIMIT", "STOP"]
OrderDirection = Literal["BUY", "SELL"]
EquityTradeSegment = Literal["DELIVERY", "INTRADAY", "F&O"]

@dataclass(kw_only=True)
class Event(ABC):
    """
    Base class for all events.
    """
    timestamp: datetime = datetime.datetime.now()

@dataclass(kw_only=True)
class MarketEvent(Event):
    """
    Class for a market update in the backtest engine
    """
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass(kw_only=True)
class SignalEvent(Event):
    """
    Class for a signal from a strategy object.
    """
    ticker: str
    signal: SignalType

@dataclass(kw_only=True)
class OrderEvent(Event):
    """
    Class for Order to be placed on an execution system.
    """
    ticker: str
    order_type: OrderType
    direction: OrderDirection
    quantity: float

@dataclass(kw_only=True)
class FillEvent(Event):
    """
    Class for a filled order, as returned by broker's interface
    Fields:
        Event (_type_): _description_
    """
    exchange: str
    ticker: str
    order_type: OrderType
    direction: OrderDirection
    quantity: float
    fill_price: float
    charges: TransactionCharges

@dataclass
class TransactionCharges:
    """Monetary charges and taxes applied to a transaction."""
    brokerage: float = 0.0
    exchange: float = 0.0
    sebi: float = 0.0
    dp: float = 0.0
    stt: float = 0.0
    stamp_duty: float = 0.0
    gst: float = 0.0

    def total_transaction_charges(self) -> float:
        return self.brokerage + self.exchange + self.sebi + self.dp
    def taxes(self) -> float:
        return self.stt + self.stamp_duty + self.gst
    def total(self) -> float:
        return self.total_transaction_charges() + self.taxes()

    def __add__(self, other: object):
        if not isinstance(other, TransactionCharges):
            return TypeError("Class mismatch")
        return TransactionCharges(
            brokerage=self.brokerage + other.brokerage,
            exchange=self.exchange + other.exchange,
            sebi=self.sebi + other.sebi,
            dp=self.dp + other.dp,
            stt=self.stt + other.stt,
            stamp_duty=self.stamp_duty + other.stamp_duty,
            gst=self.gst + other.gst,
        )
        