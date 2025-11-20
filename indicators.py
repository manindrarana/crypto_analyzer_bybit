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
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    
    # ADX (14)
    up = high - high.shift(1)
    down = low.shift(1) - low
    
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    
    plus_dm_s = pd.Series(plus_dm).ewm(alpha=1/14, adjust=False).mean()
    minus_dm_s = pd.Series(minus_dm).ewm(alpha=1/14, adjust=False).mean()
    tr_s = tr.ewm(alpha=1/14, adjust=False).mean()
    
    plus_di = 100 * (plus_dm_s / tr_s)
    minus_di = 100 * (minus_dm_s / tr_s)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    
    return df

def check_patterns(df):
    """
    Detects candlestick patterns.
    """
    if df is None or len(df) < 2:
        return df
        
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    curr_open = df['Open']
    curr_close = df['Close']
    
    # Bullish Engulfing
    is_bullish_engulfing = (prev_close < prev_open) & (curr_close > curr_open) & \
                           (curr_open <= prev_close) & (curr_close >= prev_open)
                           
    # Bearish Engulfing
    is_bearish_engulfing = (prev_close > prev_open) & (curr_close < curr_open) & \
                           (curr_open >= prev_close) & (curr_close <= prev_open)
                           
    # Hammer
    body = (curr_close - curr_open).abs()
    upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)
    lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
    is_hammer = (lower_wick > 2 * body) & (upper_wick < body * 0.5)
    
    df['Pattern'] = None
    df.loc[is_bullish_engulfing, 'Pattern'] = 'Bullish Engulfing'
    df.loc[is_bearish_engulfing, 'Pattern'] = 'Bearish Engulfing'
    df.loc[is_hammer, 'Pattern'] = 'Hammer'
    
    return df

def calculate_support_resistance(df, window=20):
    """
    Calculates Support and Resistance levels based on local min/max.
    """
    if df is None or len(df) < window:
        return [], []
        
    supports = []
    resistances = []
    
    for i in range(window, len(df) - window):
        if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            supports.append((df.index[i], df['Low'].iloc[i]))
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            resistances.append((df.index[i], df['High'].iloc[i]))
            
    return supports[-5:], resistances[-5:]

def calculate_fvg(df):
    """
    Identifies Fair Value Gaps (FVG).
    """
    fvgs = []
    if df is None or len(df) < 3:
        return fvgs
        
    for i in range(2, len(df)):
        if df['High'].iloc[i-2] < df['Low'].iloc[i]:
            fvgs.append({
                'type': 'bullish',
                'top': df['Low'].iloc[i],
                'bottom': df['High'].iloc[i-2],
                'start_time': df.index[i]
            })
        elif df['Low'].iloc[i-2] > df['High'].iloc[i]:
            fvgs.append({
                'type': 'bearish',
                'top': df['Low'].iloc[i-2],
                'bottom': df['High'].iloc[i],
                'start_time': df.index[i]
            })
            
    return fvgs[-10:]

def calculate_vwap(df):
    """
    Calculates VWAP.
    """
    if df is None or len(df) < 1:
        return df
        
    v = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * v).cumsum() / v.cumsum()
    return df

def calculate_confidence(df, setup):
    """
    Calculates a confidence score (0-100) for the trade setup.
    """
    if not setup or df is None:
        return 0, []
        
    score = 50
    reasons = []
    
    last_row = df.iloc[-1]
    
    # 1. Trend Alignment
    if setup['Type'] == 'LONG':
        if last_row['EMA_9'] > last_row['EMA_21']:
            score += 10
            reasons.append("Trend is Bullish (EMA)")
        if last_row['Close'] > last_row['SMA_200']:
            score += 10
            reasons.append("Above 200 SMA")
    elif setup['Type'] == 'SHORT':
        if last_row['EMA_9'] < last_row['EMA_21']:
            score += 10
            reasons.append("Trend is Bearish (EMA)")
        if last_row['Close'] < last_row['SMA_200']:
            score += 10
            reasons.append("Below 200 SMA")
            
    # 2. RSI Context
    if setup['Type'] == 'LONG' and last_row['RSI'] < 40:
        score += 10
        reasons.append("RSI in Bullish Zone")
    elif setup['Type'] == 'SHORT' and last_row['RSI'] > 60:
        score += 10
        reasons.append("RSI in Bearish Zone")
        
    # 3. Volume Confirmation
    if last_row['Volume'] > last_row['VOL_SMA_20']:
        score += 10
        reasons.append("High Volume")
        
    # 4. Pattern Confirmation
    if setup['Type'] == 'LONG' and last_row['Pattern'] in ['Bullish Engulfing', 'Hammer']:
        score += 10
        reasons.append(f"Bullish Pattern: {last_row['Pattern']}")
    elif setup['Type'] == 'SHORT' and last_row['Pattern'] in ['Bearish Engulfing']:
        score += 10
        reasons.append(f"Bearish Pattern: {last_row['Pattern']}")
        
    return min(score, 100), reasons

