#!/usr/bin/env python3
"""
Quick test script to verify Telegram setup and database
"""
import os
from dotenv import load_dotenv
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

print("="*60)
print("🔍 BYBIT CRYPTO ANALYZER - SYSTEM CHECK")
print("="*60)

# 1. Check Telegram credentials
print("\n1️⃣  TELEGRAM CREDENTIALS")
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if token:
    print(f"   ✅ Bot Token: {token[:10]}...{token[-5:]}")
else:
    print("   ❌ Bot Token: MISSING!")
    print("   → Add TELEGRAM_BOT_TOKEN to .env file")

if chat_id:
    print(f"   ✅ Chat ID: {chat_id}")
else:
    print("   ❌ Chat ID: MISSING!")
    print("   → Add TELEGRAM_CHAT_ID to .env file")

# 2. Test Telegram connection
if token and chat_id:
    print("\n2️⃣  TESTING TELEGRAM CONNECTION...")
    try:
        import alerts
        success, error = alerts.send_telegram_message(
            token,
            chat_id,
            "🎉 TEST MESSAGE from Bybit Analyzer\n\nIf you see this, Telegram alerts are working!"
        )
        
        if success:
            print("   ✅ Message sent successfully!")
            print("   → Check your Telegram app")
        else:
            print(f"   ❌ Failed: {error}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
else:
    print("\n2️⃣  SKIPPING Telegram test (credentials missing)")

# 3. Check database
print("\n3️⃣  DATABASE CHECK")
try:
    import database
    database.init_database()
    print("   ✅ Database initialized: ./data/trading.db")
    
    # Check if there are any saved signals
    signals = database.get_signals(limit=5)
    if signals:
        print(f"   📊 Found {len(signals)} recent signals in database")
        for sig in signals[:3]:
            print(f"      - {sig['symbol']} {sig['signal_type']} ({sig['status']})")
    else:
        print("   📭 No signals in database yet (monitor will populate)")
        
except Exception as e:
    print(f"   ❌ Database error: {e}")

# 4. Check config
print("\n4️⃣  CONFIGURATION")
try:
    import config
    cfg = config.load_config()
    print(f"   ✅ Symbols: {len(cfg.get('symbols', []))} configured")
    print(f"   ✅ Min Confluence: {cfg.get('min_confluence', 60)}%")
    print(f"   ✅ Max Alerts/Hour: {cfg.get('max_alerts_per_hour', 10)}")
except Exception as e:
    print(f"   ❌ Config error: {e}")

print("\n" + "="*60)
print("✅ SYSTEM CHECK COMPLETE")
print("="*60)
print("\n💡 Next steps:")
print("   1. If Telegram test failed, check credentials in .env")
print("   2. Run: docker-compose restart")
print("   3. Check monitor logs: docker logs crypto_analyzer_monitor -f")
print()
