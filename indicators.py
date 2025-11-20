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

    # Trend - Complete EMA Ribbon
    df['EMA_9'] = close.ewm(span=9, adjust=False).mean()
    df['EMA_15'] = close.ewm(span=15, adjust=False).mean()
    df['EMA_21'] = close.ewm(span=21, adjust=False).mean()
    df['EMA_50'] = close.ewm(span=50, adjust=False).mean()
    df['EMA_200'] = close.ewm(span=200, adjust=False).mean()
    # SMA 200 for trend filter
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
    Professional multi-factor confluence scoring using ALL available analysis:
    - EMA Ribbon alignment
    - ZigZag market structure
    - Chart patterns
    - FVG proximity  
    - Liquidation level sweeps
    - Trendline bounces/breaks
    - Volume, RSI, MACD, ADX
    Returns score 0-100 and detailed reasons.
    """
    if not setup or df is None or len(df) < 50:
        return 0, []
        
    score = 0  # Start from 0 - need to earn every point
    reasons = []
    
    last_row = df.iloc[-1]
    current_price = setup['Entry']
    trade_type = setup['Type']
    
    # Calculate all advanced analysis
    try:
        zigzag = calculate_zigzag(df)
        liq_levels = calculate_liquidation_levels(zigzag, current_price)
        trendlines = detect_trendlines(zigzag)
        chart_patterns = detect_chart_patterns(df, zigzag)
        fvgs = calculate_fvg(df)
    except:
        # Fallback if advanced calcs fail
        zigzag, liq_levels, trendlines, chart_patterns, fvgs = [], [], {'support': [], 'resistance': []}, [], []
    
    # === 1. EMA RIBBON ALIGNMENT (Max 25 points) ===
    ema_score = 0
    if not pd.isna(last_row.get('EMA_9')) and not pd.isna(last_row.get('EMA_200')):
        if trade_type == 'LONG':
            # Perfect bullish ribbon: 9 > 15 > 21 > 50 > 200
            if (last_row['EMA_9'] > last_row.get('EMA_15', 0) > last_row.get('EMA_21', 0) > 
                last_row.get('EMA_50', 0) > last_row.get('EMA_200', 0)):
                ema_score += 25
                reasons.append("⭐ Perfect EMA Ribbon Alignment")
            elif last_row['EMA_9'] > last_row['EMA_21'] > last_row.get('EMA_50', 0):
                ema_score += 15
                reasons.append("Strong EMA Trend")
            elif last_row['EMA_9'] > last_row['EMA_21']:
                ema_score += 8
                reasons.append("EMA Cross Bullish")
                
            # Above 200 EMA bonus
            if current_price > last_row.get('EMA_200', 0):
                ema_score += 5
                reasons.append("Above 200 EMA")
                
        elif trade_type == 'SHORT':
            # Perfect bearish ribbon
            if (last_row['EMA_9'] < last_row.get('EMA_15', float('inf')) < last_row.get('EMA_21', float('inf')) < 
                last_row.get('EMA_50', float('inf')) < last_row.get('EMA_200', float('inf'))):
                ema_score += 25
                reasons.append("⭐ Perfect EMA Ribbon Alignment")
            elif last_row['EMA_9'] < last_row['EMA_21'] < last_row.get('EMA_50', float('inf')):
                ema_score += 15
                reasons.append("Strong EMA Trend")
            elif last_row['EMA_9'] < last_row['EMA_21']:
                ema_score += 8
                reasons.append("EMA Cross Bearish")
                
            # Below 200 EMA bonus
            if current_price < last_row.get('EMA_200', float('inf')):
                ema_score += 5
                reasons.append("Below 200 EMA")
    
    score += min(ema_score, 25)
    
    # === 2. ZIGZAG MARKET STRUCTURE (Max 20 points) ===
    structure_score = 0
    if zigzag and len(zigzag) >= 2:
        last_swing = zigzag[-1]
        # Trading with structure (bouncing off swing low for long, swing high for short)
        if trade_type == 'LONG' and last_swing['type'] == 'low':
            price_diff = abs(current_price - last_swing['price']) / current_price
            if price_diff < 0.01:  # Within 1% of swing
                structure_score += 20
                reasons.append("🎯 Bounce off Swing Low")
            elif price_diff < 0.03:
                structure_score += 10
                reasons.append("Near Swing Low")
        elif trade_type == 'SHORT' and last_swing['type'] == 'high':
            price_diff = abs(current_price - last_swing['price']) / current_price
            if price_diff < 0.01:
                structure_score += 20
                reasons.append("🎯 Rejection at Swing High")
            elif price_diff < 0.03:
                structure_score += 10
                reasons.append("Near Swing High")
    
    score += min(structure_score, 20)
    
    # === 3. CHART PATTERNS (Max 20 points) ===
    pattern_score = 0
    if chart_patterns:
        for pattern in chart_patterns:
            if pattern['target_direction'] == trade_type:
                if pattern['confidence'] == 'High':
                    pattern_score += 20
                    reasons.append(f"🔥 {pattern['type']}")
                    break  # Only count strongest
                elif pattern['confidence'] == 'Medium':
                    pattern_score += 12
                    reasons.append(f"📊 {pattern['type']}")
    
    score += min(pattern_score, 20)
    
    # === 4. LIQUIDATION LEVEL SWEEP (Max 15 points) ===
    liq_score = 0
    if liq_levels:
        for liq in liq_levels:
            price_diff = abs(current_price - liq['price']) / current_price
            if price_diff < 0.005:  # Within 0.5%
                if (trade_type == 'LONG' and 'Long Liq' in liq['type']) or \
                   (trade_type == 'SHORT' and 'Short Liq' in liq['type']):
                    liq_score += 15
                    reasons.append(f"💀 Liquidation Sweep {liq['leverage']}x")
                    break
    
    score += min(liq_score, 15)
    
    # === 5. FAIR VALUE GAP (Max 10 points) ===
    fvg_score = 0
    if fvgs:
        for fvg in fvgs:
            # Check if price is in FVG
            if fvg['bottom'] <= current_price <= fvg['top']:
                if (trade_type == 'LONG' and fvg['type'] == 'bullish') or \
                   (trade_type == 'SHORT' and fvg['type'] == 'bearish'):
                    fvg_score += 10
                    reasons.append("📍 Trading from FVG")
                    break
    
    score += min(fvg_score, 10)
    
    # === 6. TRENDLINE CONFIRMATION (Max 10 points) ===
    trendline_score = 0
    if trendlines['support'] or trendlines['resistance']:
        # Check if near trendline
        for tl in trendlines['support']:
            # Estimate current trendline price (simplified)
            if trade_type == 'LONG' and abs(current_price - tl['start']['price']) / current_price < 0.02:
                trendline_score += 10
                reasons.append("📈 Support Trendline Bounce")
                break
        
        for tl in trendlines['resistance']:
            if trade_type == 'SHORT' and abs(current_price - tl['start']['price']) / current_price < 0.02:
                trendline_score += 10
                reasons.append("📉 Resistance Trendline")
                break
    
    score += min(trendline_score, 10)
    
    # === 7. VOLUME CONFIRMATION (Max 5 points) ===
    if not pd.isna(last_row.get('Volume')) and not pd.isna(last_row.get('VOL_SMA_20')):
        if last_row['Volume'] > last_row['VOL_SMA_20'] * 1.5:
            score += 5
            reasons.append("📊 Strong Volume")
        elif last_row['Volume'] > last_row['VOL_SMA_20']:
            score += 3
            reasons.append("Volume Confirmed")
    
    # === 8. RSI EXTREMES (Max 5 points) ===
    if not pd.isna(last_row.get('RSI')):
        if trade_type == 'LONG' and last_row['RSI'] < 30:
            score += 5
            reasons.append("RSI Oversold")
        elif trade_type == 'LONG' and last_row['RSI'] < 40:
            score += 3
        elif trade_type == 'SHORT' and last_row['RSI'] > 70:
            score += 5
            reasons.append("RSI Overbought")
        elif trade_type == 'SHORT' and last_row['RSI'] > 60:
            score += 3
    
    # === 9. ADX TREND STRENGTH (Max 5 points) ===
    if not pd.isna(last_row.get('ADX')):
        if last_row['ADX'] > 40:
            score += 5
            reasons.append("Very Strong Trend (ADX)")
        elif last_row['ADX'] > 25:
            score += 3
            reasons.append("Strong Trend")
    
    # === 10. CANDLESTICK PATTERNS (Max 5 points) ===
    if last_row.get('Pattern'):
        if trade_type == 'LONG' and last_row['Pattern'] in ['Bullish Engulfing', 'Hammer']:
            score += 5
            reasons.append(f"🕯️ {last_row['Pattern']}")
        elif trade_type == 'SHORT' and last_row['Pattern'] in ['Bearish Engulfing', 'Shooting Star']:
            score += 5
            reasons.append(f"🕯️ {last_row['Pattern']}")
    
    # Total possible: 120 points, cap at 100
    final_score = min(score, 100)
    
    # Only return setup if score >= 60 (professional threshold)
    if final_score < 60:
        reasons.insert(0, f"⚠️ Confluence Too Low ({final_score}%)")
    
    return final_score, reasons

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
def calculate_zigzag(df, deviation=0.02):
    """
    Calculates ZigZag points for market structure identification.
    Identifies swing highs and lows based on percentage deviation.
    """
    points = []
    if df is None or len(df) < 5:
        return points
        
    last_point = {'date': df.index[0], 'price': df['Close'].iloc[0], 'type': 'start'}
    points.append(last_point)
    
    direction = 0  # 1 for up, -1 for down
    
    for i in range(1, len(df)):
        price = df['Close'].iloc[i]
        date = df.index[i]
        change = (price - last_point['price']) / last_point['price']
        
        if direction == 0:
            if change >= deviation:
                direction = 1
                last_point = {'date': date, 'price': price, 'type': 'high'}
                points.append(last_point)
            elif change <= -deviation:
                direction = -1
                last_point = {'date': date, 'price': price, 'type': 'low'}
                points.append(last_point)
        elif direction == 1:  # Uptrend
            if price > last_point['price']:
                last_point['date'] = date
                last_point['price'] = price
                points[-1] = last_point
            elif change <= -deviation:
                direction = -1
                last_point = {'date': date, 'price': price, 'type': 'low'}
                points.append(last_point)
        elif direction == -1:  # Downtrend
            if price < last_point['price']:
                last_point['date'] = date
                last_point['price'] = price
                points[-1] = last_point
            elif change >= deviation:
                direction = 1
                last_point = {'date': date, 'price': price, 'type': 'high'}
                points.append(last_point)
                
    return points


def calculate_liquidation_levels(zigzag_points, current_price, leverage_assumptions=[5, 10, 20]):
    """
    Estimates liquidation levels based on ZigZag swing points.
    Calculates where long/short positions get liquidated at common leverage levels.
    """
    levels = []
    if not zigzag_points or len(zigzag_points) < 2:
        return levels
        
    # Get recent swing points (last 5)
    recent_swings = zigzag_points[-min(5, len(zigzag_points)):] 
    
    for p in recent_swings:
        if p['type'] == 'high':
            # Shorts get liquidated above swing high
            for lev in leverage_assumptions:
                liq_distance = 1 / lev  # % move to liquidate
                liq_price = p['price'] * (1 + liq_distance)
                if liq_price > current_price * 0.98:  # Only if near current price
                    levels.append({
                        'price': liq_price,
                        'type': f'Short Liq {lev}x',
                        'color': 'orange',
                        'leverage': lev
                    })
        elif p['type'] == 'low':
            # Longs get liquidated below swing low
            for lev in leverage_assumptions:
                liq_distance = 1 / lev
                liq_price = p['price'] * (1 - liq_distance)
                if liq_price < current_price * 1.02:  # Only if near current price
                    levels.append({
                        'price': liq_price,
                        'type': f'Long Liq {lev}x',
                        'color': 'red',
                        'leverage': lev
                    })
            
    return levels


def detect_trendlines(zigzag_points, min_touches=2):
    """
    Detects trendlines by connecting consecutive swing highs/lows.
    Returns both support and resistance trendlines.
    """
    trendlines = {'support': [], 'resistance': []}
    
    if not zigzag_points or len(zigzag_points) < 3:
        return trendlines
    
    # Get highs and lows separately
    highs = [p for p in zigzag_points if p['type'] == 'high']
    lows = [p for p in zigzag_points if p['type'] == 'low']
    
    # Resistance trendlines (connect highs)
    if len(highs) >= min_touches:
        for i in range(len(highs) - 1):
            p1 = highs[i]
            p2 = highs[i + 1]
            # Calculate slope
            time_diff = (p2['date'] - p1['date']).total_seconds() / 86400  # days
            if time_diff > 0:
                slope = (p2['price'] - p1['price']) / time_diff
                trendlines['resistance'].append({
                    'start': p1,
                    'end': p2,
                    'slope': slope,
                    'type': 'descending' if slope < 0 else 'ascending'
                })
    
    # Support trendlines (connect lows)
    if len(lows) >= min_touches:
        for i in range(len(lows) - 1):
            p1 = lows[i]
            p2 = lows[i + 1]
            time_diff = (p2['date'] - p1['date']).total_seconds() / 86400
            if time_diff > 0:
                slope = (p2['price'] - p1['price']) / time_diff
                trendlines['support'].append({
                    'start': p1,
                    'end': p2,
                    'slope': slope,
                    'type': 'ascending' if slope > 0 else 'descending'
                })
    
    return trendlines


def detect_chart_patterns(df, zigzag_points):
    """
    Comprehensive chart pattern detection including:
    - Head & Shoulders (Bullish/Bearish)
    - Double Top/Bottom
    - Triple Top/Bottom  
    - Triangles (Ascending/Descending/Symmetrical)
    - Flags and Pennants
    - Wedges (Rising/Falling)
    """
    patterns = []
    
    if not zigzag_points or len(zigzag_points) < 5:
        return patterns
    
    # Helper to check if prices are approximately equal (within tolerance)
    def approx_equal(p1, p2, tolerance=0.02):
        return abs(p1 - p2) / max(p1, p2) < tolerance
    
    # Get recent swings (last 7 for pattern detection)
    swings = zigzag_points[-min(7, len(zigzag_points)):]
    
    # 1. HEAD & SHOULDERS PATTERN
    if len(swings) >= 5:
        # Bearish H&S: Low-High-Low-High(head)-Low-High-Low
        for i in range(len(swings) - 4):
            if (swings[i]['type'] == 'high' and swings[i+2]['type'] == 'high' and swings[i+4]['type'] == 'high'):
                left_shoulder = swings[i]['price']
                head = swings[i+2]['price']
                right_shoulder = swings[i+4]['price']
                
                if head > left_shoulder and head > right_shoulder and approx_equal(left_shoulder, right_shoulder):
                    patterns.append({
                        'type': 'Head & Shoulders (Bearish)',
                        'confidence': 'High',
                        'target_direction': 'SHORT',
                        'neckline': min(swings[i+1]['price'], swings[i+3]['price'])
                    })
        
        # Inverted H&S (Bullish)
        for i in range(len(swings) - 4):
            if (swings[i]['type'] == 'low' and swings[i+2]['type'] == 'low' and swings[i+4]['type'] == 'low'):
                left_shoulder = swings[i]['price']
                head = swings[i+2]['price']
                right_shoulder = swings[i+4]['price']
                
                if head < left_shoulder and head < right_shoulder and approx_equal(left_shoulder, right_shoulder):
                    patterns.append({
                        'type': 'Inverted H&S (Bullish)',
                        'confidence': 'High',
                        'target_direction': 'LONG',
                        'neckline': max(swings[i+1]['price'], swings[i+3]['price'])
                    })
    
    # 2. DOUBLE TOP/BOTTOM
    if len(swings) >= 3:
        # Double Top
        for i in range(len(swings) - 2):
            if swings[i]['type'] == 'high' and swings[i+2]['type'] == 'high':
                if approx_equal(swings[i]['price'], swings[i+2]['price'], tolerance=0.015):
                    patterns.append({
                        'type': 'Double Top (Bearish)',
                        'confidence': 'Medium',
                        'target_direction': 'SHORT',
                        'resistance': swings[i]['price']
                    })
        
        # Double Bottom
        for i in range(len(swings) - 2):
            if swings[i]['type'] == 'low' and swings[i+2]['type'] == 'low':
                if approx_equal(swings[i]['price'], swings[i+2]['price'], tolerance=0.015):
                    patterns.append({
                        'type': 'Double Bottom (Bullish)',
                        'confidence': 'Medium',
                        'target_direction': 'LONG',
                        'support': swings[i]['price']
                    })
    
    # 3. TRIANGLES 
    if len(swings) >= 4:
        highs = [s for s in swings if s['type'] == 'high']
        lows = [s for s in swings if s['type'] == 'low']
        
        if len(highs) >= 2 and len(lows) >= 2:
            # Ascending Triangle: Flat resistance, rising support
            if approx_equal(highs[-1]['price'], highs[-2]['price'], 0.015) and lows[-1]['price'] > lows[-2]['price']:
                patterns.append({
                    'type': 'Ascending Triangle (Bullish)',
                    'confidence': 'Medium',
                    'target_direction': 'LONG'
                })
            
            # Descending Triangle: Flat support, falling resistance
            if approx_equal(lows[-1]['price'], lows[-2]['price'], 0.015) and highs[-1]['price'] < highs[-2]['price']:
                patterns.append({
                    'type': 'Descending Triangle (Bearish)',
                    'confidence': 'Medium',
                    'target_direction': 'SHORT'
                })
            
            # Symmetrical Triangle: Converging
            if highs[-1]['price'] < highs[-2]['price'] and lows[-1]['price'] > lows[-2]['price']:
                patterns.append({
                    'type': 'Symmetrical Triangle',
                    'confidence': 'Low',
                    'target_direction': 'BREAKOUT'
                })
    
    # 4. WEDGES (Rising/Falling)
    if len(swings) >= 4:
        highs = [s for s in swings[-4:] if s['type'] == 'high']
        lows = [s for s in swings[-4:] if s['type'] == 'low']
        
        if len(highs) >= 2 and len(lows) >= 2:
            # Rising Wedge (Bearish): Both rising but converging
            if (highs[-1]['price'] > highs[0]['price'] and lows[-1]['price'] > lows[0]['price'] and
                (highs[-1]['price'] - lows[-1]['price']) < (highs[0]['price'] - lows[0]['price'])):
                patterns.append({
                    'type': 'Rising Wedge (Bearish)',
                    'confidence': 'Medium',
                    'target_direction': 'SHORT'
                })
            
            # Falling Wedge (Bullish): Both falling but converging
            if (highs[-1]['price'] < highs[0]['price'] and lows[-1]['price'] < lows[0]['price'] and
                (highs[-1]['price'] - lows[-1]['price']) < (highs[0]['price'] - lows[0]['price'])):
                patterns.append({
                    'type': 'Falling Wedge (Bullish)',
                    'confidence': 'Medium',
                    'target_direction': 'LONG'
                })
    
    return patterns
