import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime

def fetch_data(symbol, interval, limit=200):
    """
    Fetches historical kline data from Bybit public API.
    
    Args:
        symbol (str): Trading pair, e.g., "BTCUSDT"
        interval (str): Timeframe, e.g., "15m", "1h", "4h", "1d"
        limit (int): Number of candles to fetch
        
    Returns:
        pd.DataFrame: DataFrame with Open, High, Low, Close, Volume and datetime index.
    """
    session = HTTP()
    
    # Map user-friendly intervals to Bybit API format
    interval_map = {
        "5m": "5",
        "15m": "15",
        "1h": "60",
        "2h": "120",
        "4h": "240",
        "1d": "D"
    }
    bybit_interval = interval_map.get(interval, interval)
    
    try:
        # Fetch kline data (assuming linear perps for USDT pairs)
        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=bybit_interval,
            limit=limit
        )
        
        if response['retCode'] != 0:
            print(f"Error fetching data: {response['retMsg']}")
            return pd.DataFrame()
            
        # Data is in response['result']['list']
        # Format: [startTime, open, high, low, close, volume, turnover]
        data = response['result']['list']
        
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=['startTime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Turnover'])
        
        # Bybit returns data in reverse order (newest first), so we reverse it back
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Convert types
        df['startTime'] = pd.to_numeric(df['startTime'])
        df['Open'] = df['Open'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        # Convert timestamp to datetime
        df['Date'] = pd.to_datetime(df['startTime'], unit='ms')
        df.set_index('Date', inplace=True)
        
        # Return only necessary columns
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
    except Exception as e:
        print(f"Exception in fetch_data: {e}")
        return pd.DataFrame()

def fetch_open_interest(symbol, interval, limit=200):
    """
    Fetches Open Interest data from Bybit.
    """
    session = HTTP()
    
    # Map interval to Bybit format for OI (usually matches kline)
    interval_map = {
        "15m": "15min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d"
    }
    bybit_interval = interval_map.get(interval, "1h") # Default to 1h if not found
    
    try:
        response = session.get_open_interest(
            category="linear",
            symbol=symbol,
            intervalTime=bybit_interval,
            limit=limit
        )
        
        if response['retCode'] != 0:
            return pd.DataFrame()
            
        data = response['result']['list']
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        df = df.iloc[::-1].reset_index(drop=True)
        df['timestamp'] = pd.to_numeric(df['timestamp'])
        df['openInterest'] = df['openInterest'].astype(float)
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Date', inplace=True)
        
        return df[['openInterest']]
        
    except Exception as e:
        print(f"Exception in fetch_open_interest: {e}")
        return pd.DataFrame()

def fetch_long_short_ratio(symbol, interval, limit=200):
    """
    Fetches Long/Short Ratio data from Bybit.
    """
    session = HTTP()
    
    # Map interval to Bybit format
    interval_map = {
        "15m": "15min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d"
    }
    bybit_interval = interval_map.get(interval, "1h")
    
    try:
        # Market Account Ratio
        response = session.get_long_short_ratio(
            category="linear",
            symbol=symbol,
            period=bybit_interval,
            limit=limit
        )
        
        if response['retCode'] != 0:
            return pd.DataFrame()
            
        data = response['result']['list']
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        df = df.iloc[::-1].reset_index(drop=True)
        df['timestamp'] = pd.to_numeric(df['timestamp'])
        df['buyRatio'] = df['buyRatio'].astype(float)
        df['sellRatio'] = df['sellRatio'].astype(float)
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Date', inplace=True)
        
        return df[['buyRatio', 'sellRatio']]
        
    except Exception as e:
        print(f"Exception in fetch_long_short_ratio: {e}")
        return pd.DataFrame()

        print(f"Exception in fetch_long_short_ratio: {e}")
        return pd.DataFrame()

def fetch_funding_rate(symbol):
    """
    Fetches the latest funding rate for a symbol.
    Returns a float or None.
    """
    session = HTTP()
    try:
        response = session.get_tickers(
            category="linear",
            symbol=symbol
        )
        
        if response['retCode'] != 0:
            return None
            
        result = response['result']['list']
        if not result:
            return None
            
        funding_rate = float(result[0].get('fundingRate', 0))
        return funding_rate
        
    except Exception as e:
        print(f"Exception in fetch_funding_rate: {e}")
        return None

if __name__ == "__main__":
    # Simple test
    print("Testing fetch_data...")
    df = fetch_data("BTCUSDT", "1h", 5)
    print(df)
