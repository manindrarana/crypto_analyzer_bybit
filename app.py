import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_loader
import indicators

st.set_page_config(layout="wide", page_title="Bybit Crypto Analyzer")

# Custom CSS for Dark Mode and styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #4b4b4b;
    }
    .strategy-card {
        background-color: #1c1e24;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00ff00;
    }
</style>
""", unsafe_allow_html=True)

def plot_chart(df, symbol):
    """
    Helper function to create the main chart.
    """
    supports, resistances = indicators.calculate_support_resistance(df)
    fvgs = indicators.calculate_fvg(df)
    vp_df, vp_levels = indicators.calculate_volume_profile(df)
    
    # Get latest data for OI/LS if available
    df_oi = st.session_state.data.get('df_oi', pd.DataFrame()) if st.session_state.data else pd.DataFrame()
    
    fig = make_subplots(
        rows=4, cols=2, 
        shared_xaxes=True, 
        column_widths=[0.8, 0.2],
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        specs=[[{}, {}], # Row 1: Price, Profile
                [{"colspan": 2}, None], # Row 2: MACD spans both
                [{"colspan": 2}, None], # Row 3: RSI spans both
                [{"colspan": 2}, None]], # Row 4: OI spans both
        subplot_titles=(f"{symbol} Price", "Volume Profile", "MACD", "RSI", "Open Interest")
    )
    
    # 1. Candlestick (Row 1, Col 1)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='OHLC'
    ), row=1, col=1)
    
    # EMAs & BB & VWAP (Row 1, Col 1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], line=dict(color='cyan', width=1), name='EMA 9'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], line=dict(color='magenta', width=1), name='EMA 21'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_UPPER'], line=dict(color='gray', width=1, dash='dot'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_LOWER'], line=dict(color='gray', width=1, dash='dot'), name='BB Lower'), row=1, col=1)
    
    if 'VWAP' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='gold', width=1.5, dash='dash'), name='VWAP'), row=1, col=1)

    # Support/Resistance Lines (Row 1, Col 1)
    for _, price in supports[-5:]:
        fig.add_hline(y=price, line_color="green", line_width=0.5, line_dash="dot", row=1, col=1)
    for _, price in resistances[-5:]:
        fig.add_hline(y=price, line_color="red", line_width=0.5, line_dash="dot", row=1, col=1)
        
    # FVGs (Row 1, Col 1)
    for fvg in fvgs[-10:]:
        color = "rgba(0, 255, 0, 0.2)" if fvg['type'] == 'bullish' else "rgba(255, 0, 0, 0.2)"
        fig.add_shape(
            type="rect",
            x0=fvg['start_time'], y0=fvg['bottom'], x1=df.index[-1], y1=fvg['top'],
            fillcolor=color, line=dict(width=0),
            row=1, col=1
        )

    # 2. Volume Profile (Row 1, Col 2)
    if vp_df is not None and not vp_df.empty:
        colors = []
        for price in vp_df['PriceBinCenter']:
            if vp_levels['VAL'] <= price <= vp_levels['VAH']:
                colors.append('rgba(0, 255, 0, 0.5)') # Value Area
            else:
                colors.append('rgba(128, 128, 128, 0.2)') # Outside VA
                
        fig.add_trace(go.Bar(
            x=vp_df['Volume'],
            y=vp_df['PriceBinCenter'],
            orientation='h',
            marker_color=colors,
            name='Volume Profile',
            showlegend=False
        ), row=1, col=2)
        
        # POC Line
        fig.add_hline(y=vp_levels['POC'], line_color="red", line_width=2, annotation_text="POC", row=1, col=2)
        fig.add_hline(y=vp_levels['VAH'], line_color="green", line_width=1, line_dash="dash", annotation_text="VAH", row=1, col=2)
        fig.add_hline(y=vp_levels['VAL'], line_color="green", line_width=1, line_dash="dash", annotation_text="VAL", row=1, col=2)

    # 3. MACD (Row 2, Col 1 - Spanning)
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_HIST'], name='MACD Hist', marker_color='gray'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='orange', width=1), name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_SIGNAL'], line=dict(color='blue', width=1), name='Signal'), row=2, col=1)
    
    # 4. RSI (Row 3, Col 1 - Spanning)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1), name='RSI'), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    # 5. Open Interest (Row 4, Col 1 - Spanning)
    if not df_oi.empty:
        df_oi = df_oi.reindex(df.index, method='nearest')
        fig.add_trace(go.Scatter(x=df_oi.index, y=df_oi['openInterest'], fill='tozeroy', line=dict(color='yellow', width=1), name='Open Interest'), row=4, col=1)
    
    # Layout Updates
    fig.update_layout(
        height=1200, 
        width=1400,
        xaxis_rangeslider_visible=False, 
        template="plotly_dark",
        showlegend=True
    )
    
    # Hide X-axis for Volume Profile
    fig.update_xaxes(showticklabels=False, row=1, col=2)
    
    return fig

def main():
    st.title("⚡ Bybit Crypto Analyzer Pro")
    
    # --- Sidebar Navigation ---
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["📊 Dashboard", "🔍 Multi-Screener", "🧪 Backtester"])
    
    st.sidebar.markdown("---")
    
    # --- Shared Configuration ---
    st.sidebar.header("Global Settings")
    
    # Load defaults from config
    import config
    cfg = config.load_config()
    
    default_interval = cfg.get('interval', '1h')
    default_loopback = cfg.get('loopback', 200)
    
    # Only show Symbol input on Dashboard page
    if page == "📊 Dashboard":
        symbol = st.sidebar.text_input("Symbol", value="BTCUSDT").upper()
    else:
        symbol = None # Not used in other pages directly from sidebar
        
    interval = st.sidebar.selectbox("Interval", ["5m", "15m", "1h", "2h", "4h", "1d"], index=["5m", "15m", "1h", "2h", "4h", "1d"].index(default_interval))
    loopback = st.sidebar.slider("Loopback (Candles)", min_value=100, max_value=1000, value=default_loopback, step=50)
    use_closed_candles = st.sidebar.checkbox("Analyze Closed Candles Only", value=True, help="Stabilizes signals by ignoring the current forming candle.")

    # --- Alerts Config (Telegram Only) ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("🔔 Alerts Config"):
        enable_telegram = st.checkbox("Enable Telegram Alerts")
        telegram_token = st.text_input("Bot Token", type="password")
        telegram_chat_id = st.text_input("Chat ID", type="password")

    # Initialize session state
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'analyzed' not in st.session_state:
        st.session_state.analyzed = False

    # ==========================================
    # PAGE 1: DASHBOARD
    # ==========================================
    if page == "📊 Dashboard":
        st.header(f"📊 Market Analysis: {symbol}")
        
        if st.button("Analyze Market", type="primary"):
            with st.spinner("Fetching advanced data..."):
                # Fetch Data
                df = data_loader.fetch_data(symbol, interval, limit=loopback)
                df_oi = data_loader.fetch_open_interest(symbol, interval, limit=loopback)
                df_ls = data_loader.fetch_long_short_ratio(symbol, interval, limit=loopback)
                funding_rate = data_loader.fetch_funding_rate(symbol)
                
                if df is not None and not df.empty:
                    # Calculate Indicators
                    df = indicators.calculate_indicators(df)
                    df = indicators.calculate_vwap(df)
                    df = indicators.check_patterns(df)
                    supports, resistances = indicators.calculate_support_resistance(df)
                    fvgs = indicators.calculate_fvg(df)
                    vp_df, vp_levels = indicators.calculate_volume_profile(df)
                    
                    # Store in session state
                    st.session_state.data = {
                        'df': df,
                        'df_oi': df_oi,
                        'df_ls': df_ls,
                        'funding_rate': funding_rate,
                        'supports': supports,
                        'resistances': resistances,
                        'fvgs': fvgs,
                        'vp_df': vp_df,
                        'vp_levels': vp_levels,
                        'symbol': symbol
                    }
                    st.session_state.analyzed = True
                else:
                    st.error("Failed to fetch data. Please check symbol and connection.")
                    
        # Render Dashboard if analyzed
        if st.session_state.analyzed and st.session_state.data:
            data = st.session_state.data
            df = data['df']
            df_oi = data['df_oi']
            df_ls = data['df_ls']
            funding_rate = data['funding_rate']
            current_symbol = data['symbol']
            
            # Get latest data
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2] 
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100
            
            # Trend Status
            sma_200 = df['SMA_200'].iloc[-1]
            if pd.isna(sma_200):
                    trend = "NEUTRAL (No Data)"
            else:
                trend = "BULLISH 🐂" if current_price > sma_200 else "BEARISH 🐻"
            
            # Display Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Current Price", f"${current_price:.5f}", f"{price_change_pct:.2f}%")
            col2.metric("Trend (SMA 200)", trend)
            col3.metric("Volume", f"{df['Volume'].iloc[-1]:.2f}")
            
            if not df_ls.empty:
                ls_ratio = df_ls['buyRatio'].iloc[-1] / df_ls['sellRatio'].iloc[-1]
                col4.metric("Long/Short Ratio", f"{ls_ratio:.2f}")
            else:
                col4.metric("Long/Short Ratio", "N/A")
                
            if funding_rate is not None:
                col5.metric("Funding Rate", f"{funding_rate * 100:.4f}%")
            else:
                col5.metric("Funding Rate", "N/A")
                
            # --- Main Chart ---
            st.subheader(f"{current_symbol} Price Action & Volume Profile")
            fig = plot_chart(df, current_symbol)
            st.plotly_chart(fig, use_container_width=True)
            
            # --- Strategy Card ---
            col_strat1, col_strat2 = st.columns([2, 1])
            
            with col_strat1:
                # Raw Data Expander (Restored)
                with st.expander("View Raw Data"):
                    st.dataframe(df.tail(10))
            
            with col_strat2:
                setup = indicators.get_trade_setup(df, current_price)
                
                st.subheader("Strategy Dashboard")
                if setup:
                    confidence = indicators.calculate_confidence(setup, df)
                    setup['Confidence'] = confidence['score']
                    setup['Reasons'] = confidence['reasons']
                    
                    conf_color = "red"
                    if setup['Confidence'] > 70: conf_color = "green"
                    elif setup['Confidence'] > 40: conf_color = "orange"
                    
                    dca_labels = ["-2%", "-5%", "-10%"]
                    if setup['Type'] == 'SHORT':
                        dca_labels = ["+2%", "+5%", "+10%"]
                    
                    st.markdown(f"""
                    <div class="strategy-card">
                        <h3>🚀 Trade Setup: {setup['Signal']}</h3>
                        <p><strong>Confidence Score:</strong> <span style="color:{conf_color}; font-size: 1.2em; font-weight: bold;">{setup['Confidence']}%</span></p>
                        <p><em>{', '.join(setup['Reasons'])}</em></p>
                        <hr>
                        <p><strong>Entry:</strong> ${setup['Entry']:.5f}</p>
                        <p><strong>Stop Loss:</strong> ${setup['Stop Loss']:.5f}</p>
                        <p><strong>Take Profit:</strong> ${setup['Take Profit']:.5f} (Risk/Reward 1:2)</p>
                        <hr>
                        <h4>DCA Levels:</h4>
                        <ul>
                            <li>Level 1 ({dca_labels[0]}): ${setup['DCA 1']:.5f}</li>
                            <li>Level 2 ({dca_labels[1]}): ${setup['DCA 2']:.5f}</li>
                            <li>Level 3 ({dca_labels[2]}): ${setup['DCA 3']:.5f}</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No clear trade setup detected based on current strategy logic.")

    # ==========================================
    # PAGE 2: MULTI-SCREENER
    # ==========================================
    elif page == "🔍 Multi-Screener":
        st.header("🔍 Multi-Symbol Screener")
        
        default_symbols_list = cfg.get('symbols', ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"])
        default_symbols = ", ".join(default_symbols_list)
        
        with st.expander("⚙️ Screener Configuration", expanded=True):
            symbols_input = st.text_area("Symbols (comma separated)", value=default_symbols, height=70)
            # Use global interval/loopback or allow override? Let's use global for consistency but allow separate interval
            screener_interval = st.selectbox("Screener Interval", ["5m", "15m", "1h", "4h", "1d"], index=["5m", "15m", "1h", "4h", "1d"].index(interval), key="screener_interval")
        
        if st.button("🔍 Scan Market", type="primary"):
            import screener
            import alerts
            
            symbols_list = [s.strip() for s in symbols_input.split(',') if s.strip()]
            
            with st.spinner(f"Scanning {len(symbols_list)} symbols..."):
                results_df = screener.scan_market(symbols_list, screener_interval, loopback=loopback, use_closed_candles=use_closed_candles)
                
                if not results_df.empty:
                    st.subheader(f"Found {len(results_df)} Trade Setups")
                    st.dataframe(
                        results_df.style.applymap(
                            lambda x: 'color: green' if x == 'LONG' else 'color: red', subset=['Type']
                        ).format({
                            'Price': '${:.5f}',
                            'Entry': '${:.5f}',
                            'Stop Loss': '${:.5f}',
                            'Take Profit': '${:.5f}',
                            'DCA 1': '${:.5f}',
                            'DCA 2': '${:.5f}',
                            'DCA 3': '${:.5f}',
                            'Confidence': '{:.1f}%'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Send Alerts (Manual Trigger)
                    if enable_telegram and telegram_token and telegram_chat_id:
                        with st.spinner("Sending alerts..."):
                            for index, row in results_df.iterrows():
                                msg = alerts.format_setup_message(row)
                                alerts.send_telegram_message(telegram_token, telegram_chat_id, msg)
                        
                        st.success(f"✅ Sent alerts for {len(results_df)} setups!")
                else:
                    st.info("No high-confidence setups found.")

        # Continuous Monitor Info
        st.markdown("---")
        st.subheader("🤖 Continuous Monitor")
        st.info("ℹ️ The Continuous Monitor runs as a background service in Docker.")
        st.markdown("""
        To configure the monitor, edit `config.yaml` and restart the container.
        
        **Current Monitor Settings (from config):**
        """)
        
        st.json({
            "Monitor Frequency": f"{cfg.get('monitor_frequency_minutes', 15)} minutes",
            "Monitored Symbols": cfg.get('symbols', []),
            "Interval": cfg.get('interval', '1h')
        })

    # ==========================================
    # PAGE 3: BACKTESTER
    # ==========================================
    elif page == "🧪 Backtester":
        st.header("🧪 Strategy Backtester")
        
        # We need data to backtest. If not in session state, let user fetch it here or prompt to go to Dashboard.
        # Better: Allow fetching data here too.
        
        col_data1, col_data2, col_data3 = st.columns(3)
        with col_data1:
            bt_symbol = st.text_input("Symbol", value="BTCUSDT").upper()
        with col_data2:
            bt_interval = st.selectbox("Interval", ["5m", "15m", "1h", "2h", "4h", "1d"], index=2, key="bt_interval")
        with col_data3:
            bt_loopback = st.slider("Loopback", 100, 5000, 1000, 100, key="bt_loopback")
            
        if st.button("Fetch Data for Backtest"):
            with st.spinner("Fetching data..."):
                df_bt = data_loader.fetch_data(bt_symbol, bt_interval, limit=bt_loopback)
                if df_bt is not None:
                    st.session_state.bt_data = df_bt
                    st.success(f"Loaded {len(df_bt)} candles for {bt_symbol}")
                else:
                    st.error("Failed to fetch data")

        if 'bt_data' in st.session_state:
            df = st.session_state.bt_data
            
            # Calculate indicators for backtest if not present
            if 'EMA_9' not in df.columns:
                df = indicators.calculate_indicators(df)
                df = indicators.calculate_vwap(df)
            
            st.markdown("---")
            with st.expander("⚙️ Backtest Configuration", expanded=True):
                col_bt1, col_bt2 = st.columns(2)
                with col_bt1:
                    initial_capital = st.number_input("Initial Capital ($)", min_value=100, max_value=1000000, value=10000, step=1000)
                    use_dca = st.checkbox("Use DCA Levels", value=True, help="Include DCA levels in backtest")
                with col_bt2:
                    position_size_pct = st.slider("Position Size (%)", min_value=10, max_value=100, value=100, step=10)
                    
                    st.caption("Strategy Filters")
                    use_trend = st.checkbox("Require Trend (SMA 200)", value=True, help="Only trade Long > SMA200, Short < SMA200")
                    use_volume = st.checkbox("Require Volume", value=False, help="Only trade if Volume > Vol SMA 20")
                    use_adx = st.checkbox("Require Strong Trend (ADX > 25)", value=False, help="Only trade if ADX > 25")
                    use_macd = st.checkbox("Require Momentum (MACD)", value=False, help="Only trade if MACD confirms direction")
                    
                    st.caption("Risk Management")
                    use_tsl = st.checkbox("Use Trailing Stop Loss", value=True)
                    tsl_pct = st.slider("Trailing Stop (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.1, disabled=not use_tsl)
                
                if st.button("🚀 Run Backtest", type="primary"):
                    with st.spinner("Running backtest..."):
                        import backtester
                        
                        # Create backtester instance
                        bt = backtester.Backtester(
                            initial_capital=initial_capital,
                            use_dca=use_dca,
                            position_size_pct=position_size_pct,
                            use_trend_filter=use_trend,
                            use_volume_filter=use_volume,
                            use_adx_filter=use_adx,
                            use_macd_filter=use_macd,
                            trailing_stop_pct=tsl_pct if use_tsl else None
                        )
                        
                        # Run backtest
                        results = bt.run_backtest(df)
                        
                        if results and results['metrics']['total_trades'] > 0:
                            metrics = results['metrics']
                            trades_df = backtester.format_trade_history(results['trades'])
                            equity_curve = results['equity_curve']
                            
                            # Display Metrics
                            st.markdown("### 📈 Performance Metrics")
                            
                            col1, col2, col3, col4, col5 = st.columns(5)
                            
                            # Win Rate
                            win_rate_color = "green" if metrics['win_rate'] >= 50 else "red"
                            col1.markdown(f"""
                            <div class="metric-card">
                                <h4>Win Rate</h4>
                                <p style="color:{win_rate_color}; font-size: 1.5em; font-weight: bold;">{metrics['win_rate']:.1f}%</p>
                                <p style="font-size: 0.8em;">{metrics['winning_trades']}W / {metrics['losing_trades']}L</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Profit Factor
                            pf_color = "green" if metrics['profit_factor'] >= 1.5 else ("orange" if metrics['profit_factor'] >= 1.0 else "red")
                            col2.markdown(f"""
                            <div class="metric-card">
                                <h4>Profit Factor</h4>
                                <p style="color:{pf_color}; font-size: 1.5em; font-weight: bold;">{metrics['profit_factor']:.2f}</p>
                                <p style="font-size: 0.8em;">Gross Profit/Loss</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Total Return
                            return_color = "green" if metrics['total_return'] > 0 else "red"
                            col3.markdown(f"""
                            <div class="metric-card">
                                <h4>Total Return</h4>
                                <p style="color:{return_color}; font-size: 1.5em; font-weight: bold;">{metrics['total_return_pct']:.2f}%</p>
                                <p style="font-size: 0.8em;">${metrics['total_return']:.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Max Drawdown
                            col4.markdown(f"""
                            <div class="metric-card">
                                <h4>Max Drawdown</h4>
                                <p style="color:red; font-size: 1.5em; font-weight: bold;">{metrics['max_drawdown_pct']:.2f}%</p>
                                <p style="font-size: 0.8em;">${metrics['max_drawdown']:.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Total Trades
                            col5.markdown(f"""
                            <div class="metric-card">
                                <h4>Total Trades</h4>
                                <p style="color:cyan; font-size: 1.5em; font-weight: bold;">{metrics['total_trades']}</p>
                                <p style="font-size: 0.8em;">Avg: {metrics['avg_trade_duration_hours']:.1f}h</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Additional Metrics Row
                            st.markdown("### 💰 Trade Statistics")
                            col6, col7, col8, col9 = st.columns(4)
                            
                            col6.metric("Average Win", f"${metrics['avg_win']:.2f}")
                            col7.metric("Average Loss", f"${metrics['avg_loss']:.2f}")
                            col8.metric("Largest Win", f"${metrics['largest_win']:.2f}")
                            col9.metric("Largest Loss", f"${metrics['largest_loss']:.2f}")
                            
                            # Equity Curve
                            st.markdown("### 📊 Equity Curve")
                            
                            equity_df = pd.DataFrame(equity_curve)
                            
                            fig_equity = go.Figure()
                            fig_equity.add_trace(go.Scatter(
                                x=equity_df['time'],
                                y=equity_df['equity'],
                                mode='lines',
                                name='Portfolio Value',
                                line=dict(color='cyan', width=2),
                                fill='tozeroy',
                                fillcolor='rgba(0, 255, 255, 0.1)'
                            ))
                            
                            # Add initial capital line
                            fig_equity.add_hline(
                                y=initial_capital,
                                line_dash="dash",
                                line_color="gray",
                                annotation_text="Initial Capital"
                            )
                            
                            fig_equity.update_layout(
                                height=400,
                                template="plotly_dark",
                                xaxis_title="Time",
                                yaxis_title="Portfolio Value ($)",
                                showlegend=True,
                                hovermode='x unified'
                            )
                            
                            st.plotly_chart(fig_equity, use_container_width=True)
                            
                            # Trade History
                            st.markdown("### 📋 Trade History")
                            
                            # Format the dataframe for display
                            display_df = trades_df.copy()
                            display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:.5f}")
                            display_df['exit_price'] = display_df['exit_price'].apply(lambda x: f"${x:.5f}")
                            display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:.2f}")
                            display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{x:.2f}%")
                            display_df['capital_after'] = display_df['capital_after'].apply(lambda x: f"${x:.2f}")
                            
                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Summary
                            final_capital = metrics['final_capital']
                            st.success(f"✅ Backtest Complete! Final Capital: **${final_capital:.2f}** (Started with ${initial_capital:.2f})")
                            
                        else:
                            st.warning("⚠️ No trades were generated during the backtest period. Try adjusting the timeframe or strategy parameters.")

if __name__ == "__main__":
    main()
