# backtesting-engine

A Python backtesting engine mimics real-world trading situations, avoids look-ahead bias & charges actual costs to predict realistic returns earned from Strategies.

The engine releases each market bar one at a time, executes the trades at the next bar's open with fixed slippage, and charges fees & taxes per Indian equities market. Its currently setup for Nifty index data for 2024-25, and runs the moving average crossover strategy. It reports the CAGR, P&L, Drawdown, Sharpe & Sortino performance metrics.

## How it works
The engine is implemented as separate modules for Market data Handlers, Strategy, Portfolio, Broker and a central event queue to manage flow. It includes simulators for external systems mainly Market data source, and Brokers. Backtest adds every Market data eventin the event queue, and it flows as-
<center>Mkt data bar -> Signal -> Order -> Fill -> Portfolio update*</center>

### Market data handlers
Data handlers manage data imports from external sources (csv, API etc), and release each bar to the event queue.
`CSVDataHandler` imports the historical data from a csv file. (Directory & name for csv file specified in config.json)

### Strategies
Strategy module receives a new bar from the event queue, and generates signals on the basis of the specific strategy. Currently supporting - 
1 Buy-and-Hold
2 Moving avergae crossover

### Portfolio
Portfolio module converts the signal into an order placed with broker, and allocates capital to each stock. 
`SimplePortfolio` assigns equal weight to all stocks on which backtest is run.

### Broker
It creates a live broker service, to execute an order.
`SimulatedBroker` implements realistic scenarios -
    - Look-ahead bias: It executes an order at the next bar's open to avoid Look-ahead bias. 
    - Slippage: Fixed slippage added to each fill, to account for price movement between bars, and delay in order execution.
    - Costs: Trading fees & taxes charged on every trade. Two categories - charges by service-providers & statutory taxes/duties. Costs are specified in `config.json`.

## Results
Each backtest reports the following KPIs & metrics for the portfolio,
    1. P&L
    2. CAGR
    3. Drawdown
    4. Equity curve

## Next,
    - Small market data sample: covers only 2y of index data. 
    - API integration: Receive market data from API for intra-day analysis.
    - Position sizing: Extend beyond equal-weight position sizing done currently.
    - Comparison with Benchmark: reporting the performance of Strategy & comapring it with a Buy-and-hold strategy, and appropriate benchmark.
    - Cover more startegies: Test, compare & identify strategies based on backtest performance.
