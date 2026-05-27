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

import charts
import data
import styles

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

APP_VERSION = "v0.5.2-live-refresh-fix"
MAX_BUBBLES = 4
PRICE_CACHE_TTL_SECONDS = 60
PROFILE_PATH = Path(__file__).parent / "data" / "profiles.json"
TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-]{1,8}$")

PERIOD_CONFIG = {
    "1D": {"period": "1d", "interval": "5m", "allow_ma": False, "rangebreaks": [dict(bounds=[16, 9.5], pattern="hour")]},
    "5D": {"period": "5d", "interval": "15m", "allow_ma": False, "rangebreaks": [dict(bounds=["sat", "mon"]), dict(bounds=[16, 9.5], pattern="hour")]},
    "1M": {"period": "1mo", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "6M": {"period": "6mo", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "1Y": {"period": "1y", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "5Y": {"period": "5y", "interval": "1wk", "allow_ma": True, "rangebreaks": []},
    "MAX": {"period": "max", "interval": "1mo", "allow_ma": True, "rangebreaks": []},
}

st.set_page_config(page_title="Stock Dashboard", layout="wide", initial_sidebar_state="expanded")
st.markdown(styles.get_app_css(), unsafe_allow_html=True)


def load_profiles() -> dict:
    try:
        if not PROFILE_PATH.exists():
            PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            PROFILE_PATH.write_text(json.dumps({"AI Stocks": ["NVDA", "AMD", "MSFT"], "Space": ["RKLB", "LUNR"]}, indent=2))
        return json.loads(PROFILE_PATH.read_text())
    except Exception as exc:
        logger.error("Failed to load profiles: %s", exc)
        return {"Default": ["NVDA"]}


def save_profiles(profiles: dict) -> None:
    try:
        PROFILE_PATH.write_text(json.dumps(profiles, indent=2))
    except Exception as exc:
        st.error(f"Failed to save profiles: {exc}")


def get_all_tickers(profiles: dict) -> list[str]:
    return sorted({ticker for tickers in profiles.values() for ticker in tickers}) or ["NVDA"]


def validate_ticker(ticker: str) -> tuple[bool, str]:
    if not ticker:
        return False, "Ticker cannot be empty"
    if not TICKER_PATTERN.match(ticker):
        return False, f"Invalid ticker format: {ticker}"
    return True, "Valid ticker format"


def default_bubble(ticker: str = "NVDA") -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "ticker": ticker.upper().strip(),
        "timeframe": "6M",
        "bubble_type": "Price Chart",
        "show_ma": True,
        "show_volume": True,
    }


def clear_price_caches() -> None:
    get_price_data.clear()
    get_live_quote.clear()


@st.cache_data(ttl=PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def get_live_quote(ticker: str) -> dict:
    quote = {"price": None, "prev_close": None, "open": None, "high": None, "low": None, "volume": None, "market_cap": None}
    try:
        fast = yf.Ticker(ticker).fast_info
        if fast:
            quote.update({
                "price": fast.get("last_price") or fast.get("regular_market_price"),
                "prev_close": fast.get("previous_close") or fast.get("regular_market_previous_close"),
                "open": fast.get("open") or fast.get("regular_market_open"),
                "high": fast.get("day_high") or fast.get("regular_market_day_high"),
                "low": fast.get("day_low") or fast.get("regular_market_day_low"),
                "volume": fast.get("last_volume") or fast.get("regular_market_volume"),
                "market_cap": fast.get("market_cap"),
            })
    except Exception as exc:
        logger.warning("Live quote failed for %s: %s", ticker, exc)
    return quote


@st.cache_data(ttl=PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def get_price_data(ticker: str, period: str, interval: str) -> tuple[pd.DataFrame, str, str]:
    try:
        df = yf.download(tickers=ticker, period=period, interval=interval, auto_adjust=False, progress=False, threads=False, prepost=True)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if not df.empty:
            return df, "OK", "yfinance"
    except RequestException as exc:
        logger.warning("yfinance request failed for %s: %s", ticker, exc)
    except Exception as exc:
        logger.warning("yfinance failed for %s: %s", ticker, exc)

    try:
        df = data.yahoo_direct_request(ticker, interval, period)
        if not df.empty:
            return df, "OK (via fallback)", "Yahoo Direct API"
    except Exception as exc:
        logger.warning("Yahoo fallback failed for %s: %s", ticker, exc)
    return pd.DataFrame(), "No price data returned", "No connector"


def choose(primary, fallback):
    return primary if primary is not None and not pd.isna(primary) else fallback


def remove_bubble(bubble_id: str) -> None:
    if len(st.session_state.bubbles) <= 1:
        st.warning("Keep at least one bubble.")
        return
    st.session_state.bubbles = [b for b in st.session_state.bubbles if b["id"] != bubble_id]
    st.rerun()


def duplicate_bubble(bubble: dict) -> None:
    if len(st.session_state.bubbles) >= MAX_BUBBLES:
        st.warning(f"Maximum of {MAX_BUBBLES} bubbles reached.")
        return
    new_bubble = bubble.copy()
    new_bubble["id"] = str(uuid.uuid4())[:8]
    st.session_state.bubbles.append(new_bubble)
    st.rerun()


def render_bubble(bubble: dict, all_tickers: list[str], chart_height: int) -> None:
    bubble_id = bubble["id"]
    bubble["ticker"] = bubble["ticker"].upper().strip()
    config = PERIOD_CONFIG[bubble["timeframe"]]

    with st.container(border=True):
        with st.spinner(f"Loading {bubble['ticker']}..."):
            df, status, connector = get_price_data(bubble["ticker"], config["period"], config["interval"])
            live_quote = get_live_quote(bubble["ticker"])

        if df.empty:
            st.warning(f"⚠️ {status}")
        else:
            stats = data.get_daily_quote_stats(df)
            latest = choose(live_quote.get("price"), stats["close"])
            prev_close = choose(live_quote.get("prev_close"), stats["prev_close"])
            price_change = latest - prev_close if latest is not None and prev_close else 0
            pct_change = (price_change / prev_close * 100) if prev_close else 0
            market_cap = live_quote.get("market_cap") or data.get_market_cap(bubble["ticker"])

            st.markdown(styles.get_bubble_header_html(
                ticker=bubble["ticker"],
                company_name=data.get_company_name(bubble["ticker"]),
                price=latest,
                price_change=price_change,
                pct_change=pct_change,
                market_status=data.get_market_status(),
                last_update=datetime.now(),
            ), unsafe_allow_html=True)

            st.markdown(styles.get_stats_strip_html(
                open_price=choose(live_quote.get("open"), stats["open"]),
                high=choose(live_quote.get("high"), stats["high"]),
                low=choose(live_quote.get("low"), stats["low"]),
                prev_close=prev_close,
                volume=data.format_volume(choose(live_quote.get("volume"), stats["volume"])),
                market_cap=data.format_market_cap(market_cap),
            ), unsafe_allow_html=True)

            col_tf, col_menu = st.columns([0.7, 0.3])
            with col_tf:
                st.caption("Timeframe")
                tf_cols = st.columns(len(PERIOD_CONFIG))
                for i, tf in enumerate(PERIOD_CONFIG.keys()):
                    with tf_cols[i]:
                        if st.button(tf, key=f"tf_{bubble_id}_{tf}", use_container_width=True, disabled=(tf == bubble["timeframe"])):
                            bubble["timeframe"] = tf
                            clear_price_caches()
                            st.rerun()

            with col_menu:
                with st.expander("⚙️ Menu", expanded=False):
                    selected_ticker = st.selectbox("Stock ticker", all_tickers, index=all_tickers.index(bubble["ticker"]) if bubble["ticker"] in all_tickers else 0, key=f"ticker_{bubble_id}")
                    custom_ticker = st.text_input("Or type ticker", value="", key=f"custom_ticker_{bubble_id}")
                    show_ma = st.checkbox("Moving averages", value=bubble["show_ma"], key=f"ma_{bubble_id}")
                    show_volume = st.checkbox("Volume", value=bubble["show_volume"], key=f"volume_{bubble_id}")

                    if st.button("Apply / Refresh Ticker", key=f"apply_{bubble_id}", use_container_width=True):
                        final_ticker = custom_ticker.upper().strip() or selected_ticker.upper().strip()
                        ok, msg = validate_ticker(final_ticker)
                        if not ok:
                            st.error(msg)
                        else:
                            bubble.update({"ticker": final_ticker, "show_ma": show_ma, "show_volume": show_volume})
                            clear_price_caches()
                            st.rerun()

                    if st.button("Refresh This Bubble", key=f"refresh_{bubble_id}", use_container_width=True):
                        clear_price_caches()
                        st.rerun()

                    c1, c2 = st.columns([1.25, 1.0])
                    with c1:
                        if st.button("Duplicate", key=f"duplicate_{bubble_id}", use_container_width=True):
                            duplicate_bubble(bubble)
                    with c2:
                        if st.button("Remove", key=f"remove_{bubble_id}", use_container_width=True):
                            remove_bubble(bubble_id)

            st.plotly_chart(
                charts.build_price_chart(df.copy(), bubble, config, chart_height),
                use_container_width=True,
                key=f"chart_{bubble_id}_{bubble['ticker']}_{bubble['timeframe']}_{int(time.time() // PRICE_CACHE_TTL_SECONDS)}",
                config={"displayModeBar": "hover", "displaylogo": False},
            )

        st.markdown(
            f'<div style="font-size: 0.75rem; color: #94a3b8; text-align: right; margin-top: 8px;">Source: {connector} · Status: {status} · Quote TTL: {PRICE_CACHE_TTL_SECONDS}s · Updated: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>',
            unsafe_allow_html=True,
        )


def render_layout(bubbles: list[dict], all_tickers: list[str], chart_height: int) -> None:
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
    else:
        top, bottom = st.columns(2), st.columns(2)
        with top[0]:
            render_bubble(bubbles[0], all_tickers, chart_height)
        with top[1]:
            render_bubble(bubbles[1], all_tickers, chart_height)
        with bottom[0]:
            render_bubble(bubbles[2], all_tickers, chart_height)
        with bottom[1]:
            render_bubble(bubbles[3], all_tickers, chart_height)


profiles = load_profiles()
all_tickers = get_all_tickers(profiles)
if "bubbles" not in st.session_state:
    st.session_state.bubbles = [default_bubble(all_tickers[0])]

st.sidebar.title("Stock Profiles")
st.sidebar.caption(f"Version: {APP_VERSION}")
selected_profile = st.sidebar.selectbox("Select Profile", list(profiles.keys()))
if st.sidebar.button("Refresh All Prices"):
    clear_price_caches()
    st.rerun()

new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add To Profile"):
    ticker = new_ticker.upper().strip()
    if not ticker:
        st.sidebar.error("Ticker cannot be empty")
    elif ticker in profiles[selected_profile]:
        st.sidebar.warning(f"{ticker} already in profile")
    else:
        ok, msg = validate_ticker(ticker)
        if not ok:
            st.sidebar.error(msg)
        else:
            profiles[selected_profile].append(ticker)
            save_profiles(profiles)
            st.sidebar.success(f"Added {ticker}")
            st.rerun()

if st.sidebar.button("+ Add Bubble"):
    if len(st.session_state.bubbles) < MAX_BUBBLES:
        default_ticker = profiles[selected_profile][0] if profiles[selected_profile] else all_tickers[0]
        st.session_state.bubbles.append(default_bubble(default_ticker))
        st.rerun()
    else:
        st.sidebar.warning(f"Maximum of {MAX_BUBBLES} bubbles reached.")

st.sidebar.caption(f"Active bubbles: {len(st.session_state.bubbles)} / {MAX_BUBBLES}")
st.title("📈 Stock Dashboard")
st.caption("TradingView-style bubble dashboard · Each bubble is an independent chart instance")
height = 520 if len(st.session_state.bubbles) <= 2 else 430
render_layout(st.session_state.bubbles, all_tickers, height)

st.divider()
st.subheader("Data connection check")
with st.expander("Show diagnostics", expanded=False):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Price cache TTL: `{PRICE_CACHE_TTL_SECONDS} seconds`")
    st.write(f"Active bubbles: `{len(st.session_state.bubbles)}`")
    st.json(st.session_state.bubbles)
