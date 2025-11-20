import pandas as pd
import data_loader
import indicators
import time

def scan_market(symbols, interval, loopback=200, use_closed_candles=True):
    """
    Scans a list of symbols for trade setups.
    
    Args:
        symbols (list): List of symbol strings (e.g., ['BTCUSDT', 'ETHUSDT'])
        interval (str): Timeframe (e.g., '15m', '1h')
        loopback (int): Number of candles to fetch
        use_closed_candles (bool): If True, ignores the current forming candle.
        
    Returns:
        pd.DataFrame: DataFrame containing active setups and metrics for each symbol.
    """
    results = []
    
    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
            
        try:
            # Fetch Data
            df = data_loader.fetch_data(symbol, interval, limit=loopback)
            if df.empty:
                continue
                
            # Filter for closed candles if requested
            if use_closed_candles:
                df = df.iloc[:-1]
                
            # Calculate Indicators
            df = indicators.calculate_indicators(df)
            df = indicators.calculate_vwap(df)
            df = indicators.check_patterns(df)
            
            # Get Current Price
            current_price = df['Close'].iloc[-1]
            
            # Check for Setup
            setup = indicators.get_trade_setup(df, current_price)
            
            if setup:
                # Calculate Confidence
                confidence, reasons = indicators.calculate_confidence(df, setup)
                
                # Add to results
                results.append({
                    'Symbol': symbol,
                    'Price': current_price,
                    'Signal': setup['Signal'],
                    'Type': setup['Type'],
                    'Entry': setup['Entry'],
                    'Stop Loss': setup['SL'],
                    'Take Profit': setup['TP'],
                    'DCA 1': setup['DCA_1'],
                    'DCA 2': setup['DCA_2'],
                    'DCA 3': setup['DCA_3'],
                    'Confidence': confidence,
                    'Reasons': ", ".join(reasons)
                })
                
            # Respect API rate limits
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            continue
            
    if not results:
        return pd.DataFrame()
        
    return pd.DataFrame(results).sort_values(by='Confidence', ascending=False)
