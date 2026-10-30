from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

import pandas as pd

from backend.backtesting.Event import Event, MarketEvent

# ##################################################################################################################
I = TypeVar("I", bound=Event) # generic type representing input event in a handler
O = TypeVar("O", bound=Event) # generic type representing output event in a handler

class EventHandler(ABC, Generic[I, O]):
    """
    Abstract class for Event handlers.
    """
    input_event: I  # input event
    output_event: O # output event
    @abstractmethod
    def on(self, e: I) -> O:
        raise NotImplementedError("Method must be implemented by subclasses.")

# ##################################################################################################################
class DataHandler(ABC):
    """
    Abstract Class for processing new market events in the Backtesting Engine. 
    """
    @abstractmethod
    def has_next(self) -> bool:
        """
        Check if there are more market events to process
        Returns:
            bool: True if there are more market events, False otherwise
        """
        raise NotImplementedError("Method must be implemented by subclasses.")
    @abstractmethod
    def get_and_update_latest_bars(self) -> list[MarketEvent]:
        """
        returns all market events received from the data source
        Returns:
            list[MarketEvent]: The next market event
        """
        raise NotImplementedError("Method must be implemented by subclasses.")
    
    @abstractmethod
    def get_latest_timestamp(self, ticker: str) -> datetime:
        """ returns timestamp of latest bar close for given ticker

        Args:
            ticker (str)

        Returns:
            datetime: latest bar close timestamp
        """
        raise NotImplementedError('Method must be implemented by subclasses.')
    @abstractmethod
    def get_latest_bars(self, ticker, n=1):
        """ returns latest n bars for given ticker

        Args:
            ticker (str): for which bars req
            n (int, optional): no of bars requested. Defaults to 1.
        """
        raise NotImplementedError('Method must be implemented by subclasses.')
    @abstractmethod
    def get_mkt_bar(self, ticker: str, t: datetime):
        """ returns the bar with timestamp t, from historical data

        Args:
            ticker (str): ticker for which bar's requested
            t (datetime): timestamp

        Returns:
            _type_: ohlcv row for (t+1)
        """
        raise NotImplementedError('Method must be implemented by subclasses.')

# ###################################### MARKET DATA HANDLERS IMPLEMENTATION ######################################
class CSVMarketDataHandler(DataHandler):
    """
    Data handler for processing market data from CSV files
    """
    def __init__(self, csv_file: str, tickers: list[str]):
        self.csv_file = csv_file
        self.tickers = tickers
        self._ticker_data = {}   # maps ticker to its df
        self._load_csv_data()
        self._latest_bar_generators = {}    # maps ticker to its generator
        self._create_generators()
        self._latest_mkt_data = {}  # data structure containing received mkt bars, for each ticker
        self.continue_backtest = True

    # def _load_csv_data(self) -> pd.DataFrame:
    def _load_csv_data(self) -> None:
        """ reads csv file for each ticker, and converts it to dataframes
            TODO: column nos hard-coded as per NSE's csv. No tickers. 

        """
        for ticker in self.tickers:
            df = pd.read_csv(self.csv_file
                            , index_col=0
                            , usecols=[0,1,2,3,4,5]
                            , parse_dates=True)
            # Basic Data handling
            df.columns = ['open', 'high', 'low', 'close', 'volume']  # Rename columns to match expected names
            df.sort_index(inplace=True)  # Sort by date
            df.index = pd.to_datetime(df.index)  # Ensure index is datetime
        
            df["ticker"] = "NIFTY50"  # TODO: Hardcoded for now, as NSE's csv doesn't have tickers
            # 
            self._ticker_data[ticker] = df

        return

    def _create_generators(self) -> None:
        """ creates generators for each ticker
            each generator yields a Namedtuple with classname 'ohlcv_bar'
        """
        for ticker in self.tickers:
            self._latest_bar_generators[ticker] = (row for row in self._ticker_data[ticker].itertuples(index=True, name="ohlcv_bar"))
    
    def _to_market_event_obj(self, row):
        mp = row._asdict()
        # print(mp, "|", type(mp['Index']))
        timestmp = mp.pop('Index')
        mp["timestamp"] = timestmp.to_pydatetime()
        return MarketEvent(**mp)
    
    def has_next(self) -> bool:
        # return self.current_index < len(self.data)
        return self.continue_backtest
    
    def get_and_update_latest_bars(self) -> list[MarketEvent]:
        bars = []
        for ticker in self.tickers:
            try:
                bar = next(self._latest_bar_generators[ticker])
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    bars.append(bar)
        self._update_latest_market_data(bars=bars)
        return [self._to_market_event_obj(bar) for bar in bars]
    
    def _update_latest_market_data(self, *args, **kwargs) -> None:
        """updates received mkt data bars with latest bar,
            accepts one of following keyword arguments:
                bar: single bar
                bars: list of bars
            
        """
        latest_bars = {}   # stores ticker-wise rows (Namedtuples ('ohlcv_bar')) that need to be updated
        # process_bars = []
        if 'bar' in kwargs:
            process_bars = [kwargs['bar']]
        elif 'bars' in kwargs:
            process_bars = kwargs['bars']
            
        if process_bars and isinstance(process_bars, list) and len(process_bars)>0:
            for bar in process_bars:
                ticker_rows = latest_bars.setdefault(bar.ticker, [])
                ticker_rows.append(bar)
            for ticker in latest_bars:
                # add new rows to data structure containing received mkt bars
                new_rows = pd.DataFrame(latest_bars[ticker]).set_index('Index')  # 'Index' field contains timestamp
                ticker_df = self._latest_mkt_data.setdefault(ticker
                                                             , pd.DataFrame(columns=['ticker', 'open', 'high', 'low', 'close', 'volume']))
                self._latest_mkt_data[ticker] = pd.concat([ticker_df, new_rows])
        return

    def get_latest_timestamp(self, ticker) -> datetime | None:
        try: 
            ticker_df = self._latest_mkt_data[ticker]
        except KeyError:
            print(f"No Data present for {ticker}.")
        else:
            if ticker_df is not None and len(ticker_df)>=1:
                return ticker_df.iloc[-1].name.to_pydatetime()
        return None
    
    def get_latest_bars(self, ticker, n=1):
        try: 
            ticker_df = self._latest_mkt_data[ticker]
        except KeyError:
            print(f"No Data received for {ticker}.")
        else:
            if ticker_df is not None and len(ticker_df)>=n:
                return ticker_df.iloc[-n:]   # returns a dataframe
        return None
        
    def get_mkt_bar(self, ticker: str, t: datetime):
        try: 
            ticker_df = self._ticker_data[ticker]
            return ticker_df.loc[t]
        except KeyError:
            print(f"Historical Data for {ticker}, {t} not found")
            raise
