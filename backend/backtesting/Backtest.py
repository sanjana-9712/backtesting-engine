from abc import ABC
import collections
from dataclasses import asdict
import time

from matplotlib import pyplot as plt
import pandas as pd

from backend.backtesting.Broker import Broker, SimulatedBroker
from backend.backtesting.DataHandler import DataHandler
from backend.backtesting.Event import FillEvent, MarketEvent, OrderEvent, SignalEvent
from backend.backtesting.Portfolio import Portfolio, SimplePortfolio
from backend.backtesting.Strategy import BuyAndHoldStrategy, MomentumStrategy12To1, MovingAvgCrossoverStrategy, Strategy


class Backtest(ABC):
    """
    Base class for backtesting a trading strategy
    """
    def __init__(self):
        self.event_queue = collections.deque()      # the central event queue
        self.hist_market_data = {}
    def __init__(self, data_handler: DataHandler, strategy: Strategy, portfolio: Portfolio, execution_handler: Broker):
        self.data_handler = data_handler
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.event_queue = collections.deque()  # event queue

    def _add_to_queue(self, obj)-> None:
        if obj is not None:
            self.event_queue.append(obj)
        return

    def run(self):
        """ Runs the backtest, while
            mkt_data_handler sends market events
        """
        print("Starting backtest...")
        start_time = time.time()
        while True:
            # print("Fetching market data...")    # assume mkt data comes at end of bar
            if self.data_handler.has_next():
                # 1. 
                evt_lst = self.data_handler.get_and_update_latest_bars()
                # print(f"Received market data...")
                # 2. Live broker executes any orders placed earlier
                for fill in self.execution_handler.execute_pending_orders():
                    # Update portfolio based on fill event
                    self.portfolio.process_order_fill(fill)
                    pass
                # 3. revalue portfolio at latest mkt data
                self.portfolio.mark_to_market()
                # 4. Run strategy
                if evt_lst is not None and len(evt_lst)>0:
                    for event in evt_lst:
                        self.event_queue.append(event)      # add to Events Queue
            else:
                # print("stopping backtest...")
                break
            while len(self.event_queue) > 0:
                event = self.event_queue.popleft()
                if isinstance(event, MarketEvent):
                    signal_event = self.strategy.on(event)
                    self._add_to_queue(signal_event)
                elif isinstance(event, SignalEvent):
                    order_event = self.portfolio.on(event)
                    self._add_to_queue(order_event)
                elif isinstance(event, OrderEvent):
                    fill_event = self.execution_handler.on(event)
                    self._add_to_queue(fill_event)
                elif isinstance(event, FillEvent):
                    # Update portfolio based on fill event
                    self.portfolio.process_order_fill(event)
    
        end_time = time.time()
        print(f"#### Backtest completed in {end_time - start_time:.2f} seconds")
        return
    
    def get_results(self):
        print(f"#### Backtest results...")
        kpi = self.portfolio.get_kpis()
        print(f"______________ KPI SUMMARY ________________")
        print(kpi)
        pnl = self.portfolio.get_pnl()
        print(f"______________ P&L SUMMARY ________________")
        print(pnl)
        print(f"______________ TRADE SUMMARY ________________")
        for trd in self.portfolio.get_trades():
            print(f"Trade date={trd.timestamp} | ticker={trd.ticker} | {trd.direction} | {trd.quantity} units @{trd.fill_price} | cost={trd.charges.total()}")            
        # plot cumulative returns
        return_df = self.portfolio.get_equity_curve()
        print(f"______________ EQUITY CURVE ________________")
        return_df['equity_curve'].plot()
        plt.show()
        return
        
    
# ##################################################################################################################
# ###################################### Moving avg crossover strategy backtest ######################################
# ##################################################################################################################
class MACBacktest(Backtest):
    """
    Class for backtesting a MACD strategy
    """
    def __init__(self, ticker_lst: list[str]
                 , mkt_data: DataHandler
                 , portfolio:Portfolio=None
                 , broker:Broker=None
                 , costs: dict | None=None):
        super().__init__(
            mkt_data
             , MovingAvgCrossoverStrategy(mkt_data)
            # , BuyAndHoldStrategy()
            , portfolio if portfolio is not None else SimplePortfolio(mkt_data)
            , broker if broker is not None else SimulatedBroker(data_handler=mkt_data, costs=costs)
        )


# ##################################################################################################################
# ###################################### 12-1 momnetum strategy backtest ######################################
# ##################################################################################################################
class MomentumBacktest12To1(Backtest):
    """
    Class for backtesting a 12-1 momentum strategy
    """
    def __init__(self, data_handler: DataHandler, portfolio:Portfolio=None, broker:Broker=None):
        super().__init__(data_handler
                         , MomentumStrategy12To1()
                         , portfolio if portfolio is not None else SimplePortfolio()
                         , broker if broker is not None else SimulatedBroker(data_handler))