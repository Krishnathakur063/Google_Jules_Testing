import datetime
from fyers_trading_strategy import config
from fyers_trading_strategy.fyers_client import FyersClient
from fyers_trading_strategy.strategies import DirectionalStrategy, NonDirectionalStrategy

class Backtester:
    def __init__(self, start_date, end_date, initial_capital, underlying_symbol, vix_symbol):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.underlying_symbol = underlying_symbol
        self.vix_symbol = vix_symbol

        self.cash = initial_capital
        self.positions = []
        self.trades = []

        self.fyers = FyersClient()
        self.dir_strategy = DirectionalStrategy()
        self.non_dir_strategy = NonDirectionalStrategy()

    def run_backtest(self):
        print("Starting backtest...")

        # Fetch historical data for the underlying and VIX
        # Note: Fyers API might have a limit on the date range. This might need to be chunked.
        print(f"Fetching historical data for {self.underlying_symbol}...")
        underlying_data = self.fyers.get_historical_data(self.underlying_symbol, self.start_date, self.end_date)

        print(f"Fetching historical data for {self.vix_symbol}...")
        vix_data = self.fyers.get_historical_data(self.vix_symbol, self.start_date, self.end_date)

        if not underlying_data or not vix_data:
            print("Could not fetch historical data. Aborting backtest.")
            return

        # This is a simplification. In a real scenario, you'd align timestamps carefully.
        # For this backtest, we'll just use the VIX value from the same index.
        vix_map = {candle[0]: candle[4] for candle in vix_data}

        # Main backtest loop
        prev_day = None
        for i in range(len(underlying_data)):
            if i < self.dir_strategy.long_ma_period: # Need enough data for indicators
                continue

            current_candle = underlying_data[i]
            current_timestamp = current_candle[0]
            current_price = current_candle[4]
            current_day = datetime.datetime.fromtimestamp(current_timestamp).date()

            # --- 1. Handle EOD Exits ---
            if prev_day and current_day != prev_day:
                self._handle_eod_exits(prev_day)

            # --- 2. Check for new entry signals ---
            data_slice = underlying_data[:i+1]
            dir_signal = self.dir_strategy.check_entry_signal(data_slice)
            if dir_signal:
                print(f"[{datetime.datetime.fromtimestamp(current_timestamp)}] Directional signal: {dir_signal}")
                self._execute_trade(dir_signal, current_price)

            current_vix = vix_map.get(current_timestamp)
            if current_vix:
                non_dir_signal = self.non_dir_strategy.check_entry_signal(current_vix)
                if non_dir_signal:
                    print(f"[{datetime.datetime.fromtimestamp(current_timestamp)}] Non-directional signal: {non_dir_signal}")
                    self._execute_trade(non_dir_signal, current_price)

            prev_day = current_day

        # Handle exits for the very last day
        self._handle_eod_exits(prev_day)

        print("Backtest finished.")
        self.generate_report()

    def _handle_eod_exits(self, date_to_check):
        """
        Handles the End-of-Day exit logic for all open positions.
        """
        print(f"--- Checking EOD exits for {date_to_check} ---")
        date_str = date_to_check.strftime('%Y-%m-%d')

        for position in self.positions[:]:
            if position['status'] == 'OPEN':
                current_net_premium = 0
                all_legs_found = True
                for leg in position['legs']:
                    option_symbol = leg['option']['symbol']
                    # Fetch daily data for the option to get the closing price
                    option_data = self.fyers.get_historical_data(option_symbol, date_str, date_str)
                    if option_data:
                        close_price = option_data[0][4] # Closing price of the day
                        if leg['action'] == 'SELL':
                            current_net_premium -= close_price
                        else:
                            current_net_premium += close_price
                    else:
                        print(f"Could not fetch EOD data for {option_symbol}. Cannot check exit.")
                        all_legs_found = False
                        break

                if not all_legs_found:
                    continue

                # Calculate P&L. For credit spreads, P&L is change in premium.
                pnl = position['entry_premium'] - current_net_premium
                position['pnl'] = pnl

                # Using dir_strategy as the exit logic is the same for both
                exit_signal = self.dir_strategy.check_exit_conditions(position)

                if exit_signal:
                    print(f"Closing {position['strategy']} position due to {exit_signal}. P&L: {pnl}")
                    position['status'] = 'CLOSED'
                    self.cash += position['margin_required'] + pnl
                    self.positions.remove(position)

    def _execute_trade(self, signal_details, current_price):
        """
        Executes a trade based on the signal.
        """
        strategy_type = signal_details['strategy']
        option_chain = self.fyers.get_option_chain(self.underlying_symbol)

        if not option_chain:
            print("Could not fetch option chain. Skipping trade.")
            return

        trade_legs = []
        net_premium = 0
        margin_required = 0

        if strategy_type == "Bull Put Spread":
            # Sell a 0.6 delta Put, Buy a 0.3 delta Put
            put_to_sell = self._find_option(option_chain, 0.6, 'PE')
            put_to_buy = self._find_option(option_chain, 0.3, 'PE')

            if not put_to_sell or not put_to_buy:
                print("Could not find suitable options for Bull Put Spread. Skipping trade.")
                return

            trade_legs.append({'action': 'SELL', 'option': put_to_sell})
            trade_legs.append({'action': 'BUY', 'option': put_to_buy})

            net_premium = put_to_sell['ltp'] - put_to_buy['ltp']
            margin_required = (put_to_sell['strike_price'] - put_to_buy['strike_price']) - net_premium

        elif strategy_type == "Bear Call Spread":
            # Sell a 0.6 delta Call, Buy a 0.3 delta Call
            call_to_sell = self._find_option(option_chain, 0.6, 'CE')
            call_to_buy = self._find_option(option_chain, 0.3, 'CE')

            if not call_to_sell or not call_to_buy:
                print("Could not find suitable options for Bear Call Spread. Skipping trade.")
                return

            trade_legs.append({'action': 'SELL', 'option': call_to_sell})
            trade_legs.append({'action': 'BUY', 'option': call_to_buy})

            net_premium = call_to_sell['ltp'] - call_to_buy['ltp']
            margin_required = (call_to_buy['strike_price'] - call_to_sell['strike_price']) - net_premium

        elif strategy_type == "Short Straddle":
            # Sell an ATM Call and an ATM Put
            # ATM is roughly 0.5 delta
            atm_call = self._find_option(option_chain, 0.5, 'CE')
            atm_put = self._find_option(option_chain, 0.5, 'PE')

            if not atm_call or not atm_put:
                print("Could not find suitable options for Short Straddle. Skipping trade.")
                return

            trade_legs.append({'action': 'SELL', 'option': atm_call})
            trade_legs.append({'action': 'SELL', 'option': atm_put})

            net_premium = atm_call['ltp'] + atm_put['ltp']
            # Margin for short straddle is complex. This is a rough approximation.
            # It's usually the higher of the call or put margin requirement.
            # A proper calculation would require the Fyers margin calculator API.
            margin_required = max(atm_call['strike_price'], atm_put['strike_price']) * 0.20 # Rough 20% margin

        # --- Risk Management Checks ---
        if margin_required <= 0 or margin_required > self.cash:
            print("Trade requires more margin than available cash. Skipping.")
            return

        if margin_required > self.initial_capital * config.CAPITAL_ALLOCATION_PERCENTAGE:
            print("Trade exceeds max capital allocation per trade. Skipping.")
            return

        # Create position
        position = {
            'strategy': strategy_type,
            'legs': trade_legs,
            'entry_premium': net_premium,
            'margin_required': margin_required,
            'pnl': 0,
            'status': 'OPEN'
        }

        self.positions.append(position)
        self.cash -= margin_required
        self.trades.append(position) # For reporting

        print(f"Executed {strategy_type} trade. Margin: {margin_required}, Premium: {net_premium}")

    def _find_option(self, option_chain, target_delta, option_type):
        """
        Finds the option with the delta closest to the target.

        :param option_chain: The option chain data from Fyers API.
        :param target_delta: The target delta (e.g., 0.6 or 0.3).
        :param option_type: 'CE' for Call or 'PE' for Put.
        :return: The option symbol dictionary if found, else None.
        """
        best_option = None
        min_delta_diff = float('inf')

        for option in option_chain['options_chain']:
            if option['option_type'] != option_type:
                continue

            # Fyers API provides delta in the option chain, which is great.
            # We need to handle positive delta for calls and negative for puts.
            current_delta = abs(option['delta'])
            delta_diff = abs(current_delta - target_delta)

            if delta_diff < min_delta_diff:
                min_delta_diff = delta_diff
                best_option = option

        return best_option

    def generate_report(self):
        print("\n--- Backtest Report ---")
        final_capital = self.cash
        total_pnl = final_capital - self.initial_capital
        pnl_pct = (total_pnl / self.initial_capital) * 100

        num_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / num_trades) * 100 if num_trades > 0 else 0

        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Initial Capital: {self.initial_capital:,.2f}")
        print(f"Final Capital:   {final_capital:,.2f}")
        print(f"Total P&L:       {total_pnl:,.2f} ({pnl_pct:.2f}%)")
        print("-------------------------")
        print(f"Total Trades:    {num_trades}")
        print(f"Winning Trades:  {num_wins}")
        print(f"Losing Trades:   {num_losses}")
        print(f"Win Rate:        {win_rate:.2f}%")

        # Max drawdown would require tracking portfolio value over time.
        # This is a complex addition, so we will omit it for this version
        # but acknowledge it's a key metric for real analysis.
        print("\nNote: Max Drawdown calculation is not implemented in this version.")
        print("-----------------------\n")

if __name__ == '__main__':
    # Note: This requires valid Fyers credentials in config.py
    # and will attempt to connect to the API.

    # For a real run, you would use a proper date range.
    # For testing, we can use a very short period.
    # start = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime('%Y-%m-%d')
    # end = datetime.datetime.now().strftime('%Y-%m-%d')

    # backtester = Backtester(
    #     start_date=start,
    #     end_date=end,
    #     initial_capital=100000,
    #     underlying_symbol="NSE:NIFTY50-INDEX",
    #     vix_symbol="NSE:INDIAVIX-INDEX"
    # )
    # backtester.run_backtest()
    print("Backtester structure is in place. Run from main.py for a full backtest.")
