import pandas as pd
import numpy as np
from datetime import datetime
import indicators

class Backtester:
    """
    Backtesting engine for trading strategies.
    Simulates trades on historical data and calculates performance metrics.
    """
    
    def __init__(self, initial_capital=10000, use_dca=False, position_size_pct=100, use_trend_filter=False, use_volume_filter=False, use_adx_filter=False, use_macd_filter=False, trailing_stop_pct=None):
        """
        Initialize backtester.
        
        Args:
            initial_capital (float): Starting capital in USD
            use_dca (bool): Whether to use DCA levels
            position_size_pct (float): Percentage of capital to use per trade (1-100)
            use_trend_filter (bool): Only trade with trend (SMA 200)
            use_volume_filter (bool): Only trade with high volume
            use_adx_filter (bool): Only trade with strong trend (ADX > 25)
            use_macd_filter (bool): Only trade with momentum alignment
            trailing_stop_pct (float): Trailing stop loss percentage (e.g., 1.0 for 1%)
        """
        self.initial_capital = initial_capital
        self.use_dca = use_dca
        self.position_size_pct = position_size_pct / 100
        self.use_trend_filter = use_trend_filter
        self.use_volume_filter = use_volume_filter
        self.use_adx_filter = use_adx_filter
        self.use_macd_filter = use_macd_filter
        self.trailing_stop_pct = trailing_stop_pct
        
        # Results storage
        self.trades = []
        self.equity_curve = []
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
    def run_backtest(self, df):
        """
        Run backtest on historical data.
        
        Args:
            df (pd.DataFrame): DataFrame with OHLCV data and calculated indicators
            
        Returns:
            dict: Backtest results with metrics and trade history
        """
        if df is None or len(df) < 22:
            return None
            
        # Reset state
        self.trades = []
        self.equity_curve = []
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        
        # Track open position
        open_position = None
        
        # Iterate through each candle
        for i in range(21, len(df)):  # Start after indicators are calculated
            current_row = df.iloc[i]
            current_price = current_row['Close']
            current_time = df.index[i]
            
            # Check if we have an open position
            if open_position:
                # --- Trailing Stop Logic ---
                if self.trailing_stop_pct:
                    if open_position['type'] == 'LONG':
                        # Update highest price since entry
                        open_position['highest_price'] = max(open_position.get('highest_price', -float('inf')), current_row['High'])
                        # Calculate new SL
                        new_sl = open_position['highest_price'] * (1 - self.trailing_stop_pct / 100)
                        # Only move SL up
                        open_position['sl'] = max(open_position['sl'], new_sl)
                        
                    elif open_position['type'] == 'SHORT':
                        # Update lowest price since entry
                        open_position['lowest_price'] = min(open_position.get('lowest_price', float('inf')), current_row['Low'])
                        # Calculate new SL
                        new_sl = open_position['lowest_price'] * (1 + self.trailing_stop_pct / 100)
                        # Only move SL down
                        open_position['sl'] = min(open_position['sl'], new_sl)

                # 1. Check for DCA Execution (if enabled)
                if self.use_dca and len(open_position['dca_levels']) > 0:
                    next_dca_price = open_position['dca_levels'][0]
                    dca_triggered = False
                    
                    if open_position['type'] == 'LONG':
                        if current_row['Low'] <= next_dca_price:
                            dca_triggered = True
                    elif open_position['type'] == 'SHORT':
                        if current_row['High'] >= next_dca_price:
                            dca_triggered = True
                            
                    if dca_triggered:
                        # Execute DCA
                        # Double the position size (Martingale-lite) or fixed amount? 
                        # Let's add equal amount to initial position for simplicity
                        added_size = open_position['initial_size'] 
                        
                        # Calculate new weighted average entry price
                        total_value = (open_position['entry_price'] * open_position['position_size']) + (next_dca_price * added_size)
                        new_total_size = open_position['position_size'] + added_size
                        new_entry_price = total_value / new_total_size
                        
                        # Update position
                        open_position['entry_price'] = new_entry_price
                        open_position['position_size'] = new_total_size
                        open_position['dca_levels'].pop(0) # Remove used level
                        
                        # Optional: Adjust TP to break-even + profit? 
                        # For now, keep original TP or maybe adjust it closer? 
                        # Let's keep original TP logic relative to new entry? No, keep simple.
                
                # 2. Check for Stop Loss or Take Profit
                exit_price = None
                exit_reason = None
                
                if open_position['type'] == 'LONG':
                    # Check SL (price went below SL)
                    if current_row['Low'] <= open_position['sl']:
                        exit_price = open_position['sl']
                        exit_reason = 'Stop Loss'
                    # Check TP (price went above TP)
                    elif current_row['High'] >= open_position['tp']:
                        exit_price = open_position['tp']
                        exit_reason = 'Take Profit'
                        
                elif open_position['type'] == 'SHORT':
                    # Check SL (price went above SL)
                    if current_row['High'] >= open_position['sl']:
                        exit_price = open_position['sl']
                        exit_reason = 'Stop Loss'
                    # Check TP (price went below TP)
                    elif current_row['Low'] <= open_position['tp']:
                        exit_price = open_position['tp']
                        exit_reason = 'Take Profit'
                
                # Close position if exit triggered
                if exit_price:
                    pnl = self._calculate_pnl(open_position, exit_price)
                    self.current_capital += pnl
                    
                    # Record trade
                    trade_record = {
                        'entry_time': open_position['entry_time'],
                        'exit_time': current_time,
                        'type': open_position['type'],
                        'entry_price': open_position['entry_price'], # This is avg price if DCA used
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'position_size': open_position['position_size'],
                        'pnl': pnl,
                        'pnl_pct': (pnl / open_position['position_size']) * 100,
                        'capital_after': self.current_capital
                    }
                    self.trades.append(trade_record)
                    
                    # Update peak capital for drawdown calculation
                    if self.current_capital > self.peak_capital:
                        self.peak_capital = self.current_capital
                    
                    # Clear position
                    open_position = None
            
            # If no open position, check for entry signals
            if not open_position:
                # Get current data slice for strategy
                df_slice = df.iloc[:i+1]
                setup = indicators.get_trade_setup(
                    df_slice, 
                    current_price,
                    use_trend_filter=self.use_trend_filter,
                    use_volume_filter=self.use_volume_filter,
                    use_adx_filter=self.use_adx_filter,
                    use_macd_filter=self.use_macd_filter
                )
                
                if setup:
                    # Calculate position size
                    # If using DCA, we might want to start smaller? 
                    # For now, use configured %
                    position_size = self.current_capital * self.position_size_pct
                    
                    dca_levels = []
                    if self.use_dca:
                        dca_levels = [setup['DCA_1'], setup['DCA_2'], setup['DCA_3']]
                    
                    # Open new position
                    open_position = {
                        'type': setup['Type'],
                        'entry_time': current_time,
                        'entry_price': setup['Entry'],
                        'sl': setup['SL'],
                        'tp': setup['TP'],
                        'position_size': position_size,
                        'initial_size': position_size, # Track for DCA sizing
                        'signal': setup['Signal'],
                        'dca_levels': dca_levels
                    }
                    
                    # Initialize High/Low for Trailing Stop
                    if setup['Type'] == 'LONG':
                        open_position['highest_price'] = current_row['High']
                    elif setup['Type'] == 'SHORT':
                        open_position['lowest_price'] = current_row['Low']
            
            # Record equity at each step
            equity = self.current_capital
            if open_position:
                # Add unrealized P&L
                unrealized_pnl = self._calculate_pnl(open_position, current_price)
                equity += unrealized_pnl
                
            self.equity_curve.append({
                'time': current_time,
                'equity': equity
            })
        
        # Close any remaining open position at the end
        if open_position:
            final_price = df.iloc[-1]['Close']
            pnl = self._calculate_pnl(open_position, final_price)
            self.current_capital += pnl
            
            trade_record = {
                'entry_time': open_position['entry_time'],
                'exit_time': df.index[-1],
                'type': open_position['type'],
                'entry_price': open_position['entry_price'],
                'exit_price': final_price,
                'exit_reason': 'End of Data',
                'position_size': open_position['position_size'],
                'pnl': pnl,
                'pnl_pct': (pnl / open_position['position_size']) * 100,
                'capital_after': self.current_capital
            }
            self.trades.append(trade_record)
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        
        return {
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def _calculate_pnl(self, position, exit_price):
        """
        Calculate P&L for a position.
        
        Args:
            position (dict): Position details
            exit_price (float): Exit price
            
        Returns:
            float: Profit or loss in USD
        """
        entry_price = position['entry_price']
        position_size = position['position_size']
        
        if position['type'] == 'LONG':
            # Long: profit when price goes up
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SHORT
            # Short: profit when price goes down
            pnl_pct = (entry_price - exit_price) / entry_price
        
        pnl = position_size * pnl_pct
        return pnl
    
    def _calculate_metrics(self):
        """
        Calculate performance metrics from trade history.
        
        Returns:
            dict: Performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'avg_trade_duration': 0
            }
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        
        # Win Rate
        win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0
        
        # Profit Factor
        gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
        
        # Total Return
        total_return = self.current_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Max Drawdown
        max_drawdown = 0
        max_drawdown_pct = 0
        peak = self.initial_capital
        
        for point in self.equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # Average Win/Loss
        avg_win = (gross_profit / num_wins) if num_wins > 0 else 0
        avg_loss = (gross_loss / num_losses) if num_losses > 0 else 0
        
        # Largest Win/Loss
        largest_win = max([t['pnl'] for t in winning_trades]) if winning_trades else 0
        largest_loss = min([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Average Trade Duration
        durations = []
        for trade in self.trades:
            duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600  # hours
            durations.append(duration)
        avg_trade_duration = np.mean(durations) if durations else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': num_wins,
            'losing_trades': num_losses,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'avg_trade_duration_hours': avg_trade_duration,
            'final_capital': self.current_capital
        }

def format_trade_history(trades):
    """
    Convert trade list to formatted DataFrame.
    
    Args:
        trades (list): List of trade dictionaries
        
    Returns:
        pd.DataFrame: Formatted trade history
    """
    if not trades:
        return pd.DataFrame()
    
    df = pd.DataFrame(trades)
    
    # Format columns
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['duration'] = df['exit_time'] - df['entry_time']
    
    # Reorder columns
    columns = ['entry_time', 'exit_time', 'duration', 'type', 'entry_price', 
               'exit_price', 'exit_reason', 'pnl', 'pnl_pct', 'capital_after']
    
    return df[columns]
