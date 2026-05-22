import json
import logging
import re
import time
import uuid
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf
from requests.exceptions import RequestException, Timeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

APP_VERSION = "v0.4.0-improved-bugs-fixes"
MAX_BUBBLES = 4
PROFILE_PATH = Path(__file__).parent / "data" / "profiles.json"
BUBBLE_TYPES = ["Price Chart"]

# Market hours constants (in 24-hour format)
MARKET_OPEN_HOUR = 9.5  # 9:30 AM
MARKET_CLOSE_HOUR = 16  # 4:00 PM

# Ticker validation regex: 1-5 alphanumeric chars, hyphens, periods
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

st.markdown("""
<style>
.stApp{background:#0b1220;color:#f8fafc}header[data-testid="stHeader"]{background:rgba(11,18,32,.86)!important;backdrop-filter:blur(8px)}.block-container{padding-top:2.4rem;max-width:1720px}h1,h2,[...]
header[data-testid="stHeader"] button,button[title*="sidebar"],button[aria-label*="sidebar"]{background:#60a5fa!important;border:2px solid #f8fafc!important;border-radius:12px!important;color:#fff[...]

/* Simple window border: remove experimental layered frame effects. */
div[data-testid="stVerticalBlockBorderWrapper"]{border:4px solid rgba(241,245,249,.82)!important;border-radius:24px!important;background:#0f172a!important;padding:16px 18px!important;margin-bottom[...]

/* Readable controls without broad leakage. */
div[data-testid="stButton"] button,div[data-testid="stButton"] button *{color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap!important;text-shadow:none!important}di[...]
input,textarea,input *,textarea *{color:#020617!important;-webkit-text-fill-color:#020617!important;caret-color:#020617!important}input::placeholder,textarea::placeholder{color:#475569!important;o[...]
div[data-testid="stCheckbox"] label,div[data-testid="stCheckbox"] label *{color:#bfdbfe!important;font-weight:700!important}div[data-testid="stCheckbox"] input[type="checkbox"]{accent-color:#60a5f[...]
div[data-testid="stExpander"]{background:#111827!important;border:1px solid #64748b!important;border-radius:14px!important}div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summa[...]
.bubble-title{font-size:1.05rem;font-weight:900;color:#f8fafc!important;margin-bottom:4px}.bubble-subtitle{font-size:.78rem;color:#93c5fd!important;margin-bottom:10px}.bubble-footer{font-size:.75r[...]
</style>
""", unsafe_allow_html=True)


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
        # Quick validation: try to fetch info from Yahoo Finance
        ticker_obj = yf.Ticker(ticker)
        # Attempt to access info to verify ticker exists
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


def yahoo_direct_request(ticker: str, interval: str, range_value: str) -> pd.DataFrame:
    """Fetch stock data directly from Yahoo Finance API."""
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
        data = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False
        )
        
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            data = data.dropna(subset=["Open", "High", "Low", "Close"])
        
        if not data.empty:
            logger.info(f"yfinance returned {len(data)} rows for {ticker}")
            return data, "OK", connector
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
        data = yahoo_direct_request(ticker, interval, period)
        
        if not data.empty:
            logger.info(f"Yahoo Direct API returned {len(data)} rows for {ticker}")
            return data, "OK (via fallback)", connector
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


