# ==========================================
# NEW PAGES CODE TO ADD TO APP.PY
# ==========================================
# This code should be added to app.py after the Backtester page implementation
# Update the sidebar radio line to include the new pages:
# page = st.sidebar.radio("Go to", ["📊 Dashboard", "🔍 Multi-Screener", "🧪 Backtester", "📜 Signal History", "📒 Trade Journal", "📊 Analytics"])

import database
import trade_journal
import analytics
from datetime import datetime, timedelta

# ==========================================
# PAGE 4: SIGNAL HISTORY
# ==========================================
elif page == "📜 Signal History":
    st.header("📜 Signal History")
    st.markdown("Browse all detected trade signals with confluence analysis")
    
    # Initialize database
    database.init_database()
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_symbol = st.text_input("Filter by Symbol", placeholder="e.g., BTCUSDT")
    with col2:
        filter_status = st.selectbox("Status", ["All", "NEW", "ALERTED", "TAKEN", "IGNORED"])
    with col3:
        min_confluence = st.slider("Min Confluence Score", 0, 100, 60)
    
    days_back = st.slider("Days to Show", 1, 90, 7)
    
    # Fetch signals
    status_filter = None if filter_status == "All" else filter_status
    symbol_filter = filter_symbol.upper() if filter_symbol else None
    
    signals = database.get_signals(
        limit=200,
        symbol=symbol_filter,
        status=status_filter,
        min_confluence=min_confluence,
        days=days_back
    )
    
    if signals:
        st.success(f"Found {len(signals)} signals")
        
        # Convert to DataFrame for display
        display_data = []
        for sig in signals:
            display_data.append({
                'ID': sig['id'],
                'Time': sig['timestamp'],
                'Symbol': sig['symbol'],
                'Type': sig['signal_type'],
                'Entry': f"${sig['entry_price']:.5f}",
                'SL': f"${sig['stop_loss']:.5f}" if sig['stop_loss'] else 'N/A',
                'TP': f"${sig['take_profit']:.5f}" if sig['take_profit'] else 'N/A',
                'Confluence': f"{sig['confluence_score']}%",
                'Status': sig['status']
            })
        
        df_signals = pd.DataFrame(display_data)
        
        # Display table
        st.dataframe(
            df_signals.style.applymap(
                lambda x: 'color: green' if x == 'LONG' else ('color: red' if x == 'SHORT' else ''),
                subset=['Type']
            ),
            use_container_width=True,
            hide_index=True
        )
        
        # Export functionality
        if st.button("📥 Export to CSV"):
            csv = df_signals.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Show detailed view for selected signal
        st.markdown("---")
        st.subheader("Signal Details")
        signal_id = st.number_input("Enter Signal ID to view details", min_value=1, step=1)
        
        if signal_id:
            selected = [s for s in signals if s['id'] == signal_id]
            if selected:
                sig = selected[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"### {sig['symbol']} {sig['signal_type']}")
                    st.write(f"**Entry:** ${sig['entry_price']:.5f}")
                    st.write(f"**Stop Loss:** ${sig['stop_loss']:.5f}")
                    st.write(f"**Take Profit:** ${sig['take_profit']:.5f}")
                    st.write(f"**Confluence Score:** {sig['confluence_score']}%")
                    st.write(f"**Status:** {sig['status']}")
                
                with col2:
                    st.markdown("#### Confluence Reasons")
                    if sig['confluence_reasons']:
                        for reason in sig['confluence_reasons']:
                            st.write(f"✓ {reason}")
                
                # Action buttons
                st.markdown("---")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("Mark as TAKEN"):
                        database.update_signal_status(signal_id, 'TAKEN')
                        st.success("Status updated to TAKEN!")
                        st.rerun()
                
                with col_b:
                    if st.button("Mark as IGNORED"):
                        database.update_signal_status(signal_id, 'IGNORED')
                        st.info("Status updated to IGNORED")
                        st.rerun()
            else:
                st.warning(f"Signal ID {signal_id} not found")
    else:
        st.info("No signals found matching filters")


