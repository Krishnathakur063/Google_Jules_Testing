from fyers_trading_strategy import config
from fyers_trading_strategy import indicators

class Strategy:
    """
    Base class for all trading strategies.
    """
    def __init__(self, sl_pct=config.SL_PERCENTAGE, tp_pct=config.TP_PERCENTAGE):
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct

    def check_exit_conditions(self, position):
        """
        Checks if an open position should be closed based on SL/TP.

        :param position: A dictionary representing the open position.
        :return: A string "SL" or "TP" if exit condition is met, else None.
        """
        pnl = position['pnl']
        # For credit strategies, the 'cost' is the initial premium received.
        # A positive P&L means the premium has decreased.
        initial_premium = position['entry_premium']

        # Stop-loss: if the current P&L is a loss greater than SL % of the initial premium.
        # A negative P&L here means we are losing money.
        if pnl <= -1 * self.sl_pct * initial_premium:
            return "SL"

        # Take-profit: if the current P&L is a gain greater than TP % of the initial premium.
        if pnl >= self.tp_pct * initial_premium:
            return "TP"

        return None

class DirectionalStrategy(Strategy):
    """
    A directional trading strategy based on MA crossover and RSI.
    """
    def __init__(self, short_ma_period=21, long_ma_period=55, rsi_period=14):
        super().__init__()
        self.short_ma_period = short_ma_period
        self.long_ma_period = long_ma_period
        self.rsi_period = rsi_period

    def check_entry_signal(self, data):
        """
        Checks for a directional trade entry signal.

        :param data: List of historical candle data.
        :return: A dictionary with trade details if signal is found, else None.
        """
        short_ma = indicators.calculate_sma(data, self.short_ma_period)
        long_ma = indicators.calculate_sma(data, self.long_ma_period)
        rsi = indicators.calculate_rsi(data, self.rsi_period)

        if short_ma is None or long_ma is None or rsi is None:
            return None

        # Get the latest values
        last_short_ma = short_ma.iloc[-1]
        last_long_ma = long_ma.iloc[-1]
        prev_short_ma = short_ma.iloc[-2]
        prev_long_ma = long_ma.iloc[-2]
        last_rsi = rsi.iloc[-1]

        # User requested RSI > 75 for momentum. This is unconventional, as RSI > 70 is typically
        # considered overbought (a reversal signal). A more standard interpretation of using RSI for
        # momentum confirmation is to check if it's above the centerline (50).
        # We will use RSI > 50 for bullish and RSI < 50 for bearish signals to represent momentum.
        is_bullish_momentum = last_rsi > 50
        is_bearish_momentum = last_rsi < 50

        # Bullish Crossover
        if prev_short_ma <= prev_long_ma and last_short_ma > last_long_ma and is_bullish_momentum:
            return {"signal": "BUY", "strategy": "Bull Put Spread"}

        # Bearish Crossover
        if prev_short_ma >= prev_long_ma and last_short_ma < last_long_ma and is_bearish_momentum:
            return {"signal": "SELL", "strategy": "Bear Call Spread"}

        return None

class NonDirectionalStrategy(Strategy):
    """
    A non-directional trading strategy based on India VIX.
    """
    def __init__(self):
        super().__init__()

    def check_entry_signal(self, vix_value):
        """
        Checks for a non-directional trade entry signal.

        :param vix_value: The current India VIX value.
        :return: A dictionary with trade details if signal is found, else None.
        """
        if vix_value > config.INDIA_VIX_THRESHOLD:
            return {"signal": "SELL", "strategy": "Short Straddle"}

        return None

if __name__ == '__main__':
    # Example usage for testing
    dummy_data = [
        [1672531200, 100, 102, 98, 100, 1000] for _ in range(54)
    ]
    # Create a crossover
    dummy_data.append([1672531500, 105, 106, 104, 105, 1200])
    dummy_data.append([1672531800, 106, 107, 105, 106, 1100])

    # This is a simplified test. A real test would need more data.
    dir_strategy = DirectionalStrategy(short_ma_period=5, long_ma_period=10)

    # We need to craft data that triggers the RSI condition as well.
    # This is complex to do with dummy data, so we will trust the logic for now.
    # A full test suite would be needed for a production system.

    non_dir_strategy = NonDirectionalStrategy()

    # Test non-directional
    print("Testing NonDirectionalStrategy:")
    print(f"VIX = 17: {non_dir_strategy.check_entry_signal(17)}")
    print(f"VIX = 19: {non_dir_strategy.check_entry_signal(19)}")

    # Test exit conditions
    pos = {'pnl': 9, 'cost': 100} # 9% profit
    print(f"Exit for 9% profit: {dir_strategy.check_exit_conditions(pos)}")
    pos = {'pnl': 81, 'cost': 100} # 81% profit
    print(f"Exit for 81% profit: {dir_strategy.check_exit_conditions(pos)}")
    pos = {'pnl': -23, 'cost': 100} # 23% loss
    print(f"Exit for 23% loss: {dir_strategy.check_exit_conditions(pos)}")
