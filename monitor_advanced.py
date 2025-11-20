import time
import logging
import config
import screener
import alerts
import database
import indicators
from datetime import datetime, timedelta
from collections import deque
import sys

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Alert rate limiting
alert_history = deque(maxlen=100)  # Track last 100 alerts
symbol_cooldowns = {}  # Symbol -> last alert time

# Timeframe configuration with weights and scan frequencies
TIMEFRAMES = {
    '5m': {'weight': 0.8, 'scan_interval_minutes': 5, 'enabled': True},
    '15m': {'weight': 1.0, 'scan_interval_minutes': 15, 'enabled': True},
    '1h': {'weight': 1.2, 'scan_interval_minutes': 60, 'enabled': True},
    '4h': {'weight': 1.5, 'scan_interval_minutes': 240, 'enabled': True},
    '1d': {'weight': 2.0, 'scan_interval_minutes': 1440, 'enabled': True}
}

def is_within_alert_limit(max_per_hour=10):
    """Check if we can send more alerts this hour."""
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_alerts = [t for t in alert_history if t > one_hour_ago]
    
    if len(recent_alerts) >= max_per_hour:
        logger.warning(f"⚠️  Alert limit reached ({len(recent_alerts)}/{max_per_hour} in last hour)")
        return False
    return True

def is_symbol_on_cooldown(symbol, cooldown_minutes=120):
    """Check if symbol recently alerted (cross-timeframe dedup)."""
    if symbol in symbol_cooldowns:
        time_since_last = datetime.now() - symbol_cooldowns[symbol]
        if time_since_last < timedelta(minutes=cooldown_minutes):
            remaining = cooldown_minutes - (time_since_last.total_seconds() / 60)
            logger.info(f"⏭️  {symbol} on cooldown ({remaining:.0f}m remaining)")
            return True
    return False

def apply_timeframe_weight(confluence_score, timeframe):
    """Apply weight bonus for higher timeframes."""
    weight = TIMEFRAMES[timeframe]['weight']
    weighted_score = confluence_score * weight
    
    # Cap at 100
    return min(100, weighted_score)

