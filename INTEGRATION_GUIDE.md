# INTEGRATION INSTRUCTIONS FOR APP.PY
# ====================================

## Step 1: Update Imports (at the top of app.py after line 6)
Add these import statements:
```python
import database
import trade_journal
import analytics
from datetime import datetime, timedelta
```

## Step 2: Update Sidebar Navigation (around line 166)
Find the line:
```python
page = st.sidebar.radio("Go to", ["📊 Dashboard", "🔍 Multi-Screener", "🧪 Backtester"])
```

Replace it with:
```python
page = st.sidebar.radio("Go to", [
    "📊 Dashboard", 
    "🔍 Multi-Screener", 
    "🧪 Backtester",
    "📜 Signal History",
    "📒 Trade Journal",
    "📊 Analytics"
])
```

## Step 3: Add New Page Implementations
At the END of app.py  (before the `if __name__ == "__main__":` line at line 604), 
copy and paste the ENTIRE content from new_pages.py starting from:
```python
# ==========================================
# PAGE 4: SIGNAL HISTORY
# ==========================================
elif page == "📜 Signal History":
```

All the way to the end of the Analytics page implementation.

This will add all 3 new pages to your app!

## Files Created:
1. `database.py` - SQLite database management
2. `trade_journal.py` - Trade tracking functions
3. `analytics.py` - Performance analytics
4. `new_pages.py` - The page implementations (copy from this file)

## After Integration:
Run: `docker-compose restart` to apply all changes!
