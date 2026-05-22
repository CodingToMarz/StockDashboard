import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

APP_VERSION = "v0.2.3-yahoo-fallback"

st.set_page_config(page_title="Stock Dashboard", layout="wide")

PROFILE_PATH = Path("data/profiles.json")

PERIOD_CONFIG = {
    "1D": {"period": "1d", "interval": "5m", "show_ma": False},
    "5D": {"period": "5d", "interval": "15m", "show_ma": False},
    "1M": {"period": "1mo", "interval": "1d", "show_ma": True},
    "6M": {"period": "6mo", "interval": "1d", "show_ma": True},
    "1Y": {"period": "1y", "interval": "1d", "show_ma": True},
    "5Y": {"period": "5y", "interval": "1wk", "show_ma": True},
    "MAX": {"period": "max", "interval": "1mo", "show_ma": True},
}

st.markdown(
    """
    <style>
    .stApp {
        background: #0b1220;
        color: #e5e7eb;
    }
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e40af;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }
    .version-pill {
        display: inline-block;
        background: #1d4ed8;
        color: #dbeafe;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }
    .status-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 14px 16px;
        margin: 10px 0 16px 0;
    }
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_profiles() -> dict:
    if not PROFILE_PATH.exists():
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        starter_profiles = {"AI Stocks": ["NVDA", "AMD", "MSFT"], "Space": ["RKLB", "LUNR"]}
        PROFILE_PATH.write_text(json.dumps(starter_profiles, indent=2))
    return json.loads(PROFILE_PATH.read_text())


def save_profiles(profiles: dict) -> None:
    PROFILE_PATH.write_text(json.dumps(profiles, indent=2))


def yahoo_direct_request(ticker: str, interval: str, range_value: str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

    params = {
        "interval": interval,
        "range": range_value,
        "includePrePost": "false",
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()

    result = data.get("chart", {}).get("result")
    if not result:
        return pd.DataFrame()

    result = result[0]

    timestamps = result.get("timestamp")
    quote = result.get("indicators", {}).get("quote", [{}])[0]

    if not timestamps:
        return pd.DataFrame()

    df = pd.DataFrame({
        "Open": quote.get("open", []),
        "High": quote.get("high", []),
        "Low": quote.get("low", []),
        "Close": quote.get("close", []),
        "Volume": quote.get("volume", []),
    })

    df.index = pd.to_datetime(timestamps, unit="s")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])

    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period: str, interval: str):
    connector_used = "yfinance"

    try:
        data = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception:
        data = pd.DataFrame()

    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data = data.dropna(subset=["Open", "High", "Low", "Close"])

    if data.empty:
        connector_used = "Yahoo Direct API"

        try:
            data = yahoo_direct_request(ticker, interval, period)
        except Exception as exc:
            return pd.DataFrame(), f"All connectors failed: {exc}", connector_used

    if data.empty:
        return pd.DataFrame(), "No rows returned by either connector.", connector_used

    return data, "OK", connector_used


profiles = load_profiles()

st.sidebar.title("Stock Profiles")
st.sidebar.caption(f"Version: {APP_VERSION}")

selected_profile = st.sidebar.selectbox("Select Profile", list(profiles.keys()))

new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add To Profile"):
    ticker = new_ticker.upper().strip()
    if ticker and ticker not in profiles[selected_profile]:
        profiles[selected_profile].append(ticker)
        save_profiles(profiles)
        st.sidebar.success(f"Added {ticker}")

selected_stock = st.sidebar.selectbox("Select Stock", profiles[selected_profile])
selected_period = st.sidebar.radio("Timeframe", list(PERIOD_CONFIG.keys()), index=4)
config = PERIOD_CONFIG[selected_period]

st.markdown(f'<span class="version-pill">{APP_VERSION}</span>', unsafe_allow_html=True)
st.title("Stock Dashboard")

with st.spinner(f"Loading {selected_stock} market data..."):
    df, data_status, connector_used = get_price_data(selected_stock, config["period"], config["interval"])

chart_rendered = False

if df.empty:
    st.markdown('<div class="status-card">Chart area reserved. No valid price data is available yet.</div>', unsafe_allow_html=True)
    st.error(f"No price data returned for {selected_stock}")
else:
    latest = df.iloc[-1]

    col1, col2, col3 = st.columns(3)
    col1.metric("Ticker", selected_stock)
    col2.metric("Last Price", f"${latest['Close']:,.2f}")
    col3.metric("Rows Loaded", f"{len(df):,}")

    chart_df = df.copy()

    if config["show_ma"]:
        chart_df["MA20"] = chart_df["Close"].rolling(window=20).mean()
        chart_df["MA50"] = chart_df["Close"].rolling(window=50).mean()
        chart_df["MA200"] = chart_df["Close"].rolling(window=200).mean()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.74, 0.26],
    )

    fig.add_trace(
        go.Candlestick(
            x=chart_df.index,
            open=chart_df["Open"],
            high=chart_df["High"],
            low=chart_df["Low"],
            close=chart_df["Close"],
            name="Price",
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
        ),
        row=1,
        col=1,
    )

    if config["show_ma"]:
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA20"], mode="lines", name="20 MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA50"], mode="lines", name="50 MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], mode="lines", name="200 MA"), row=1, col=1)

    fig.add_trace(
        go.Bar(
            x=chart_df.index,
            y=chart_df["Volume"],
            name="Volume",
            opacity=0.45,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        height=760,
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        xaxis_rangeslider_visible=False,
    )

    st.plotly_chart(fig, use_container_width=True)
    chart_rendered = True

st.divider()
st.subheader("Data connection check")

with st.expander("Show diagnostics", expanded=True):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Connector used: `{connector_used}`")
    st.write(f"Ticker: `{selected_stock}`")
    st.write(f"Selected timeframe: `{selected_period}`")
    st.write(f"Data status: `{data_status}`")
    st.write(f"Rows returned: `{len(df)}`")
    st.write(f"Chart rendered: `{chart_rendered}`")

    if not df.empty:
        st.dataframe(df.tail(10), use_container_width=True)