def scan_timeframe(symbols, timeframe, cfg, min_confluence=60):
    """Scan market for one specific timeframe."""
    try:
        tf_config = TIMEFRAMES[timeframe]
        if not tf_config['enabled']:
            return []
        
        logger.info(f"🔍 Scanning {timeframe} timeframe...")
        
        results_df = screener.scan_market(
            symbols,
            timeframe,
            loopback=cfg.get('loopback', 500),
            use_closed_candles=cfg.get('use_closed_candles', True)
        )
        
        if results_df.empty:
            return []
        
        # Filter by minimum confluence BEFORE applying timeframe weight
        base_filtered = results_df[results_df['Confidence'] >= min_confluence]
        
        if base_filtered.empty:
            logger.info(f"  No setups met {min_confluence}%+ threshold on {timeframe}")
            return []
        
        # Apply timeframe weighting
        qualified_setups = []
        for index, row in base_filtered.iterrows():
            base_score = row['Confidence']
            weighted_score = apply_timeframe_weight(base_score, timeframe)
            
            logger.info(f"  ✅ {row['Symbol']} {row['Type']}: {base_score}% (weighted: {weighted_score:.0f}%)")
            
            qualified_setups.append({
                'row': row,
                'timeframe': timeframe,
                'base_confluence': base_score,
                'weighted_confluence': weighted_score
            })
        
        return qualified_setups
        
    except Exception as e:
        logger.error(f"Error scanning {timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return []

def process_and_alert(setup_data, telegram_creds):
    """Process a qualified setup and send alert."""
    row = setup_data['row']
    timeframe = setup_data['timeframe']
    base_conf = setup_data['base_confluence']
    weighted_conf = setup_data['weighted_confluence']
    
    symbol = row['Symbol']
    signal_type = row['Type']
    entry_price = row['Entry']
    
    # Check for database duplicate (24 hours)
    if database.is_duplicate_signal(symbol, signal_type, entry_price, hours=24):
        logger.info(f"⏭️  Skipping duplicate (DB): {symbol} {signal_type} on {timeframe}")
        return False
    
    # Check symbol cooldown (2 hours cross-timeframe)
    if is_symbol_on_cooldown(symbol, cooldown_minutes=120):
        return False
    
    # Extract setup details
    setup = {
        'Type': signal_type,
        'Entry': entry_price,
        'SL': row.get('Stop Loss'),
        'TP': row.get('Take Profit'),
        'DCA_1': row.get('DCA 1'),
        'DCA_2': row.get('DCA 2'),
        'DCA_3': row.get('DCA 3')
    }
    
    # Parse confluence reasons
    confluence_reasons = []
    reasons_str = row.get('Reasons', '')
    if isinstance(reasons_str, list):
        confluence_reasons = reasons_str
    elif isinstance(reasons_str, str) and reasons_str:
        confluence_reasons = [r.strip() for r in reasons_str.split(',') if r.strip()]
    
    # Calculate R:R ratio
    sl = row.get('Stop Loss', 0)
    tp = row.get('Take Profit', 0)
    risk_reward = "N/A"
    if sl and tp:
        if signal_type == "LONG":
            risk = entry_price - sl
            reward = tp - entry_price
        else:  # SHORT
            risk = sl - entry_price
            reward = entry_price - tp
        
        if risk > 0:
            risk_reward = f"1:{reward/risk:.2f}"
    
    # Save to database
    try:
        signal_id = database.save_signal(
            symbol=symbol,
            timeframe=timeframe,
            setup=setup,
            confluence_score=int(base_conf),  # Store base score
            confluence_reasons=confluence_reasons,
            chart_patterns=None
        )
        logger.info(f"💾 Signal saved to database (ID: {signal_id})")
    except Exception as e:
        logger.error(f"Failed to save signal: {e}")
        signal_id = None
    
    # Format enhanced alert message
    msg = format_enhanced_alert(
        symbol=symbol,
        timeframe=timeframe,
        signal_type=signal_type,
        entry=entry_price,
        sl=sl,
        tp=tp,
        base_confluence=base_conf,
        weighted_confluence=weighted_conf,
        reasons=confluence_reasons,
        risk_reward=risk_reward,
        row=row
    )
    
    # Send Telegram alert
    if telegram_creds['token'] and telegram_creds['chat_id']:
        success, err = alerts.send_telegram_message(
            telegram_creds['token'],
            telegram_creds['chat_id'],
            msg
        )
        
        if success:
            logger.info(f"✅ Telegram alert sent for {symbol} ({timeframe})")
            
            # Record alert
            alert_history.append(datetime.now())
            symbol_cooldowns[symbol] = datetime.now()
            
            # Update signal status
            if signal_id:
                try:
                    database.update_signal_status(signal_id, 'ALERTED', alerted_at=datetime.now())
                except Exception as e:
                    logger.error(f"Failed to update signal status: {e}")
            
            return True
        else:
            logger.error(f"❌ Telegram failed for {symbol}: {err}")
    
    return False

def format_enhanced_alert(symbol, timeframe, signal_type, entry, sl, tp, 
                          base_confluence, weighted_confluence, reasons, risk_reward, row):
    """Create rich alert message with full details."""
    
    # Star rating based on weighted score
    if weighted_confluence >= 95:
        stars = "⭐⭐⭐⭐⭐"
    elif weighted_confluence >= 85:
        stars = "⭐⭐⭐⭐"
    elif weighted_confluence >= 75:
        stars = "⭐⭐⭐"
    elif weighted_confluence >= 65:
        stars = "⭐⭐"
    else:
        stars = "⭐"
    
    # Trade direction emoji
    direction_emoji = "🟢" if signal_type == "LONG" else "🔴"
    
    # Build message
    msg = f"""🚀 HIGH-PROBABILITY SETUP DETECTED 🚀

{direction_emoji} **{symbol}** | **{timeframe}** Timeframe
Type: **{signal_type}**
Confluence Score: **{base_confluence:.0f}%** (Weighted: {weighted_confluence:.0f}%) {stars}

📊 **ENTRY ZONE**
Entry: ${entry:.5f}
Stop Loss: ${sl:.5f} ({((sl-entry)/entry*100):.2f}%)
Take Profit: ${tp:.5f} ({((tp-entry)/entry*100):.2f}%)
R:R Ratio: {risk_reward}

📈 **TECHNICAL CONFLUENCE**"""
    
    # Add reasons
    if reasons:
        for reason in reasons[:8]:  # Top 8 reasons only
            msg += f"\n✅ {reason}"
    
    msg += f"\n\n⚠️ **RISK MANAGEMENT**"
    msg += f"\nRecommended Position: 1-2% of capital"
    msg += f"\nAlways use stop loss!"
    
    msg += f"\n\n#{symbol} #{timeframe} #Confluence{int(base_confluence)}"
    
    return msg

def main():
    logger.info("🚀 Starting Advanced Multi-Timeframe Monitor...")
    
    # Initialize database
    try:
        database.init_database()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return
    
    # Load config
    cfg = config.load_config()
    telegram_creds = config.get_telegram_creds()
    
    symbols = cfg.get('symbols', [])
    min_confluence = cfg.get('min_confluence', 60)
    max_alerts_per_hour = cfg.get('max_alerts_per_hour', 10)
    
    # Check Telegram credentials
    if not telegram_creds['token'] or not telegram_creds['chat_id']:
        logger.error("❌ TELEGRAM CREDENTIALS MISSING! Check .env file")
        logger.error(f"Token: {'✅ Set' if telegram_creds['token'] else '❌ Missing'}")
        logger.error(f"Chat ID: {'✅ Set' if telegram_creds['chat_id'] else '❌ Missing'}")
    else:
        logger.info("✅ Telegram credentials loaded")
    
    logger.info(f"Monitoring {len(symbols)} symbols")
    logger.info(f"Min Confluence: {min_confluence}%")
    logger.info(f"Max Alerts/Hour: {max_alerts_per_hour}")
    logger.info(f"Enabled Timeframes: {[tf for tf, cfg in TIMEFRAMES.items() if cfg['enabled']]}")
    
    # Track last scan time per timeframe
    last_scan = {tf: datetime.now() - timedelta(days=1) for tf in TIMEFRAMES.keys()}
    
    scan_counter = 0
    
    while True:
        try:
            current_time = datetime.now()
            alerts_sent_this_cycle = 0
            
            # Rotate through timeframes (staggered scanning)
            for timeframe in ['5m', '15m', '1h', '4h', '1d']:
                tf_config = TIMEFRAMES[timeframe]
                
                # Check if it's time to scan this timeframe
                time_since_last_scan = current_time - last_scan[timeframe]
                scan_due = time_since_last_scan >= timedelta(minutes=tf_config['scan_interval_minutes'])
                
                if scan_due and tf_config['enabled']:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🔍 Scan #{scan_counter} [{timeframe}]")
                    logger.info(f"{'='*60}")
                    
                    # Scan this timeframe
                    setups = scan_timeframe(symbols, timeframe, cfg, min_confluence)
                    
                    if setups:
                        logger.info(f"Found {len(setups)} qualified setups on {timeframe}")
                        
                        # Sort by weighted confluence (best first)
                        setups.sort(key=lambda x: x['weighted_confluence'], reverse=True)
                        
                        # Process each setup
                        for setup in setups:
                            # Check if we can still send alerts
                            if not is_within_alert_limit(max_alerts_per_hour):
                                logger.warning("⚠️  Alert limit reached, skipping remaining setups")
                                break
                            
                            # Process and alert
                            if process_and_alert(setup, telegram_creds):
                                alerts_sent_this_cycle += 1
                                time.sleep(2)  # Small delay between alerts
                    
                    last_scan[timeframe] = current_time
                    scan_counter += 1
                    
                    # Small pause between timeframe scans
                    time.sleep(5)
            
            # Show summary
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 Cycle Summary: {alerts_sent_this_cycle} alerts sent")
            logger.info(f"{'='*60}\n")
            
            # Sleep before next cycle (use shortest interval)
            sleep_minutes = 5
            logger.info(f"💤 Sleeping for {sleep_minutes} minutes...")
            time.sleep(sleep_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in monitor loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)  # Wait 1 min before retry

if __name__ == "__main__":
    main()
