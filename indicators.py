import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    Adds technical indicators to the DataFrame using pure pandas.
    """
    # Ensure we have enough data
    if df is None or len(df) < 1:
        return df

    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    # Trend
    # EMA 9
    df['EMA_9'] = close.ewm(span=9, adjust=False).mean()
    # EMA 21
    df['EMA_21'] = close.ewm(span=21, adjust=False).mean()
    # SMA 200
    df['SMA_200'] = close.rolling(window=200).mean()
    
    # Volatility: Bollinger Bands (20, 2)
    sma_20 = close.rolling(window=20).mean()
    std_20 = close.rolling(window=20).std()
    df['BB_UPPER'] = sma_20 + (std_20 * 2)
    df['BB_MIDDLE'] = sma_20
    df['BB_LOWER'] = sma_20 - (std_20 * 2)
    
    # Momentum: RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean() # Simple RSI for stability
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    # Wilder's Smoothing for RSI (more accurate)
    # We'll use a simple approximation if we want to avoid complex loops, 
    # but EWM is better for Wilder's
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']
    
    # Volume SMA 20
    df['VOL_SMA_20'] = volume.rolling(window=20).mean()
    
    # ATR (14)
    # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    
    return df

def check_patterns(df):
    """
    Detects candlestick patterns.
    Adds 'Pattern' column to df.
    """
    if df is None or len(df) < 2:
        return df
        
    # Bullish Engulfing
    # Previous candle red, current candle green
    # Current open < Prev close, Current close > Prev open
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    curr_open = df['Open']
    curr_close = df['Close']
    
    is_bullish_engulfing = (prev_close < prev_open) & (curr_close > curr_open) & \
                           (curr_open <= prev_close) & (curr_close >= prev_open)
                           
    # Bearish Engulfing
    # Previous candle green, current candle red
    is_bearish_engulfing = (prev_close > prev_open) & (curr_close < curr_open) & \
                           (curr_open >= prev_close) & (curr_close <= prev_open)
                           
    # Hammer
    # Small body, long lower wick, little/no upper wick
    body = (curr_close - curr_open).abs()
    # Calculate wicks
    # Upper wick = High - max(Open, Close)
    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)
    # Lower wick = min(Open, Close) - Low
    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
    
    # Hammer definition: Lower wick > 2 * body AND Upper wick < body * 0.5 (small upper wick)
    is_hammer = (lower_wick > 2 * body) & (upper_wick < body * 0.5)
    
    df['Pattern'] = None
    df.loc[is_bullish_engulfing, 'Pattern'] = 'Bullish Engulfing'
    df.loc[is_bearish_engulfing, 'Pattern'] = 'Bearish Engulfing'
    df.loc[is_hammer, 'Pattern'] = 'Hammer'
    
    return df

def calculate_support_resistance(df, window=20):
    """
    Identifies local support and resistance levels.
    Returns a list of price levels.
    """
    if df is None or len(df) < window:
        return [], []
        
    highs = df['High']
    lows = df['Low']
    
    # Simple pivot detection: High is higher than 'window' neighbors
    # This is a simplified approach for visual reference
    
    supports = []
    resistances = []
    
    # Look for local extrema
    for i in range(window, len(df) - window):
        is_resistance = True
        is_support = True
        
        for j in range(i - window, i + window + 1):
            if highs.iloc[j] > highs.iloc[i]:
                is_resistance = False
            if lows.iloc[j] < lows.iloc[i]:
                is_support = False
                
        if is_resistance:
            resistances.append((df.index[i], highs.iloc[i]))
        if is_support:
            supports.append((df.index[i], lows.iloc[i]))
            
    return supports, resistances

def calculate_fvg(df):
    """
    Identifies Fair Value Gaps (FVG).
    Returns a list of FVGs: {'type': 'bullish'/'bearish', 'top': price, 'bottom': price, 'start_time': date, 'end_time': date}
    """
    if df is None or len(df) < 3:
        return []
        
    fvgs = []
    
    high = df['High']
    low = df['Low']
    
    # Iterate through candles (starting from index 2)
    for i in range(2, len(df)):
        # Bullish FVG: Low of candle i > High of candle i-2
        # The gap is between High[i-2] and Low[i]
        if low.iloc[i] > high.iloc[i-2]:
            gap_size = low.iloc[i] - high.iloc[i-2]
            # Filter small gaps if needed, but for now keep all
            if gap_size > 0:
                fvgs.append({
                    'type': 'bullish',
                    'top': low.iloc[i],
                    'bottom': high.iloc[i-2],
                    'start_time': df.index[i-2],
                    'end_time': df.index[i] # Visualizing up to current candle usually
                })
                
        # Bearish FVG: High of candle i < Low of candle i-2
        # The gap is between Low[i-2] and High[i]
        elif high.iloc[i] < low.iloc[i-2]:
            gap_size = low.iloc[i-2] - high.iloc[i]
            if gap_size > 0:
                fvgs.append({
                    'type': 'bearish',
                    'top': low.iloc[i-2],
                    'bottom': high.iloc[i],
                    'start_time': df.index[i-2],
                    'end_time': df.index[i]
                })
                
    return fvgs

def calculate_vwap(df):
    """
    Calculates Volume Weighted Average Price (VWAP).
    Note: Standard VWAP resets daily. Here we calculate a rolling VWAP for simplicity 
    or based on the loaded data if it's intraday.
    """
    if df is None or len(df) < 1:
        return df
        
    # Typical Price
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    # VWAP = Cumulative(TP * Volume) / Cumulative(Volume)
    # We'll calculate it for the loaded timeframe (session VWAP equivalent)
    
    vwap = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
    df['VWAP'] = vwap
    
    return df

def calculate_confidence(df, setup):
    """
    Calculates a confidence score (0-100) for the trade setup.
    """
    if not setup or df is None:
        return 0, []
        
    score = 0
    reasons = []
    
    last_row = df.iloc[-1]
    current_price = last_row['Close']
    
    # 1. Trend Alignment (20%)
    # Bullish Signal + Price > SMA 200
    if setup['Type'] == 'LONG' and current_price > last_row['SMA_200']:
        score += 20
        reasons.append("Trend is Bullish (Price > SMA 200)")
    # Bearish Signal + Price < SMA 200
    elif setup['Type'] == 'SHORT' and current_price < last_row['SMA_200']:
        score += 20
        reasons.append("Trend is Bearish (Price < SMA 200)")
    
    # 2. Momentum (20%)
    if setup['Type'] == 'LONG' and last_row['RSI'] < 60: # Room to grow
        score += 20
        reasons.append("RSI has room to grow")
    elif setup['Type'] == 'SHORT' and last_row['RSI'] > 40: # Room to drop
        score += 20
        reasons.append("RSI has room to drop")
        
    # 3. Volume (10%)
    # Current volume > Moving Average
    if last_row['Volume'] > last_row['VOL_SMA_20']:
        score += 10
        reasons.append("High Volume")
        
    # 4. Pattern Confluence (15%)
    if last_row['Pattern']:
        # Ideally check if pattern matches direction, but for now any pattern is good context
        score += 15
        reasons.append(f"Candlestick Pattern: {last_row['Pattern']}")
        
    # 5. Support/Resistance Confluence (20%)
    supports, resistances = calculate_support_resistance(df)
    
    if setup['Type'] == 'LONG':
        # Price is close to a support level
        for _, price in supports:
            if abs(current_price - price) / current_price < 0.01:
                score += 20
                reasons.append("Near Support Level")
                break
    elif setup['Type'] == 'SHORT':
        # Price is close to a resistance level
        for _, price in resistances:
            if abs(current_price - price) / current_price < 0.01:
                score += 20
                reasons.append("Near Resistance Level")
                break
    
    # 6. FVG Confluence (15%)
    fvgs = calculate_fvg(df)
    in_fvg = False
    for fvg in fvgs:
        if setup['Type'] == 'LONG' and fvg['type'] == 'bullish':
            if fvg['bottom'] <= current_price <= fvg['top'] * 1.01:
                in_fvg = True
                break
        elif setup['Type'] == 'SHORT' and fvg['type'] == 'bearish':
            if fvg['bottom'] * 0.99 <= current_price <= fvg['top']:
                in_fvg = True
                break
    
    if in_fvg:
        score += 15
        reasons.append(f"In/Near {setup['Type'].capitalize()} FVG")
        
    return min(score, 100), reasons

def get_trade_setup(df, current_price):
    """
    Generates trade setup (Entry, SL, TP, DCA).
    Returns dict or None.
    """
    if df is None or len(df) < 22:
        return None
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    if pd.isna(last_row['EMA_9']) or pd.isna(last_row['EMA_21']) or pd.isna(last_row['RSI']):
        return None
        
    # Signals
    ema_cross_up = (prev_row['EMA_9'] <= prev_row['EMA_21']) and (last_row['EMA_9'] > last_row['EMA_21'])
    ema_cross_down = (prev_row['EMA_9'] >= prev_row['EMA_21']) and (last_row['EMA_9'] < last_row['EMA_21'])
    
    rsi_oversold = last_row['RSI'] < 30
    rsi_overbought = last_row['RSI'] > 70
    
    signal = None
    trade_type = None
    
    # Long Logic
    if ema_cross_up:
        signal = "EMA Cross UP (Long)"
        trade_type = "LONG"
    elif rsi_oversold:
        signal = "RSI Oversold (Long)"
        trade_type = "LONG"
        
    # Short Logic
    elif ema_cross_down:
        signal = "EMA Cross DOWN (Short)"
        trade_type = "SHORT"
    elif rsi_overbought:
        signal = "RSI Overbought (Short)"
        trade_type = "SHORT"
        
    if not signal:
        return None
        
    atr_val = last_row['ATR'] if not pd.isna(last_row['ATR']) else (current_price * 0.02)
    
    setup = {
        'Signal': signal,
        'Type': trade_type,
        'Entry': current_price
    }
    
    if trade_type == "LONG":
        # Stop Loss: Lowest Low of last 5 candles OR Entry - 2*ATR
        last_5_low = df['Low'].tail(5).min()
        sl_price = min(last_5_low, current_price - (2 * atr_val))
        risk = current_price - sl_price
        
        setup['SL'] = sl_price
        setup['TP'] = current_price + (risk * 2) # 1:2 Risk/Reward
        
        # DCA Levels (Lower)
        setup['DCA_1'] = current_price * 0.98
        setup['DCA_2'] = current_price * 0.95
        setup['DCA_3'] = current_price * 0.90
        
    elif trade_type == "SHORT":
        # Stop Loss: Highest High of last 5 candles OR Entry + 2*ATR
        last_5_high = df['High'].tail(5).max()
        sl_price = max(last_5_high, current_price + (2 * atr_val))
        risk = sl_price - current_price
        
        setup['SL'] = sl_price
        setup['TP'] = current_price - (risk * 2) # 1:2 Risk/Reward
        
        # DCA Levels (Higher)
        setup['DCA_1'] = current_price * 1.02
        setup['DCA_2'] = current_price * 1.05
        setup['DCA_3'] = current_price * 1.10
        
    return setup

def calculate_volume_profile(df, n_rows=100):
    """
    Calculates Volume Profile Visible Range (VPVR).
    Returns a DataFrame with bins, volume, and key levels (POC, VAH, VAL).
    """
    if df is None or len(df) < 1:
        return None, {}
        
    # 1. Create Price Bins
    min_price = df['Low'].min()
    max_price = df['High'].max()
    
    # Use numpy histogram to bin volume by price
    # We use 'Close' as the price proxy for the volume in that candle
    # Ideally we'd use tick data, but for kline data, Close or Typical Price is standard approximation
    price_bins = np.linspace(min_price, max_price, n_rows + 1)
    
    # Calculate histogram
    # weights=Volume means we sum Volume for each bin
    hist, bin_edges = np.histogram(df['Close'], bins=price_bins, weights=df['Volume'])
    
    # Create DataFrame for Profile
    vp_df = pd.DataFrame({
        'Volume': hist,
        'PriceBin': bin_edges[:-1] # Use lower edge or center
    })
    
    # Center of bins for plotting
    vp_df['PriceBinCenter'] = vp_df['PriceBin'] + (bin_edges[1] - bin_edges[0]) / 2
    
    # 2. Find POC (Point of Control)
    max_vol_idx = vp_df['Volume'].idxmax()
    poc_price = vp_df.loc[max_vol_idx, 'PriceBinCenter']
    poc_volume = vp_df.loc[max_vol_idx, 'Volume']
    
    # 3. Calculate Value Area (70% of Volume)
    total_volume = vp_df['Volume'].sum()
    value_area_vol = total_volume * 0.70
    
    # Sort by volume to accumulate highest volume nodes first (standard VA logic usually expands from POC, 
    # but sorting is a robust approximation for "High Volume Nodes")
    # A more strict definition expands up/down from POC, but this is good for general "Value" identification
    vp_sorted = vp_df.sort_values(by='Volume', ascending=False)
    vp_sorted['CumVol'] = vp_sorted['Volume'].cumsum()
    
    # Filter for Value Area
    va_df = vp_sorted[vp_sorted['CumVol'] <= value_area_vol]
    
    vah = va_df['PriceBinCenter'].max()
    val = va_df['PriceBinCenter'].min()
    
    levels = {
        'POC': poc_price,
        'VAH': vah,
        'VAL': val,
        'POC_Volume': poc_volume
    }
    
    return vp_df, levels
