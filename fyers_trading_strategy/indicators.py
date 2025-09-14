import pandas as pd

def calculate_sma(data, period):
    """
    Calculates the Simple Moving Average (SMA).

    :param data: A list of candle data from Fyers API.
    :param period: The period for the SMA.
    :return: A pandas Series with the SMA values.
    """
    if len(data) < period:
        return None

    df = pd.DataFrame(data)
    # Fyers API candle format: [timestamp, open, high, low, close, volume]
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    df['close'] = pd.to_numeric(df['close'])

    sma = df['close'].rolling(window=period).mean()
    return sma

def calculate_rsi(data, period=14):
    """
    Calculates the Relative Strength Index (RSI).

    :param data: A list of candle data from Fyers API.
    :param period: The period for the RSI.
    :return: A pandas Series with the RSI values.
    """
    if len(data) < period:
        return None

    df = pd.DataFrame(data)
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    df['close'] = pd.to_numeric(df['close'])

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

if __name__ == '__main__':
    # Example usage for testing
    dummy_data = [
        [1672531200, 100, 102, 98, 101, 1000],
        [1672531500, 101, 103, 99, 102, 1200],
        [1672531800, 102, 104, 100, 103, 1100],
        [1672532100, 103, 105, 101, 104, 1300],
        [1672532400, 104, 106, 102, 105, 1400],
        [1672532700, 105, 107, 103, 106, 1500],
        [1672533000, 106, 108, 104, 107, 1600],
        [1672533300, 107, 109, 105, 108, 1700],
        [1672533600, 108, 110, 106, 109, 1800],
        [1672533900, 109, 111, 107, 110, 1900],
        [1672534200, 110, 112, 108, 111, 2000],
        [1672534500, 111, 113, 109, 112, 2100],
        [1672534800, 112, 114, 110, 113, 2200],
        [1672535100, 113, 115, 111, 114, 2300],
        [1672535400, 114, 116, 112, 115, 2400],
    ]

    sma_5 = calculate_sma(dummy_data, 5)
    rsi_14 = calculate_rsi(dummy_data, 14)

    print("SMA (5):")
    print(sma_5)
    print("\nRSI (14):")
    print(rsi_14)
