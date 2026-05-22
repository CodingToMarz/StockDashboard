import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf
from requests.exceptions import RequestException

# Import new helper modules
import data
import charts
import styles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

APP_VERSION = "v0.5.0-tradingview-style"
MAX_BUBBLES = 4
PROFILE_PATH = Path(__file__).parent / "data" / "profiles.json"
BUBBLE_TYPES = ["Price Chart"]

# Market hours constants
MARKET_OPEN_HOUR = 9.5
MARKET_CLOSE_HOUR = 16

# Ticker validation regex
TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,5}$")

PERIOD_CONFIG = {
    "1D": {"period": "1d", "interval": "5m", "allow_ma": False, "rangebreaks": [dict(bounds=[MARKET_CLOSE_HOUR, MARKET_OPEN_HOUR], pattern="hour")]},
    "5D": {"period": "5d", "interval": "15m", "allow_ma": False, "rangebreaks": [dict(bounds=["sat", "mon"]), dict(bounds=[MARKET_CLOSE_HOUR, MARKET_OPEN_HOUR], pattern="hour")]},
    "1M": {"period": "1mo", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "6M": {"period": "6mo", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "1Y": {"period": "1y", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "5Y": {"period": "5y", "interval": "1wk", "allow_ma": True, "rangebreaks": []},
    "MAX": {"period": "max", "interval": "1mo", "allow_ma": True, "rangebreaks": []},
}

st.set_page_config(page_title="Stock Dashboard", layout="wide", initial_sidebar_state="expanded")

# Apply CSS styling
st.markdown(styles.get_app_css(), unsafe_allow_html=True)


def load_profiles() -> dict:
    """Load stock profiles from JSON file. Creates default profiles if file doesn't exist."""
    try:
        if not PROFILE_PATH.exists():
            PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            default_profiles = {"AI Stocks": ["NVDA", "AMD", "MSFT"], "Space": ["RKLB", "LUNR"]}
            PROFILE_PATH.write_text(json.dumps(default_profiles, indent=2))
            logger.info("Created default profiles")
        profiles = json.loads(PROFILE_PATH.read_text())
        logger.info(f"Loaded {len(profiles)} profiles")
        return profiles
    except IOError as e:
        logger.error(f"Failed to load profiles: {e}")
        return {"Default": ["NVDA"]}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in profiles file: {e}")
        return {"Default": ["NVDA"]}


def save_profiles(profiles: dict) -> None:
    """Save stock profiles to JSON file with error handling."""
    try:
        PROFILE_PATH.write_text(json.dumps(profiles, indent=2))
        logger.info("Profiles saved successfully")
    except IOError as e:
        logger.error(f"Failed to save profiles: {e}")
        st.error(f"Failed to save profiles: {e}")


def get_all_tickers(profiles: dict) -> list[str]:
    """Extract and sort all unique tickers from all profiles."""
    return sorted({ticker for group in profiles.values() for ticker in group}) or ["NVDA"]


def validate_ticker(ticker: str) -> tuple[bool, str]:
    """
    Validate ticker format and existence on Yahoo Finance.
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not ticker:
        return False, "Ticker cannot be empty"
    
    if not TICKER_PATTERN.match(ticker):
        return False, f"Invalid ticker format: '{ticker}'. Use 1-5 alphanumeric characters, hyphens, or periods."
    
    try:
        ticker_obj = yf.Ticker(ticker)
        _ = ticker_obj.info
        logger.info(f"Validated ticker: {ticker}")
        return True, "Valid ticker"
    except (KeyError, IndexError) as e:
        logger.warning(f"Ticker validation failed for {ticker}: {e}")
        return False, f"Ticker '{ticker}' not found on Yahoo Finance"
    except RequestException as e:
        logger.warning(f"Network error validating ticker {ticker}: {e}")
        return False, f"Network error validating ticker (please try again)"
    except Exception as e:
        logger.error(f"Unexpected error validating ticker {ticker}: {e}")
        return False, f"Error validating ticker: {str(e)}"


def default_bubble(ticker: str = "NVDA") -> dict:
    """Create a default bubble configuration with unique ID."""
    return {
        "id": str(uuid.uuid4())[:8],
        "ticker": ticker,
        "timeframe": "6M",
        "bubble_type": "Price Chart",
        "show_ma": True,
        "show_volume": True
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_price_data(ticker: str, period: str, interval: str) -> tuple[pd.DataFrame, str, str]:
    """
    Fetch price data from multiple connectors with fallback strategy.
    
    Returns:
        tuple: (dataframe, status_message, connector_used)
    """
    connector = "yfinance"
    last_error = None
    
    # Try yfinance first
    try:
        logger.info(f"Fetching {ticker} via yfinance (period={period}, interval={interval})")
        df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False
        )
        
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
        
        if not df.empty:
            logger.info(f"yfinance returned {len(df)} rows for {ticker}")
            return df, "OK", connector
        else:
            logger.warning(f"yfinance returned empty data for {ticker}")
            last_error = "yfinance returned no data"
            
    except RequestException as e:
        logger.warning(f"yfinance request error for {ticker}: {e}")
        last_error = f"yfinance network error: {str(e)}"
    except Exception as e:
        logger.warning(f"yfinance error for {ticker}: {e}")
        last_error = f"yfinance error: {str(e)}"
    
    # Fallback to Yahoo Direct API
    connector = "Yahoo Direct API"
    try:
        logger.info(f"Falling back to Yahoo Direct API for {ticker}")
        df = data.yahoo_direct_request(ticker, interval, period)
        
        if not df.empty:
            logger.info(f"Yahoo Direct API returned {len(df)} rows for {ticker}")
            return df, "OK (via fallback)", connector
        else:
            logger.warning(f"Yahoo Direct API returned empty data for {ticker}")
            last_error = "Both connectors returned no data"
            
    except RequestException as e:
        logger.error(f"Yahoo Direct API request error for {ticker}: {e}")
        last_error = f"Yahoo Direct API error: {str(e)}"
    except Exception as e:
        logger.error(f"Yahoo Direct API error for {ticker}: {e}")
        last_error = f"Yahoo Direct API error: {str(e)}"
    
    # Both connectors failed
    error_msg = f"Failed to fetch data: {last_error}"
    logger.error(f"{error_msg} (ticker: {ticker})")
    return pd.DataFrame(), error_msg, connector


def remove_bubble(bubble_id: str) -> bool:
    """Remove bubble by ID. Prevents removing last bubble. Returns success status."""
    if len(st.session_state.bubbles) <= 1:
        st.warning("Keep at least one bubble.")
        logger.info("Attempted to remove last bubble - operation blocked")
        return False
    
    st.session_state.bubbles = [b for b in st.session_state.bubbles if b["id"] != bubble_id]
    logger.info(f"Removed bubble {bubble_id}")
    st.rerun()
    return True


def duplicate_bubble(bubble: dict) -> bool:
    """Duplicate a bubble. Prevents exceeding MAX_BUBBLES. Returns success status."""
    if len(st.session_state.bubbles) >= MAX_BUBBLES:
        st.warning(f"Maximum of {MAX_BUBBLES} bubbles reached.")
        logger.info(f"Attempted to duplicate bubble - max limit ({MAX_BUBBLES}) reached")
        return False
    
    new_bubble = bubble.copy()
    new_bubble["id"] = str(uuid.uuid4())[:8]
    st.session_state.bubbles.append(new_bubble)
    logger.info(f"Duplicated bubble {bubble['id']} to {new_bubble['id']}")
    st.rerun()
    return True


def render_bubble(bubble: dict, all_tickers: list[str], chart_height: int) -> None:
    """Render TradingView-style bubble with header, stats, timeframes, and chart."""
    bubble_id = bubble["id"]
    config = PERIOD_CONFIG[bubble["timeframe"]]
    
    with st.container(border=True):
        # Fetch data
        with st.spinner(f"Loading {bubble['ticker']}..."):
            df, status, connector = get_price_data(bubble["ticker"], config["period"], config["interval"])
        
        if df.empty:
            st.warning(f"⚠️ {status}")
            logger.warning(f"No data available for {bubble['ticker']}: {status}")
        else:
            # Extract statistics
            stats = data.get_daily_quote_stats(df)
            company_name = data.get_company_name(bubble["ticker"])
            market_cap = data.get_market_cap(bubble["ticker"])
            market_status = data.get_market_status()
            
            latest_close = stats["close"]
            prev_close = stats["prev_close"]
            price_change = latest_close - prev_close if prev_close else 0
            pct_change = (price_change / prev_close * 100) if prev_close else 0
            
            # === PHASE 1: TradingView Header ===
            st.markdown(
                styles.get_bubble_header_html(
                    ticker=bubble["ticker"],
                    company_name=company_name,
                    price=latest_close,
                    price_change=price_change,
                    pct_change=pct_change,
                    market_status=market_status,
                    last_update=datetime.now()
                ),
                unsafe_allow_html=True
            )
            
            # === PHASE 2: Financial Stats Strip ===
            st.markdown(
                styles.get_stats_strip_html(
                    open_price=stats["open"],
                    high=stats["high"],
                    low=stats["low"],
                    prev_close=stats["prev_close"],
                    volume=data.format_volume(stats["volume"]),
                    market_cap=data.format_market_cap(market_cap)
                ),
                unsafe_allow_html=True
            )
            
            # === PHASE 4: Timeframe Button Row ===
            st.markdown(
                styles.get_timeframe_buttons_html(
                    timeframes=list(PERIOD_CONFIG.keys()),
                    active_timeframe=bubble["timeframe"],
                    bubble_id=bubble_id
                ),
                unsafe_allow_html=True
            )
            
            # Timeframe selection in sidebar menu
            col_tf, col_menu = st.columns([0.7, 0.3])
            with col_tf:
                # Timeframe buttons (alternative clickable version)
                tf_cols = st.columns(len(PERIOD_CONFIG))
                for i, tf in enumerate(PERIOD_CONFIG.keys()):
                    with tf_cols[i]:
                        if st.button(tf, key=f"tf_{bubble_id}_{tf}", use_container_width=True):
                            bubble["timeframe"] = tf
                            logger.info(f"Changed timeframe to {tf} for bubble {bubble_id}")
                            st.rerun()
            
            with col_menu:
                with st.expander("⚙️ Menu", expanded=False):
                    selected_ticker = st.selectbox(
                        "Stock ticker",
                        all_tickers,
                        index=all_tickers.index(bubble["ticker"]) if bubble["ticker"] in all_tickers else 0,
                        key=f"ticker_{bubble_id}"
                    )
                    custom_ticker = st.text_input("Or type ticker", value="", key=f"custom_ticker_{bubble_id}")
                    show_ma = st.checkbox("Moving averages", value=bubble["show_ma"], key=f"ma_{bubble_id}")
                    show_volume = st.checkbox("Volume", value=bubble["show_volume"], key=f"volume_{bubble_id}")
                    
                    if st.button("Apply", key=f"apply_{bubble_id}", use_container_width=True):
                        final_ticker = custom_ticker.upper().strip() or selected_ticker
                        
                        is_valid, validation_msg = validate_ticker(final_ticker)
                        if not is_valid:
                            st.error(validation_msg)
                            logger.warning(f"Invalid ticker provided: {final_ticker}")
                        else:
                            bubble.update({
                                "ticker": final_ticker,
                                "show_ma": show_ma,
                                "show_volume": show_volume
                            })
                            logger.info(f"Updated bubble {bubble_id}: ticker={final_ticker}")
                            st.rerun()
                    
                    c1, c2 = st.columns([1.25, 1.0])
                    with c1:
                        if st.button("Duplicate", key=f"duplicate_{bubble_id}", use_container_width=True):
                            duplicate_bubble(bubble)
                    
                    with c2:
                        if st.button("Remove", key=f"remove_{bubble_id}", use_container_width=True):
                            remove_bubble(bubble_id)
            
            # === PHASE 5: Chart Polish ===
            st.plotly_chart(
                charts.build_price_chart(df.copy(), bubble, config, chart_height),
                use_container_width=True,
                key=f"chart_{bubble_id}",
                config={"displayModeBar": "hover", "displaylogo": False}
            )
        
        # Footer
        st.markdown(
            f'<div style="font-size: 0.75rem; color: #94a3b8; text-align: right; margin-top: 8px;">Source: {connector} · Status: {status} · Updated: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>',
            unsafe_allow_html=True
        )


def render_layout(bubbles: list[dict], all_tickers: list[str], chart_height: int) -> None:
    """Render bubbles in responsive grid layout."""
    count = len(bubbles)
    
    if count == 1:
        render_bubble(bubbles[0], all_tickers, chart_height)
    elif count == 2:
        cols = st.columns(2)
        for i, bubble in enumerate(bubbles):
            with cols[i]:
                render_bubble(bubble, all_tickers, chart_height)
    elif count == 3:
        top = st.columns(2)
        with top[0]:
            render_bubble(bubbles[0], all_tickers, chart_height)
        with top[1]:
            render_bubble(bubbles[1], all_tickers, chart_height)
        render_bubble(bubbles[2], all_tickers, chart_height)
    elif count >= 4:
        top, bottom = st.columns(2), st.columns(2)
        with top[0]:
            render_bubble(bubbles[0], all_tickers, chart_height)
        with top[1]:
            render_bubble(bubbles[1], all_tickers, chart_height)
        with bottom[0]:
            render_bubble(bubbles[2], all_tickers, chart_height)
        with bottom[1]:
            render_bubble(bubbles[3], all_tickers, chart_height)


# Initialize session state and load data
profiles = load_profiles()
all_tickers = get_all_tickers(profiles)

if "bubbles" not in st.session_state:
    st.session_state.bubbles = [default_bubble(all_tickers[0])]
    logger.info("Initialized session state with default bubble")

# Sidebar configuration
st.sidebar.title("Stock Profiles")
st.sidebar.caption(f"Version: {APP_VERSION}")
selected_profile = st.sidebar.selectbox("Select Profile", list(profiles.keys()))

new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add To Profile"):
    ticker = new_ticker.upper().strip()
    
    if not ticker:
        st.sidebar.error("Ticker cannot be empty")
    elif ticker in profiles[selected_profile]:
        st.sidebar.warning(f"{ticker} already in profile")
        logger.info(f"Attempted to add duplicate ticker {ticker} to {selected_profile}")
    else:
        is_valid, validation_msg = validate_ticker(ticker)
        if not is_valid:
            st.sidebar.error(validation_msg)
            logger.warning(f"Invalid ticker {ticker} attempted to be added to profile: {validation_msg}")
        else:
            profiles[selected_profile].append(ticker)
            save_profiles(profiles)
            all_tickers = get_all_tickers(profiles)
            st.sidebar.success(f"Added {ticker}")
            logger.info(f"Added ticker {ticker} to profile {selected_profile}")
            st.rerun()

if st.sidebar.button("+ Add Bubble"):
    if len(st.session_state.bubbles) < MAX_BUBBLES:
        default_ticker = (
            profiles[selected_profile][0]
            if profiles[selected_profile]
            else all_tickers[0]
        )
        st.session_state.bubbles.append(default_bubble(default_ticker))
        logger.info(f"Added new bubble with ticker {default_ticker}")
        st.rerun()
    else:
        st.sidebar.warning(f"Maximum of {MAX_BUBBLES} bubbles reached.")
        logger.info(f"Attempted to add bubble - max limit ({MAX_BUBBLES}) reached")

st.sidebar.caption(f"Active bubbles: {len(st.session_state.bubbles)} / {MAX_BUBBLES}")

# Main content
st.title("📈 Stock Dashboard")
st.caption("TradingView-style bubble dashboard · Each bubble is an independent chart instance")

count = len(st.session_state.bubbles)
height = 520 if count <= 2 else 430

render_layout(st.session_state.bubbles, all_tickers, height)

st.divider()
st.subheader("Data connection check")
with st.expander("Show diagnostics", expanded=False):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Active bubbles: `{len(st.session_state.bubbles)}`")
    st.write(f"Profiles loaded: `{len(profiles)}`")
    st.write(f"Unique tickers: `{len(all_tickers)}`")
    st.write(f"Cache TTL: `3600 seconds (1 hour)`")
    st.write("Bubble data:")
    st.json(st.session_state.bubbles)
    st.write("Profile data:")
    st.json(profiles)
