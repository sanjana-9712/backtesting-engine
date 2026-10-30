# backtesting-engine

An event-based backtesting engine that mimics real-world trading situations, avoids look-ahead bias & charges actual costs to predict realistic returns earned from Strategies.

The Backtesting engine is build using separate modules for Market data Handlers, Strategy, Portfolio, Broker and a central event queue to manage flow. It includes simulators for external systems mainly Market data source, and Brokers. The engine adds daily data bar by bar in the event queue, and sets in motion the strategy logic of the backtest.

                                    *Mkt data -> Signal -> Order -> Fill -> Portfolio update*

## Market data handlers
Data handlers manage importing of data from external sources (API, csv), and release them to the event queue in a squential manner.
Currently, supports CSVDataHandler that imports the historical data from a csv file. (Directory & name for csv file specified in config.json)
Currently, Nifty50 index historical data from 01-jan-24 to 31-dec-2025, downloaded as CSV from NSE's website (bhavcopy) is present in the backend/backtesting/data/ folder.

## Strategy
Strategy module generates signals on the basis of new market data received for the specific strategy. Currently supporting - 
1 Buy-and-Hold
2 Moving avergae crossover

## Portfolio
Portfolio module performs all portfolio management functions. It generates the order to place with broker, based on signal, and allocates capital to each stock. Currently, the SimplePortfolio implementation assigns equal weight to all stocks on whcih backtest is run.

## Broker module
It creates a live broker service, which executes an order placed with it, at the next bar's open along with some slippage. This avoids Lookahead bias. Slippage accounts for price movement between bars, and during any latency in order execution
Further, the Simulated Broker charges realistic costs on every trade. These trading costs can be broadly divided into 2 categories - charges by service-providers & statutory taxes/duties. These costs (as % of turnover) are specified in the config file (config.json) for all major types of trades - Delivery/Cash, Intra-day & F&Os.

## Reporting
The engine reports the following KPIs & metrics for the portfolio,
1 P&L
2 CAGR
3 Drawdown
4 Equity curve