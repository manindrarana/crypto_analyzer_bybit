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

def main():
    st.title("⚡ Bybit Crypto Analyzer Pro")
    
    # Sidebar
    st.sidebar.header("Configuration")
    symbol = st.sidebar.text_input("Symbol", value="BTCUSDT").upper()
    interval = st.sidebar.selectbox("Interval", ["5m", "15m", "1h", "2h", "4h", "1d"], index=2)
    loopback = st.sidebar.slider("Loopback (Candles)", min_value=100, max_value=1000, value=200, step=50)
    use_closed_candles = st.sidebar.checkbox("Analyze Closed Candles Only", value=True, help="Stabilizes signals by ignoring the current forming candle.")
    
    if st.sidebar.button("Analyze Market"):
        with st.spinner("Fetching advanced data..."):
            # Fetch Data
            df = data_loader.fetch_data(symbol, interval, limit=loopback)
            df_oi = data_loader.fetch_open_interest(symbol, interval, limit=loopback)
            df_ls = data_loader.fetch_long_short_ratio(symbol, interval, limit=loopback)
            funding_rate = data_loader.fetch_funding_rate(symbol)
            
            if df.empty:
                st.error(f"Could not fetch data for {symbol}. Please check the symbol and try again.")
                return
            
            # Filter for closed candles if requested
            if use_closed_candles:
                df = df.iloc[:-1]
                if not df_oi.empty: df_oi = df_oi.iloc[:-1]
                if not df_ls.empty: df_ls = df_ls.iloc[:-1]
                
            # Calculate Indicators
            df = indicators.calculate_indicators(df)
            df = indicators.calculate_vwap(df)
            df = indicators.check_patterns(df)
            supports, resistances = indicators.calculate_support_resistance(df)
            fvgs = indicators.calculate_fvg(df)
            
            # Calculate Volume Profile
            vp_df, vp_levels = indicators.calculate_volume_profile(df)
            
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
            
            # --- Main Chart (Candlestick + Indicators + Volume Profile) ---
            st.subheader(f"{symbol} Price Action & Volume Profile")
            
            # Create Subplots: 1 Row, 2 Cols (Candles 80%, Profile 20%)
            # We will use a separate figure for the main chart + profile
            # And then another figure for Sub-indicators (MACD, RSI) to keep it clean or combine all?
            # Let's combine all into one big figure with subplots for a pro dashboard feel.
            # Layout:
            # Row 1: Price + Volume Profile (Col 1 & 2)
            # Row 2: MACD (Col 1 only, spanning width?) -> No, simpler to keep Profile separate or side-by-side.
            # Let's do: Row 1 (Price | Profile), Row 2 (MACD), Row 3 (RSI), Row 4 (OI)
            
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
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Strategy Card
            setup = indicators.get_trade_setup(df, current_price)
            confidence, reasons = indicators.calculate_confidence(df, setup)
            
            st.subheader("Strategy Dashboard")
            if setup:
                conf_color = "red"
                if confidence > 70: conf_color = "green"
                elif confidence > 40: conf_color = "orange"
                
                dca_labels = ["-2%", "-5%", "-10%"]
                if setup['Type'] == 'SHORT':
                    dca_labels = ["+2%", "+5%", "+10%"]
                
                st.markdown(f"""
                <div class="strategy-card">
                    <h3>🚀 Trade Setup: {setup['Signal']}</h3>
                    <p><strong>Confidence Score:</strong> <span style="color:{conf_color}; font-size: 1.2em; font-weight: bold;">{confidence}%</span></p>
                    <p><em>{', '.join(reasons)}</em></p>
                    <hr>
                    <p><strong>Entry:</strong> ${setup['Entry']:.5f}</p>
                    <p><strong>Stop Loss:</strong> ${setup['SL']:.5f}</p>
                    <p><strong>Take Profit:</strong> ${setup['TP']:.5f} (Risk/Reward 1:2)</p>
                    <hr>
                    <h4>DCA Levels:</h4>
                    <ul>
                        <li>Level 1 ({dca_labels[0]}): ${setup['DCA_1']:.5f}</li>
                        <li>Level 2 ({dca_labels[1]}): ${setup['DCA_2']:.5f}</li>
                        <li>Level 3 ({dca_labels[2]}): ${setup['DCA_3']:.5f}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No clear trade setup detected based on current strategy logic (EMA Cross or RSI Oversold).")
                
            # Raw Data Expander
            with st.expander("View Raw Data"):
                st.dataframe(df.tail(10))

if __name__ == "__main__":
    main()
