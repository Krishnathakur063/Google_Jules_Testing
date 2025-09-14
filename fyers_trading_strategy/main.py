import datetime
from fyers_trading_strategy import config
from fyers_trading_strategy.backtester import Backtester

def main():
    """
    Main function to run the backtesting process.
    """
    print("--- Starting Options Trading Strategy Backtest ---")

    # --- Configuration ---
    # Note: Make sure to fill in your Fyers API credentials in config.py

    # Define the backtest period (last 5 years)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=config.BACKTEST_YEARS * 365)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Define backtest parameters
    initial_capital = 100000  # Example: 1 Lakh
    underlying_symbol = "NSE:NIFTY50-INDEX"
    vix_symbol = "NSE:INDIAVIX-INDEX"

    print(f"Backtest Period: {start_date_str} to {end_date_str}")
    print(f"Underlying Symbol: {underlying_symbol}")
    print(f"Initial Capital: {initial_capital:,.2f}")
    print("-------------------------------------------------")

    try:
        # Initialize and run the backtester
        backtester = Backtester(
            start_date=start_date_str,
            end_date=end_date_str,
            initial_capital=initial_capital,
            underlying_symbol=underlying_symbol,
            vix_symbol=vix_symbol
        )
        backtester.run_backtest()

    except Exception as e:
        print(f"\nAn error occurred during the backtest: {e}")
        print("Please ensure your API credentials in config.py are correct and you have an active internet connection.")

    print("\n--- Backtest Run Finished ---")


if __name__ == "__main__":
    main()
