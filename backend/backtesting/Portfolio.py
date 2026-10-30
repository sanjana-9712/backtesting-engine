from abc import ABC, abstractmethod

import datetime as dt
from functools import reduce
import pandas as pd

from backend.backtesting.DataHandler import DataHandler, EventHandler
from backend.backtesting.Event import FillEvent, OrderEvent, SignalEvent, TransactionCharges


class Portfolio(EventHandler[SignalEvent, OrderEvent], ABC):
    """
    Abstract class for Portfolio management
    """
    input_event: SignalEvent
    output_event: OrderEvent
    @abstractmethod
    def process_order_fill(self, e: FillEvent):
        """
        After an order is filled, method updates positions, and performance metrics

        Args:
            e (FillEvent): order fill event
        """
        raise NotImplementedError("method implemented in subclass")
    @abstractmethod
    def mark_to_market(self) -> None:
        """ updates portfolio returns/positions per new market data
        """
        raise NotImplementedError("method implemented in subclass")
    @abstractmethod
    def get_equity_curve(self, ticker: str):
        """returns the dataframe storing returns for ticker

        Args:
            ticker (str): stock
        """
        raise NotImplementedError("method implemented in subclass")
    @abstractmethod
    def get_kpis(self, ticker: str | None = None):
        """ return KPI for the strategy

        Args:
            ticker (str | None, optional): asset for which kpi requested. Defaults to portfolio.
        """
        raise NotImplementedError("method implemented in subclass")
    @abstractmethod
    def get_trades(self, ticker: str):
        """ returns all trades executed by the strategy

        Args:
            ticker (str): asset
        """
        raise NotImplementedError("method implemented in subclass")
    @abstractmethod
    def get_pnl(self, ticker: str | None = None) -> dict:
        """ returns gross & net pnl

        Args:
            ticker (str | None, optional): asset for which pnl requested. Defaults to portfolio.
        """
        raise NotImplementedError("method implemented in subclass")
    

# ##################################################################################################################
# ###################################### PORTFOLIO IMPLEMENTATION ######################################
# ##################################################################################################################

