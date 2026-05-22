"""
Data fetching and processing helpers for StockDashboard.
Handles ticker validation, company info, market stats, and formatting.
"""

import logging
from datetime import datetime
import pandas as pd
import yfinance as yf
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def get_company_name(ticker: str) -> str:
    """
    Fetch company name for ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Company name or ticker if not found
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        name = ticker_obj.info.get("longName") or ticker_obj.info.get("shortName") or ticker
        logger.info(f"Fetched company name for {ticker}: {name}")
        return name
    except (KeyError, RequestException) as e:
        logger.warning(f"Could not fetch company name for {ticker}: {e}")
        return ticker
    except Exception as e:
        logger.error(f"Unexpected error fetching company name for {ticker}: {e}")
        return ticker


def get_market_cap(ticker: str) -> str:
    """
    Fetch and format market cap for ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Formatted market cap string (e.g., "2.5T") or "N/A"
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        market_cap = ticker_obj.info.get("marketCap")
        
        if market_cap is None:
            return "N/A"
        
        return format_market_cap(market_cap)
    except (KeyError, RequestException) as e:
        logger.warning(f"Could not fetch market cap for {ticker}: {e}")
        return "N/A"
    except Exception as e:
        logger.error(f"Unexpected error fetching market cap for {ticker}: {e}")
        return "N/A"


def get_daily_quote_stats(df: pd.DataFrame, ticker: str = None) -> dict:
    """
    Extract daily OHLCV stats from dataframe.
    
    Args:
        df: Price dataframe with OHLCV columns
        ticker: Optional ticker for fetching previous close
        
    Returns:
        dict with open, high, low, close, volume, prev_close, change, change_pct
    """
    if df.empty:
        return {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "prev_close": None,
            "change": None,
            "change_pct": None
        }
    
    try:
        latest = df.iloc[-1]
        open_price = latest.get("Open")
        high_price = latest.get("High")
        low_price = latest.get("Low")
        close_price = latest.get("Close")
        volume = latest.get("Volume")
        
        # Try to get previous close from yesterday's data
        prev_close = None
        if len(df) > 1:
            prev_close = df.iloc[-2].get("Close")
        
        # If not available in df, fetch from yfinance
        if prev_close is None and ticker:
            try:
                ticker_obj = yf.Ticker(ticker)
                prev_close = ticker_obj.info.get("previousClose")
            except Exception as e:
                logger.warning(f"Could not fetch previous close for {ticker}: {e}")
        
        # Calculate change if we have close and prev_close
        change = None
        change_pct = None
        if close_price is not None and prev_close is not None:
            change = close_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
        
        stats = {
            "open": float(open_price) if open_price else None,
            "high": float(high_price) if high_price else None,
            "low": float(low_price) if low_price else None,
            "close": float(close_price) if close_price else None,
            "volume": float(volume) if volume else None,
            "prev_close": float(prev_close) if prev_close else None,
            "change": float(change) if change is not None else None,
            "change_pct": float(change_pct) if change_pct is not None else None
        }
        
        logger.info(f"Extracted stats for {ticker}: close=${stats['close']:.2f}, change={stats['change_pct']:.2f}%")
        return stats
        
    except Exception as e:
        logger.error(f"Error extracting stats from dataframe: {e}")
        return {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "prev_close": None,
            "change": None,
            "change_pct": None
        }


def format_volume(volume: float) -> str:
    """
    Format volume as human-readable string.
    
    Args:
        volume: Volume number
        
    Returns:
        Formatted string (e.g., "1.2M", "500K", "2.5B")
    """
    if volume is None:
        return "N/A"
    
    try:
        volume = float(volume)
        
        if volume >= 1e9:
            return f"{volume / 1e9:.1f}B"
        elif volume >= 1e6:
            return f"{volume / 1e6:.1f}M"
        elif volume >= 1e3:
            return f"{volume / 1e3:.1f}K"
        else:
            return f"{int(volume)}"
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not format volume {volume}: {e}")
        return "N/A"


def format_market_cap(market_cap: float) -> str:
    """
    Format market cap as human-readable string.
    
    Args:
        market_cap: Market cap value
        
    Returns:
        Formatted string (e.g., "2.5T", "500B", "1.2M")
    """
    if market_cap is None:
        return "N/A"
    
    try:
        market_cap = float(market_cap)
        
        if market_cap >= 1e12:
            return f"${market_cap / 1e12:.2f}T"
        elif market_cap >= 1e9:
            return f"${market_cap / 1e9:.2f}B"
        elif market_cap >= 1e6:
            return f"${market_cap / 1e6:.2f}M"
        else:
            return f"${int(market_cap)}"
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not format market cap {market_cap}: {e}")
        return "N/A"


def get_market_status() -> str:
    """
    Determine current market status.
    
    Returns:
        Status string: "Market Open", "Pre-Market", "After Hours", or "Market Closed"
    """
    try:
        now = datetime.now()
        weekday = now.weekday()  # 0-4 = Mon-Fri, 5-6 = Sat-Sun
        hour = now.hour
        minute = now.minute
        
        # Market closed on weekends
        if weekday >= 5:
            return "Market Closed"
        
        # Market hours: 9:30 AM - 4:00 PM ET (13:30 - 20:00 UTC)
        # Note: This is simplified and doesn't account for holidays
        current_time_minutes = hour * 60 + minute
        
        open_time = 9 * 60 + 30  # 9:30 AM
        close_time = 16 * 60      # 4:00 PM
        
        if current_time_minutes < open_time:
            return "Pre-Market"
        elif current_time_minutes < close_time:
            return "Market Open"
        else:
            return "After Hours"
            
    except Exception as e:
        logger.error(f"Error determining market status: {e}")
        return "Unknown"
