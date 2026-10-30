from abc import ABC, abstractmethod
import collections
from datetime import datetime

from backend.backtesting.DataHandler import DataHandler, EventHandler
from backend.backtesting.Event import EquityTradeSegment, FillEvent, OrderEvent, TransactionCharges


class Broker(EventHandler[OrderEvent, FillEvent], ABC):
    """
    Abstract Class to handle Order events
    for different types of APIs (brokers, exchanges)
    """
    input_event: OrderEvent
    output_event: FillEvent
    @abstractmethod
    def execute_pending_orders(self) -> list[FillEvent]:
        raise NotImplementedError("method implemented in subclass")

# ##################################################################################################################
# ###################################### IMPLEMENTATION FOR BROKER SIMULATOR ######################################
# ##################################################################################################################

class SimulatedBroker(Broker):
    """
    Simple broker that executes orders on a simulated "live" broker.
    supports market orders.
    Simple "Live" Broker executes a Market order at next bar's (t+1) close (or, open, open+high etc),
    modelling a fixed slippage, commission/brokerage, other fees/taxes
    """

    def __init__(self
                 , data_handler: DataHandler
                 , costs:dict | None=None):
        self.data_handler = data_handler
        self.slippage_pct = (costs or {}).get("slippage", 0)
        self.costs = costs or {}
        self.pending_orders = collections.deque()

    def on(self, e: OrderEvent) -> FillEvent:
        """ Simulate order execution and generate a fill event,
            only for orders that were placed before latest-bar,
            to avoid Look-ahead bias
        """
        # 
        print(f"\t\tReceived order for TICKER={e.ticker} at={e.timestamp}")
        last_bar_timestamp = self.data_handler.get_latest_timestamp(e.ticker)
        if e.timestamp < last_bar_timestamp:
            # execute the order
            return self._execute_order(e)
        else:
            # wait for next bar to execute the order
            self.pending_orders.append(e)

    def execute_pending_orders(self) -> list[FillEvent]:
        """ execute the orders for which latest market data was not 
            available before
        """
        fill_lst = []
        while len(self.pending_orders)>0:
            order = self.pending_orders.popleft()
            last_bar_date = self.data_handler.get_latest_timestamp(order.ticker)
            # execute those orders which were placed before latest-bar
            if last_bar_date > order.timestamp:
                fill_lst.append(self._execute_order(order))
            else:
                print(f"can't execute Order for TICKER={order.ticker}")
        return fill_lst

    def _execute_order(self, e: OrderEvent) -> FillEvent:
        """ the Live broker executes given order,
            at the open price of latest mkt bar
        """
        match e.order_type:
            case "MARKET":
                try:
                    # executing market order
                    fill_price, fill_timestamp = self.get_market_price(e.ticker)  # open price
                    # Slippage
                    fill_price *= (1+self.slippage_pct) if e.direction=="BUY" else (1-self.slippage_pct)
                    # Trading costs & taxes
                    charges = self._compute_costs(e, fill_price, self.costs)
                    return FillEvent(
                        timestamp=fill_timestamp,
                        exchange="DUMMY",
                        ticker=e.ticker,
                        order_type=e.order_type,
                        direction=e.direction,
                        quantity=e.quantity,
                        fill_price=fill_price,
                        charges=charges
                    )
                except Exception as e:
                    print(e)
                    # raise
                return None
            case "LIMIT":
                raise NotImplementedError("Cant execute LIMIT orders")
            case "STOP":
                raise NotImplementedError("Cant execute STOP orders")

    def get_market_price(self, ticker: str) -> float:
        """ 
        retrieve the current market price for a given ticker
        """
        latest_bar = self.data_handler.get_latest_bars(ticker).iloc[0]
        return latest_bar['open'], latest_bar.name
    #     return self.get_market_price(ticker, self.data_handler.get_latest_timestamp())
    
    # def get_market_price(self, ticker: str, t: datetime) -> float:
    #     """ returns open price, for ticker, for bar with timestamp t

    #     Args:
    #         ticker (str): asset's ticker
    #         t (datetime): timestamp of bar requested

    #     Returns:
    #         float: open price
    #     """
    #     bar_t = self.data_handler.get_mkt_bar(ticker, t)
    #     return bar_t['open'], bar_t.name

    def _compute_costs(self, e: OrderEvent, fill_price: float, costs:dict) -> TransactionCharges:
        """ returns trading costs & taxes charged on a delivery order

        Args:
            e (OrderEvent): order executed
            fill_price (float)

        Returns:
            TransactionCharges: obj storing all costs
        """
        trading_costs = TradingCosts("DELIVERY", costs)
        return TransactionCharges(
            brokerage=trading_costs.brokerage(e, fill_price),
            exchange=trading_costs.exchange_fees(e, fill_price),
            sebi=trading_costs.sebi_fees(e, fill_price),
            dp=trading_costs.dp_charges(e, fill_price),
            stt=trading_costs.stt(e, fill_price),
            stamp_duty=trading_costs.stamp_duty(e, fill_price),
            gst=trading_costs.gst(e, fill_price),
        )

class TradingCosts:
    def __init__(self, segment:EquityTradeSegment, costs:dict):
        # import costs & tax rates from configs
        self.segment = str(segment).lower()
        segment_costs = costs.get(self.segment, {})
        self.brokerage_pct = segment_costs.get("brokerage", 0)
        self.exchange_fees_pct = segment_costs.get("exchange", 0)
        self.sebi_fees_pct = segment_costs.get("sebi", 0)
        self.dp_charge_per_order = segment_costs.get("dp", 0)
        self.stt_pct = segment_costs.get("stt", 0)
        self.stamp_duty_pct = segment_costs.get("stamp_duty", segment_costs.get("stampduty", 0))
        self.gst_pct = segment_costs.get("gst", 0)
    
    @staticmethod
    def _turnover(order: OrderEvent, price: float) -> float:
        return order.quantity * price

    @staticmethod
    def _percent_of(amount: float, rate: float) -> float:
        return amount * rate / 100

    def brokerage(self, order: OrderEvent, price: float) -> float:
        return self._percent_of(self._turnover(order, price), self.brokerage_pct)

    def exchange_fees(self, order: OrderEvent, price: float) -> float:
        return self._percent_of(self._turnover(order, price), self.exchange_fees_pct)

    def sebi_fees(self, order: OrderEvent, price: float) -> float:
        return self._percent_of(self._turnover(order, price), self.sebi_fees_pct)

    def dp_charges(self, order: OrderEvent, price: float) -> float:
        # TODO: proper handling needs to be done
        return float(self.dp_charge_per_order) if order.direction == "SELL" else 0.0

    def stt(self, order: OrderEvent, price: float) -> float:
        return self._percent_of(self._turnover(order, price), self.stt_pct)

    def stamp_duty(self, order: OrderEvent, price: float) -> float:
        if order.direction != "BUY":
            return 0.0
        return self._percent_of(self._turnover(order, price), self.stamp_duty_pct)

    def gst(self, order: OrderEvent, price: float) -> float:
        taxable_charges = (
            self.brokerage(order, price)
            + self.exchange_fees(order, price)
            + self.sebi_fees(order, price)
        )
        return self._percent_of(taxable_charges, self.gst_pct)