# ==========================================
# PAGE 5: TRADE JOURNAL
# ==========================================
elif page == "📒 Trade Journal":
    st.header("📒 Trade Journal")
    st.markdown("Track your trades and performance")
    
    # Initialize database
    database.init_database()
    
    # Two sections: Add Trade & View Trades
    tab1, tab2 = st.tabs(["➕ Add Trade", "📊 Trade History"])
    
    with tab1:
        st.subheader("Log a New Trade")
        
        col1, col2 = st.columns(2)
        with col1:
            trade_symbol = st.text_input("Symbol", value="BTCUSDT").upper()
            trade_type = st.selectbox("Type", ["LONG", "SHORT"])
            entry_price = st.number_input("Entry Price", min_value=0.0, format="%.5f")
            entry_date = st.date_input("Entry Date", value=datetime.now())
            entry_time = st.time_input("Entry Time", value=datetime.now().time())
        
        with col2:
            exit_price = st.number_input("Exit Price (optional)", min_value=0.0, format="%.5f")
            exit_date = st.date_input("Exit Date (if closed)")
            exit_time = st.time_input("Exit Time")
            quantity = st.number_input("Quantity/Size", min_value=0.0, value=1.0)
            notes = st.text_area("Notes")
        
        if st.button("💾 Save Trade", type="primary"):
            entry_datetime = datetime.combine(entry_date, entry_time)
            exit_datetime = datetime.combine(exit_date, exit_time) if exit_price > 0 else None
            
            trade_id = trade_journal.log_trade_entry(
                symbol=trade_symbol,
                trade_type=trade_type,
                entry_price=entry_price,
                quantity=quantity,
                notes=notes
            )
            
            if exit_price > 0 and exit_datetime:
                trade_journal.log_trade_exit(trade_id, exit_price, quantity)
                st.success(f"✅ Trade closed and saved! ID: {trade_id}")
            else:
                st.success(f"✅ Trade entry logged! ID: {trade_id}")
    
    with tab2:
        st.subheader("Trade History & Performance")
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            history_symbol = st.text_input("Filter Symbol", placeholder="All symbols")
        with filter_col2:
            history_days = st.slider("Days Back", 7, 365, 30)
        
        # Get trades
        symbol_filter = history_symbol.upper() if history_symbol else None
        trades = database.get_trades(limit=100, symbol=symbol_filter, days=history_days)
        
        # Get statistics
        stats = trade_journal.get_trade_statistics(symbol=symbol_filter, days=history_days)
        
        # Display stats
        st.markdown("### 📈 Performance Metrics")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Trades", stats['closed_trades'])
        col2.metric("Win Rate", f"{stats['win_rate']:.1f}%")
        col3.metric("Total PnL", f"${stats['total_pnl']:.2f}")
        
        if stats['avg_win'] > 0:
            col4.metric("Avg Win", f"${stats['avg_win']:.2f}")
        else:
            col4.metric("Avg Win", "N/A")
        
        if stats['profit_factor'] > 0:
            col5.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
        else:
            col5.metric("Profit Factor", "N/A")
        
        # Trades table
        if trades:
            st.markdown("### 📋 Recent Trades")
            
            display_trades = []
            for t in trades:
                display_trades.append({
                    'ID': t['id'],
                    'Symbol': t['symbol'],
                    'Type': t['trade_type'],
                    'Entry': f"${t['entry_price']:.5f}",
                    'Exit': f"${t['exit_price']:.5f}" if t['exit_price'] else 'Open',
                    'PnL': f"${t['pnl']:.2f}" if t['pnl'] else 'N/A',
                    'PnL %': f"{t['pnl_percent']:.2f}%" if t['pnl_percent'] else 'N/A',
                    'Outcome': t['outcome'] if t['outcome'] else 'Open',
                    'Entry Time': t['entry_time']
                })
            
            df_trades = pd.DataFrame(display_trades)
            
            st.dataframe(
                df_trades.style.applymap(
                    lambda x: 'color: green' if x == 'WIN' else ('color: red' if x == 'LOSS' else ''),
                    subset=['Outcome']
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No trades found")


# ==========================================
# PAGE 6: ANALYTICS
# ==========================================
elif page == "📊 Analytics":
    st.header("📊 Performance Analytics")
    st.markdown("Data-driven insights into your trading system")
    
    # Initialize database
    database.init_database()
    
    # Overall Stats
    overall_stats = analytics.get_overall_stats()
    
    st.markdown("### 🎯 Overall Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Signals", overall_stats['total_signals'])
    col2.metric("Signals Alerted", overall_stats['signals_alerted'])
    col3.metric("Total Trades", overall_stats['total_trades'])
    col4.metric("Win Rate", f"{overall_stats['win_rate']:.1f}%")
    
    col5, col6 = st.columns(2)
    col5.metric("Total PnL", f"${overall_stats['total_pnl']:.2f}")
    col6.metric("Best Symbol", overall_stats['best_symbol'])
    
    st.markdown("---")
    
    # Win Rate by Symbol
    st.markdown("### 📊 Performance by Symbol")
    symbol_stats = analytics.get_win_rate_by_symbol()
    
    if symbol_stats:
        df_symbols = pd.DataFrame(symbol_stats)
        
        fig_symbols = go.Figure(data=[
            go.Bar(
                x=df_symbols['symbol'],
                y=df_symbols['win_rate'],
                marker_color='cyan',
                text=df_symbols['win_rate'].apply(lambda x: f"{x:.1f}%"),
                textposition='auto'
            )
        ])
        
        fig_symbols.update_layout(
            title="Win Rate by Symbol",
            xaxis_title="Symbol",
            yaxis_title="Win Rate (%)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_symbols, use_container_width=True)
        
        # Detailed table
        st.dataframe(
            df_symbols.style.format({
                'win_rate': '{:.2f}%',
                'total_pnl': '${:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No symbol data available yet")
    
    st.markdown("---")
    
    # Confluence Effectiveness
    st.markdown("### 🎯 Confluence Score Analysis")
    confluence_stats = analytics.get_confluence_effectiveness()
    
    if confluence_stats:
        df_confluence = pd.DataFrame(confluence_stats)
        
        fig_confluence = go.Figure(data=[
            go.Bar(
                x=df_confluence['range'],
                y=df_confluence['count'],
                marker_color='gold',
                text=df_confluence['count'],
                textposition='auto'
            )
        ])
        
        fig_confluence.update_layout(
            title="Signal Distribution by Confluence Score",
            xaxis_title="Confluence Range",
            yaxis_title="Number of Signals",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_confluence, use_container_width=True)
    else:
        st.info("Not enough signal data yet")
    
    st.markdown("---")
    
    # Equity Curve
    st.markdown("### 💰 Equity Curve")
    days_for_equity = st.slider("Days to Show", 7, 90, 30)
    
    equity_df = analytics.generate_equity_curve(days=days_for_equity)
    
    if not equity_df.empty:
        fig_equity = go.Figure()
        
        fig_equity.add_trace(go.Scatter(
            x=equity_df['date'],
            y=equity_df['cumulative_pnl'],
            mode='lines+markers',
            name='Cumulative PnL',
            line=dict(color='cyan', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 255, 0.1)'
        ))
        
        fig_equity.update_layout(
            title="Equity Curve",
            xaxis_title="Date",
            yaxis_title="Cumulative PnL ($)",
            template="plotly_dark",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_equity, use_container_width=True)
    else:
        st.info("No trade data available for equity curve")
    
    st.markdown("---")
    
    # Top Confluence Reasons
    st.markdown("### ⭐ Most Common Confluence Factors")
    top_reasons = analytics.get_top_confluence_reasons()
    
    if top_reasons:
        df_reasons = pd.DataFrame(top_reasons[:10])
        
        fig_reasons = go.Figure(data=[
            go.Bar(
                y=df_reasons['reason'],
                x=df_reasons['count'],
                orientation='h',
                marker_color='magenta',
                text=df_reasons['count'],
                textposition='auto'
            )
        ])
        
        fig_reasons.update_layout(
            title="Top 10 Confluence Factors in High-Quality Signals",
            xaxis_title="Frequency",
            yaxis_title="Factor",
            template="plotly_dark",
            height=500
        )
        
        st.plotly_chart(fig_reasons, use_container_width=True)
    else:
        st.info("Not enough data yet")
