"""
Data fetching and manipulation helpers for StockDashboard.
"""
import logging
from datetime import datetime

import pandas as pd
import yfinance as yf
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


def get_company_name(ticker: str) -> str:
    """Fetch company name from Yahoo Finance."""
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        name = info.get("longName") or info.get("shortName") or ticker
        logger.info(f"Fetched company name for {ticker}: {name}")
        return name
    except Exception as e:
        logger.warning(f"Failed to fetch company name for {ticker}: {e}")
        return ticker


def get_market_cap(ticker: str) -> float | None:
    """Fetch market cap from Yahoo Finance."""
    try:
        ticker_obj = yf.Ticker(ticker)
        fast_info = ticker_obj.fast_info
        market_cap = fast_info.get("market_cap") if fast_info else None
        if market_cap:
            logger.info(f"Fetched market cap for {ticker}: ${market_cap:,.0f}")
        return market_cap
    except Exception as e:
        logger.warning(f"Failed to fetch market cap for {ticker}: {e}")
        return None


def get_daily_quote_stats(df: pd.DataFrame) -> dict[str, float | None]:
    """
    Extract daily trading statistics from price data.
    
    Returns:
        dict with keys: open, high, low, close, prev_close, volume
    """
    if df.empty or len(df) < 2:
        return {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "prev_close": None,
            "volume": None
        }
    
    current = df.iloc[-1]
    previous = df.iloc[-2]
    
    return {
        "open": float(current.get("Open")) if "Open" in current.index else None,
        "high": float(current.get("High")) if "High" in current.index else None,
        "low": float(current.get("Low")) if "Low" in current.index else None,
        "close": float(current.get("Close")) if "Close" in current.index else None,
        "prev_close": float(previous.get("Close")) if "Close" in previous.index else None,
        "volume": float(current.get("Volume")) if "Volume" in current.index else None,
    }


def format_volume(volume: float | None) -> str:
    """Format volume with K/M/B suffixes."""
    if volume is None or pd.isna(volume):
        return "N/A"
    
    if volume >= 1_000_000_000:
        return f"{volume/1_000_000_000:.1f}B"
    elif volume >= 1_000_000:
        return f"{volume/1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"{volume/1_000:.1f}K"
    else:
        return f"{volume:,.0f}"


def format_market_cap(market_cap: float | None) -> str:
    """Format market cap with T/B/M suffixes."""
    if market_cap is None or pd.isna(market_cap):
        return "N/A"
    
    if market_cap >= 1_000_000_000_000:
        return f"${market_cap/1_000_000_000_000:.2f}T"
    elif market_cap >= 1_000_000_000:
        return f"${market_cap/1_000_000_000:.2f}B"
    elif market_cap >= 1_000_000:
        return f"${market_cap/1_000_000:.2f}M"
    else:
        return f"${market_cap:,.0f}"


def get_market_status() -> str:
    """
    Determine current market status.
    
    Returns:
        "Market Open" | "Pre-Market" | "After Hours" | "Market Closed"
    """
    try:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        
        # Market hours: 9:30 AM - 4:00 PM ET weekdays
        market_open_hour = 9
        market_open_minute = 30
        market_close_hour = 16
        
        is_weekend = weekday >= 5
        
        if is_weekend:
            return "Market Closed"
        
        current_minutes = hour * 60 + minute
        market_open_minutes = market_open_hour * 60 + market_open_minute
        market_close_minutes = market_close_hour * 60
        
        if current_minutes >= market_open_minutes and current_minutes < market_close_minutes:
            return "● Market Open"
        elif current_minutes < market_open_minutes:
            return "◐ Pre-Market"
        else:
            return "◐ After Hours"
    except Exception as e:
        logger.warning(f"Error determining market status: {e}")
        return "Market Status Unknown"


def yahoo_direct_request(ticker: str, interval: str, range_value: str) -> pd.DataFrame:
    """Fetch stock data directly from Yahoo Finance API."""
    import requests
    
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        response = requests.get(
            url,
            params={"interval": interval, "range": range_value, "includePrePost": "false"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        result = data.get("chart", {}).get("result")
        
        if not result:
            logger.warning(f"No result from Yahoo Direct API for {ticker}")
            return pd.DataFrame()
        
        result = result[0]
        timestamps = result.get("timestamp")
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        
        if not timestamps:
            logger.warning(f"No timestamps in Yahoo Direct response for {ticker}")
            return pd.DataFrame()
        
        df = pd.DataFrame({
            "Open": quote.get("open", []),
            "High": quote.get("high", []),
            "Low": quote.get("low", []),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", [])
        })
        df.index = pd.to_datetime(timestamps, unit="s")
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        logger.info(f"Yahoo Direct API returned {len(df)} rows for {ticker}")
        return df
        
    except Timeout as e:
        logger.error(f"Timeout from Yahoo Direct API for {ticker}: {e}")
        raise
    except RequestException as e:
        logger.error(f"Request error from Yahoo Direct API for {ticker}: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Data parsing error from Yahoo Direct API for {ticker}: {e}")
        raise