class SimplePortfolio(Portfolio):
    """
    Simple portfolio implementation,
    allows position of max ₹1 for every ticker (i.e. position is 0 or 1)
    """
    def __init__(self, md: DataHandler, initial_capital:float=1000000):
        self.mkt_data = md
        self.initial_capital = initial_capital  # 1mn as default
        # Trades executed
        self.trades = {}
        # Assets
        self.positions = {}     # Maps ticker to its cumulative position
        self.cash = {ticker: initial_capital/len(md.tickers) for ticker in md.tickers}          # cash alloted for each ticker
        # dataframe for storing portfolio details
        self.return_df = {ticker: pd.DataFrame(columns=['timestamp', 'position', 'cash', 'value', 'cumulative_return', 'return']).set_index('timestamp') for ticker in md.tickers}
        # portfolio level details
        self.portfolio_df = None

    def _get_position(self, ticker: str) -> int:
        """ returns portfolio position for ticker,
        """
        return self.positions.setdefault(ticker, 0)
    
    def on(self, e: SignalEvent) -> OrderEvent:
        """ converts Buy/Sell signals to Orders.
        Buy signal for ticker generates Buy order only of no position held in portfolio,
        as max position for any stock is 1 unit
        Short positions not allowed, so 
        Sell signal creates Sell order when position>0

        Args:
            e: SignalEvent obj

        Returns:
            OrderEvent: respective Order
        """
        # Implement order generation logic based on signal
        print(f"\tgeneratin order for TICKER={e.ticker} with signal={e.signal}")
        curr_position = self._get_position(e.ticker)
        if e.signal=="BUY":
            if abs(curr_position)<0.01:  # buy when position is 0
                return OrderEvent(
                    timestamp=e.timestamp,
                    ticker=e.ticker,
                    order_type="MARKET",
                    direction="BUY",
                    quantity=self._quantity_alloted(e)
                )
        elif e.signal=="SELL":  # sell when position is >0
            if curr_position>0.0:
                return OrderEvent(
                    timestamp=e.timestamp,
                    ticker=e.ticker,
                    order_type="MARKET",
                    direction="SELL",
                    quantity=self._quantity_alloted(e)
                )
        elif e.signal=="EXIT":
            pass
        return
    
    def _quantity_alloted(self, e: SignalEvent) -> int:
        """ quantity alloted to the order for this signal

        Args:
            e (SignalEvent): Signal obj

        Returns:
            int: alloted quantity
        """
        match e.signal:
            case "BUY":
                # investing all cash available in buy
                estim_price = self.mkt_data.get_latest_bars(e.ticker).iloc[-1]['close']
                # taking a buffer to accommodate for slippage & costs
                return int((self.cash[e.ticker] * 0.9) / estim_price)
            case "SELL":
                # sell all current posiiton
                return self._get_position(e.ticker)

    def process_order_fill(self, e: FillEvent):
        print(f"\t\tOrder executed for TICKER={e.ticker} at price={e.fill_price} at {e.timestamp}")
        # Add to trades
        self.trades.setdefault(e.ticker, []).append(e)   # Using FillEvent class for storing trades for now
        # Update portfolio positions, and cash 
        self.positions[e.ticker] = self._get_position(e.ticker) + (1 if e.direction=="BUY" else -1)*e.quantity
        self.cash[e.ticker] += (-1 if e.direction=="BUY" else 1) * e.quantity * e.fill_price
        # subtract trading costs
        self.cash[e.ticker] -=  - e.charges.total()
        # print(f"\t\tUpdated: position={self.positions[e.ticker]} cash={self.cash[e.ticker]}")
        return

    def mark_to_market(self) -> None:
        """ 
        runs after receiving latest market data, and trades
        updates return_df dataframe
        """
        # calculate portfolio's return
        for ticker in self.return_df:
            latest_bar = self.mkt_data.get_latest_bars(ticker).iloc[-1]
            ticker_df = self.return_df[ticker]
            # 
            curr_position = self._get_position(ticker)
            curr_pf_value = self.cash[ticker] + curr_position * latest_bar['close']   # mtm

            ticker_df.loc[latest_bar.name] = [
                    curr_position
                    , self.cash[ticker]
                    , curr_pf_value     # portfolio value
                    , curr_pf_value/ (self.initial_capital/len(self.cash))    # cumulative return
                    , 0                 # return earned bar-on-bar
                ]
            # calculate & update daily return
            if len(ticker_df)>1:
                ticker_df.loc[latest_bar.name, "return"] = ticker_df.iloc[-1]["value"]/ticker_df.iloc[-2]["value"] - 1
            # else:
            #     # first day of strategy
            #     pass
        return

    def get_equity_curve(self, ticker:str | None = None) -> pd.DataFrame:
        """ returns equity curve for asset

        Args:
            ticker (str | None, optional): asset for which eq curve requested. Defaults to portfolio.

        Returns:
            pd.DataFrame: use column 'equity_curve'
        """
        try:
            if ticker is None:
                pf = self._create_portfolio_summary()
                return pf.copy().rename(columns={'cumulative_return': 'equity_curve'})
            return self.return_df[ticker][['cumulative_return']].copy().rename(columns={'cumulative_return': 'equity_curve'})
        except KeyError:
            print(f"Ticker {ticker} not part of strategy")
            return []
    
    def get_trades(self, ticker: str | None = None):
        try:
            if ticker is None:
                return sorted(reduce(lambda a,b: a+b, map(lambda tck: self.trades[tck], self.trades.keys())), key=lambda x: x.timestamp)
            return self.trades[ticker]
        except KeyError:
            print(f"Ticker {ticker} not part of strategy")
            return []
    
    def _create_portfolio_summary(self) -> pd.DataFrame:
        """ returns dataframe containing portfolio-level summary,
            columns = value, cumulative_return, return

        Returns:
            pd.DataFrame: _description_
        """
        if self.portfolio_df is None or len(self.portfolio_df)==0:
            df = pd.DataFrame(columns=['timestamp', 'value','cumulative_return', 'return']).set_index('timestamp')
            # df['cash'] = reduce(lambda a,b: a+b, map(lambda ticker: self.return_df[ticker]['cash'], self.return_df.keys()))
            df['value'] = reduce(lambda a,b: a+b, map(lambda ticker: self.return_df[ticker]['value'], self.return_df.keys()))
            df['cumulative_return'] = df['value']/self.initial_capital
            df['return'] = df['cumulative_return']/df['cumulative_return'].shift(1) - 1
            self.portfolio_df = df
        return self.portfolio_df

    def get_kpis(self, ticker: str | None = None) -> dict:
        df = self._create_portfolio_summary() if ticker is None else self.return_df[ticker]
        kpi_calculator = KeyPerformanceMetrics(df[['return']])
        return {
            "CAGR (%)": round(float(kpi_calculator.CAGR() * 100), 4)
            # , "Sharpe": kpi_calculator.sharpe()
            # , "Sortino": kpi_calculator.sortino()
            , "Max Drawdown (%)": round(float(kpi_calculator.drawdown() * 100), 4)
        }
    
    def get_pnl(self, ticker: str | None = None) -> dict:
        df = self._create_portfolio_summary() if ticker is None else self.return_df[ticker]
        gross_pnl = df.iloc[-1]['value'] - self.initial_capital
        return {
            "Gross P&L": round(float(gross_pnl), 2)
            , "Net P&L": round(float(gross_pnl - self.get_costs().total()), 2)
        }
    
    def get_costs(self, ticker: str | None = None) -> TransactionCharges:
        # print(f"Calculating costs from Trades...")
        return reduce(lambda a,b: a+b, map(lambda t: t.charges, self.get_trades(ticker)))
    
class KeyPerformanceMetrics:
    """ Class for calculating KPIs for a portfolio,
        using daily (bar) returns.        
    """
    def __init__(self, df:pd.DataFrame):
        self.returns_df = df    # daily returns
    
    @staticmethod
    def yearfrac(start_date: dt.datetime, end_date: dt.datetime, convention="ACTUAL/365") -> float:
        """ return year fraction between 2 dates

        Args:
            start_date
            end_date
            convention: defaults to ACTUAL/365
        """
        days = end_date - start_date
        return round((days)/dt.timedelta(365), 4)
    
    def CAGR(self) -> float:
        """ Compounded annual growth rate of a portfolio,
            whose daily returns are given in dataframe

        Args:
            return_df (pd.DataFrame): daily returns earned

        Returns:
            float: cagr value
        """
        df = self.returns_df.copy()
        df['cum_return'] = (1+df['return']).cumprod()   # column
        first_day, last_day = df.index[0].to_pydatetime(), df.index[-1].to_pydatetime()     # datetime        
        return (df["cum_return"].to_list()[-1])**self.yearfrac(first_day, last_day) - 1

    def drawdown(self) -> float:
        """ max drawdown of a portfolio (in %)

        Returns:
            float: max drawdown seen in strategy value (as %)
        """
        df = self.returns_df.copy()
        df['cum_return'] = (1+df['return']).cumprod()
        df['cum_roll_max'] = df['cum_return'].cummax()
        # df['drawdown'] = df['cum_roll_max'] - df['cum_return']
        df['drawdown_pct'] = (df['cum_roll_max'] - df['cum_return']) / df['cum_roll_max']
        return df["drawdown_pct"].max()