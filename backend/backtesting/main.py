from backend.backtesting.DataHandler import CSVMarketDataHandler
from backend.backtesting.Backtest import MACBacktest
from backend.utils.config_loader import load_configuration

def main():
    print("#### Starting Backtesting Engine...")
    
    backtest_configs = load_configuration(config_file="config.json")  # Load configs from config.json

    # Market Data source
    csv_file = (backtest_configs["market_data_csv"]["directory"] if backtest_configs["market_data_csv"]["directory"][-1]=="/" else backtest_configs["market_data_csv"]["directory"] + "/") + backtest_configs["market_data_csv"]["filename"]
    tickers = ["NIFTY50"]
    csv_data_handler = CSVMarketDataHandler(csv_file, tickers)
    
    # trading costs
    costs = backtest_configs["costs"]

    # Running Moving Average Crossover Backtest
    print("Running Moving Average Crossover Backtest, on Historcial Data from CSV")
    test = MACBacktest(tickers, mkt_data=csv_data_handler, costs=costs)   

    # # Running 12-1 Momentum Strategy Backtest
    # # print("Running 12-1 Momentum Strategy Backtest, on Historcial Data from CSV")
    # # momentum_test = MACBacktest(data_handler=csv_data_handler, broker=simulated_broker)

    test.run()
    test.get_results()
    print("#### Stopping Backtesting Engine...")


if __name__ == "__main__":
    main()