def build_price_chart(df: pd.DataFrame, bubble: dict, config: dict, chart_height: int) -> go.Figure:
    """Build candlestick chart with optional moving averages and volume."""
    rows = 2 if bubble["show_volume"] else 1
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.74, 0.26] if rows == 2 else [1]
    )
    
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444"
        ),
        row=1,
        col=1
    )
    
    if bubble["show_ma"] and config["allow_ma"]:
        for label, window, color in [("20 MA", 20, "#f97316"), ("50 MA", 50, "#14b8a6"), ("200 MA", 200, "#8b5cf6")]:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Close"].rolling(window=window, min_periods=1).mean(),
                    mode="lines",
                    name=label,
                    line=dict(color=color, width=1.8)
                ),
                row=1,
                col=1
            )
    
    if bubble["show_volume"]:
        colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="Volume",
                opacity=0.55,
                marker_color=colors
            ),
            row=2,
            col=1
        )
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    fig.update_layout(
        template="plotly_dark",
        height=chart_height,
        paper_bgcolor="rgba(17,24,39,0)",
        plot_bgcolor="rgba(17,24,39,.78)",
        font=dict(color="#e5e7eb", size=12),
        legend=dict(font=dict(size=11), x=0.01, y=0.99),
        margin=dict(l=60, r=20, t=60, b=40),
        hovermode="x unified"
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#334155",
        tickfont=dict(color="#cbd5e1", size=11),
        rangebreaks=config["rangebreaks"]
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#334155",
        tickfont=dict(color="#cbd5e1", size=11)
    )
    
    fig.update_yaxes(title_text="Price", row=1, col=1)
    return fig


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
    """Render individual bubble with controls and chart."""
    bubble_id = bubble["id"]
    config = PERIOD_CONFIG[bubble["timeframe"]]
    
    with st.container(border=True):
        title_col, menu_col = st.columns([0.68, 0.32], vertical_alignment="top")
        
        with title_col:
            st.markdown(f'<div class="bubble-title">{bubble["ticker"]} • {bubble["bubble_type"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bubble-subtitle">{bubble["timeframe"]} · independent dashboard bubble</div>', unsafe_allow_html=True)
        
        with menu_col:
            with st.expander("Menu", expanded=False):
                selected_ticker = st.selectbox(
                    "Stock ticker",
                    all_tickers,
                    index=all_tickers.index(bubble["ticker"]) if bubble["ticker"] in all_tickers else 0,
                    key=f"ticker_{bubble_id}"
                )
                custom_ticker = st.text_input("Or type ticker", value="", key=f"custom_ticker_{bubble_id}")
                selected_timeframe = st.selectbox(
                    "Timeframe",
                    list(PERIOD_CONFIG.keys()),
                    index=list(PERIOD_CONFIG.keys()).index(bubble["timeframe"]),
                    key=f"timeframe_{bubble_id}"
                )
                selected_type = st.selectbox(
                    "Bubble type",
                    BUBBLE_TYPES,
                    index=0,
                    key=f"type_{bubble_id}"
                )
                show_ma = st.checkbox("Moving averages", value=bubble["show_ma"], key=f"ma_{bubble_id}")
                show_volume = st.checkbox("Volume", value=bubble["show_volume"], key=f"volume_{bubble_id}")
                
                if st.button("Apply", key=f"apply_{bubble_id}", use_container_width=True):
                    final_ticker = custom_ticker.upper().strip() or selected_ticker
                    
                    # Validate ticker before applying
                    is_valid, validation_msg = validate_ticker(final_ticker)
                    if not is_valid:
                        st.error(validation_msg)
                        logger.warning(f"Invalid ticker provided: {final_ticker}")
                    else:
                        bubble.update({
                            "ticker": final_ticker,
                            "timeframe": selected_timeframe,
                            "bubble_type": selected_type,
                            "show_ma": show_ma,
                            "show_volume": show_volume
                        })
                        logger.info(f"Updated bubble {bubble_id}: ticker={final_ticker}, timeframe={selected_timeframe}")
                        st.rerun()
                
                c1, c2 = st.columns([1.25, 1.0])
                with c1:
                    if st.button("Duplicate", key=f"duplicate_{bubble_id}", use_container_width=True):
                        duplicate_bubble(bubble)
                
                with c2:
                    if st.button("Remove", key=f"remove_{bubble_id}", use_container_width=True):
                        remove_bubble(bubble_id)
        
        with st.spinner(f"Loading {bubble['ticker']}..."):
            df, status, connector = get_price_data(bubble["ticker"], config["period"], config["interval"])
        
        if df.empty:
            st.warning(f"⚠️ {status}")
            logger.warning(f"No data available for {bubble['ticker']}: {status}")
        else:
            latest = df.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Ticker", bubble["ticker"])
            m2.metric("Last Price", f"${latest['Close']:,.2f}")
            m3.metric("Rows", f"{len(df):,}")
            st.plotly_chart(
                build_price_chart(df.copy(), bubble, config, chart_height),
                use_container_width=True,
                key=f"chart_{bubble_id}",
                config={"displayModeBar": "hover", "displaylogo": False}
            )
        
        st.markdown(
            f'<div class="bubble-footer">Source: {connector} · Status: {status} · Updated: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>',
            unsafe_allow_html=True
        )


def render_layout(bubbles: list[dict], all_tickers: list[str], chart_height: int) -> None:
    """Render bubbles in responsive grid layout. Scalable to any number of bubbles."""
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
        # Validate ticker before adding to profile
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
st.title("Stock Dashboard")
st.caption("Bubble-based dashboard layout · each bubble is an independent chart instance")

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