def get_trade_setup(df, current_price, use_trend_filter=False, use_volume_filter=False, use_adx_filter=False, use_macd_filter=False):
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
    # Check for crossover in the last 3 candles to catch recent moves
    ema_cross_up = False
    ema_cross_down = False
    
    for i in range(1, 4): # Check last 3 candles (indices -1, -2, -3)
        curr = df.iloc[-i]
        prev = df.iloc[-i-1]
        if (prev['EMA_9'] <= prev['EMA_21']) and (curr['EMA_9'] > curr['EMA_21']):
            ema_cross_up = True
            break
        if (prev['EMA_9'] >= prev['EMA_21']) and (curr['EMA_9'] < curr['EMA_21']):
            ema_cross_down = True
            break
    
    rsi_oversold = last_row['RSI'] < 35 # Relaxed from 30
    rsi_overbought = last_row['RSI'] > 65 # Relaxed from 70
    
    signal = None
    trade_type = None
    
    # Long Logic
    if ema_cross_up:
        signal = "Recent EMA Cross UP (Long)"
        trade_type = "LONG"
    elif rsi_oversold:
        signal = "RSI Oversold (Long)"
        trade_type = "LONG"
        
    # Short Logic
    elif ema_cross_down:
        signal = "Recent EMA Cross DOWN (Short)"
        trade_type = "SHORT"
    elif rsi_overbought:
        signal = "RSI Overbought (Short)"
        trade_type = "SHORT"
        
    if not signal:
        return None
        
    # --- Filters ---
    
    # 1. Trend Filter (SMA 200)
    if use_trend_filter:
        sma_200 = last_row.get('SMA_200')
        if pd.isna(sma_200):
            return None 
        if trade_type == "LONG" and current_price <= sma_200:
            return None 
        if trade_type == "SHORT" and current_price >= sma_200:
            return None 
            
    # 2. Volume Filter (Volume > Volume SMA)
    if use_volume_filter:
        vol_sma = last_row.get('VOL_SMA_20')
        volume = last_row.get('Volume')
        if pd.isna(vol_sma) or pd.isna(volume):
            pass 
        elif volume <= vol_sma:
            return None 
            
    # 3. ADX Filter (Trend Strength > 25)
    if use_adx_filter:
        adx = last_row.get('ADX')
        if pd.isna(adx):
            pass
        elif adx <= 25:
            return None 
            
    # 4. MACD Filter (Momentum)
    if use_macd_filter:
        macd = last_row.get('MACD')
        macd_signal = last_row.get('MACD_SIGNAL')
        if pd.isna(macd) or pd.isna(macd_signal):
            pass
        else:
            if trade_type == "LONG" and macd <= macd_signal:
                return None 
            if trade_type == "SHORT" and macd >= macd_signal:
                return None 
            
    atr_val = last_row['ATR'] if not pd.isna(last_row['ATR']) else (current_price * 0.02)
    
    setup = {
        'Signal': signal,
        'Type': trade_type,
        'Entry': current_price
    }
    
    if trade_type == "LONG":
        last_5_low = df['Low'].tail(5).min()
        sl_price = min(last_5_low, current_price - (2 * atr_val))
        risk = current_price - sl_price
        setup['SL'] = sl_price
        setup['TP'] = current_price + (risk * 2)
        setup['DCA_1'] = current_price * 0.98
        setup['DCA_2'] = current_price * 0.95
        setup['DCA_3'] = current_price * 0.90
        
    elif trade_type == "SHORT":
        last_5_high = df['High'].tail(5).max()
        sl_price = max(last_5_high, current_price + (2 * atr_val))
        risk = sl_price - current_price
        setup['SL'] = sl_price
        setup['TP'] = current_price - (risk * 2)
        setup['DCA_1'] = current_price * 1.02
        setup['DCA_2'] = current_price * 1.05
        setup['DCA_3'] = current_price * 1.10
        
    return setup

def calculate_volume_profile(df, n_rows=100):
    """
    Calculates Volume Profile Visible Range (VPVR).
    """
    if df is None or len(df) < 1:
        return None, {}
        
    min_price = df['Low'].min()
    max_price = df['High'].max()
    price_bins = np.linspace(min_price, max_price, n_rows + 1)
    hist, bin_edges = np.histogram(df['Close'], bins=price_bins, weights=df['Volume'])
    
    vp_df = pd.DataFrame({
        'Volume': hist,
        'PriceBin': bin_edges[:-1]
    })
    vp_df['PriceBinCenter'] = vp_df['PriceBin'] + (bin_edges[1] - bin_edges[0]) / 2
    
    max_vol_idx = vp_df['Volume'].idxmax()
    poc_price = vp_df.loc[max_vol_idx, 'PriceBinCenter']
    poc_volume = vp_df.loc[max_vol_idx, 'Volume']
    
    total_volume = vp_df['Volume'].sum()
    value_area_vol = total_volume * 0.70
    vp_sorted = vp_df.sort_values(by='Volume', ascending=False)
    vp_sorted['CumVol'] = vp_sorted['Volume'].cumsum()
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
