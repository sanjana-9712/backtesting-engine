from abc import ABC

import pandas as pd

from backend.backtesting.DataHandler import DataHandler, EventHandler
from backend.backtesting.Event import MarketEvent, SignalEvent


class Strategy(EventHandler[MarketEvent, SignalEvent], ABC):
    """
    Strategy class that generates signals based on market data received from source
    """
    input_event: MarketEvent
    output_event: SignalEvent

    def _get_latest_bar(self, ticker:str):
        return self.hist_mkt_data[ticker].iloc[-1]

# ##################################################################################################################
# ###################################### STRATEGIES' IMPLEMENTATION ######################################
# ##################################################################################################################

class BuyAndHoldStrategy(Strategy):
    """ 
    A simple Strategy that buys all tickers at start of strategy, 
    and holds them
    """
    def __init__(self):
        self._tickers_bought = {}   # tells whether a ticker has been bought earlier

    def on(self, e: MarketEvent) -> SignalEvent:
        """ In buy-and-hold a Buy signal is generated at start of strategy
        for a ticker and then no additional signals

        Args:
            e (MarketEvent): mkt event received

        Returns:
            SignalEvent: signal generated accordingly
        """
        if e.ticker not in self._tickers_bought:
            # buy signal
            self._tickers_bought[e.ticker] = 1
            return SignalEvent(timestamp=e.timestamp, ticker=e.ticker, signal="BUY")
        return
        
class MovingAvgCrossoverStrategy(Strategy):
    """
    Moving avergae crossover strategy with a fast & slow moving avergaes,
    either simple, or exponential
    Default window sizes, short=12, long=26
    """
    def __init__(self, md: DataHandler, short_window=12, long_window=26):
        self.mkt_data = md
        self.short_window = short_window
        self.long_window = long_window
        # maps ticker to its current position LONG/OUT
        self._bought = {ticker: "OUT" for ticker in md.tickers}
        # dataframe for fast & slow moving averages, for each ticker
        self._df_ti = {ticker: pd.DataFrame(columns=['timestamp','fast_ma', 'slow_ma']).set_index('timestamp') for ticker in md.tickers}
    
    def on(self, e: MarketEvent) -> SignalEvent:
        """ generates signal based on fast & slow MAs.
        Buy when fast crosses slow, and Sell when slow crosses fast
        Args:
            e (MarketEvent): bar received

        Returns:
            SignalEvent: corresponding signal
        """
        try:
            temp = self.mkt_data.get_latest_bars(e.ticker, self.long_window)    # a dataframe
        except Exception as e:
            print(e)
            raise
        else:
            if temp is not None:
                # calculating moving averages...
                self._df_ti[e.ticker].loc[e.timestamp] = [
                    temp['close'].rolling(window=self.short_window).mean().iloc[-1]
                    , temp['close'].rolling(window=self.long_window).mean().iloc[-1]
                ]
                last_bar = self._df_ti[e.ticker].loc[e.timestamp]
                if not pd.isna(last_bar['fast_ma']) and not pd.isna(last_bar['slow_ma']):
                    # both Fast & slow MAs exist
                    if last_bar['fast_ma'] > last_bar['slow_ma'] and self._bought.get(e.ticker, "OUT")=="OUT":
                        # fast ma cuts from below
                        self._bought[e.ticker] = "LONG"
                        return SignalEvent(timestamp=e.timestamp, ticker=e.ticker, signal="BUY")
                    elif last_bar['fast_ma'] < last_bar['slow_ma'] and self._bought.get(e.ticker, "OUT")=="LONG":
                        self._bought[e.ticker] = "OUT"
                        return SignalEvent(timestamp=e.timestamp, ticker=e.ticker, signal="SELL")
        # Compute moving avergaes using old calculated MAs, and new event
        # Simple moving averages
        # ticker_df['fast_ma'] = ticker_df['close'].rolling(window=self.short_window).mean()
        # ticker_df['slow_ma'] = ticker_df['close'].rolling(window=self.long_window).mean()
        # # using Exponential Moving avg for smoothing
        # ticker_df['fast_ma'] = ticker_df['close'].ewm(span=self.short_window, min_periods=self.short_window).mean()
        # ticker_df['slow_ma'] = ticker_df['close'].ewn(span=self.short_window, min_periods=self.long_window).mean()        
        return

class MomentumStrategy12To1(Strategy):
    """
    12-1 momentum strategy
    """
    def __init__(self):
        super().__init__()
    def on(self, e: MarketEvent) -> SignalEvent:
        print(f"event for TICKER={e.ticker}")
        # Implement 12-to-1 momentum logic here
        # return SignalEvent(ticker=e.ticker, signal="HOLD")  # Placeholder
        return NotImplementedError("12-1 momentum strategy not implemented yet.")

