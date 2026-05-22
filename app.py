import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

APP_VERSION = "v0.2.6-control-contrast"

st.set_page_config(page_title="Stock Dashboard", layout="wide")

PROFILE_PATH = Path("data/profiles.json")

PERIOD_CONFIG = {
    "1D": {"period": "1d", "interval": "5m", "show_ma": False, "rangebreaks": [dict(bounds=[16, 9.5], pattern="hour")]},
    "5D": {"period": "5d", "interval": "15m", "show_ma": False, "rangebreaks": [dict(bounds=["sat", "mon"]), dict(bounds=[16, 9.5], pattern="hour")]},
    "1M": {"period": "1mo", "interval": "1d", "show_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "6M": {"period": "6mo", "interval": "1d", "show_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "1Y": {"period": "1y", "interval": "1d", "show_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "5Y": {"period": "5y", "interval": "1wk", "show_ma": True, "rangebreaks": []},
    "MAX": {"period": "max", "interval": "1mo", "show_ma": True, "rangebreaks": []},
}

st.markdown(
    """
    <style>
    header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
    }
    #MainMenu, footer {
        visibility: hidden !important;
    }
    .stApp {
        background: #0b1220;
        color: #f8fafc;
    }
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #2563eb;
    }
    .block-container {
        padding-top: 1.0rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }
    h1, h2, h3, h4, p, label, span, div {
        color: #f8fafc;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: #dbeafe !important;
    }

    /* Inputs and select boxes: force dark readable text on white controls */
    input, textarea {
        color: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
    }
    input::placeholder, textarea::placeholder {
        color: #475569 !important;
        -webkit-text-fill-color: #475569 !important;
        opacity: 1 !important;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #ffffff !important;
        color: #020617 !important;
        border: 1px solid #cbd5e1 !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] svg,
    div[data-baseweb="select"] input {
        color: #020617 !important;
        fill: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
    }
    div[role="listbox"],
    div[role="option"],
    ul[role="listbox"],
    li[role="option"] {
        background-color: #ffffff !important;
        color: #020617 !important;
    }
    div[role="option"] span,
    li[role="option"] span {
        color: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
    }
    div[role="option"]:hover,
    li[role="option"]:hover {
        background-color: #dbeafe !important;
        color: #020617 !important;
    }

    /* Buttons: always readable */
    .stButton > button,
    button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        background-color: #ffffff !important;
        color: #020617 !important;
        border: 1px solid #93c5fd !important;
        font-weight: 800 !important;
    }
    .stButton > button p,
    .stButton > button span,
    button[kind="secondary"] p,
    button[kind="secondary"] span,
    button[data-testid="baseButton-secondary"] p,
    button[data-testid="baseButton-secondary"] span {
        color: #020617 !important;
    }
    .stButton > button:hover,
    button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #dbeafe !important;
        color: #020617 !important;
        border-color: #60a5fa !important;
    }

    /* Expanders: avoid white-on-white when opened */
    div[data-testid="stExpander"] {
        background-color: #111827 !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
    }
    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] summary {
        background-color: #111827 !important;
        color: #f8fafc !important;
    }
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span,
    div[data-testid="stExpander"] svg {
        color: #f8fafc !important;
        fill: #f8fafc !important;
    }
    div[data-testid="stExpander"] div,
    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] span {
        color: #f8fafc !important;
    }

    .version-pill {
        display: inline-block;
        background: #2563eb;
        color: #ffffff !important;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 800;
        margin-bottom: 0.75rem;
        letter-spacing: 0.02em;
    }
    .status-card {
        background: #111827;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 14px 16px;
        margin: 10px 0 16px 0;
        color: #f8fafc !important;
    }
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 12px;
    }
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }
    div[data-testid="stMetricLabel"] p {
        color: #93c5fd !important;
        font-weight: 700;
    }
    .stRadio label,
    .stSelectbox label,
    .stTextInput label {
        color: #bfdbfe !important;
        font-weight: 700;
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
    params = {"interval": interval, "range": range_value, "includePrePost": "false"}
    headers = {"User-Agent": "Mozilla/5.0"}

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
        chart_df["MA20"] = chart_df["Close"].rolling(window=20, min_periods=1).mean()
        chart_df["MA50"] = chart_df["Close"].rolling(window=50, min_periods=1).mean()
        chart_df["MA200"] = chart_df["Close"].rolling(window=200, min_periods=1).mean()

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
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA20"], mode="lines", name="20 MA", line=dict(color="#f97316", width=1.8)), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA50"], mode="lines", name="50 MA", line=dict(color="#14b8a6", width=1.8)), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], mode="lines", name="200 MA", line=dict(color="#8b5cf6", width=1.8)), row=1, col=1)

    volume_colors = ["#22c55e" if close >= open_ else "#ef4444" for close, open_ in zip(chart_df["Close"], chart_df["Open"])]
    fig.add_trace(
        go.Bar(
            x=chart_df.index,
            y=chart_df["Volume"],
            name="Volume",
            opacity=0.55,
            marker_color=volume_colors,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=dict(text=f"{selected_stock} • {selected_period}", font=dict(color="#f8fafc", size=20)),
        template="plotly_dark",
        height=760,
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font=dict(color="#e5e7eb", size=13),
        legend=dict(font=dict(color="#e5e7eb", size=12)),
        xaxis_rangeslider_visible=False,
        margin=dict(l=25, r=25, t=55, b=25),
        hovermode="x unified",
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#334155",
        tickfont=dict(color="#cbd5e1", size=12),
        title_font=dict(color="#bfdbfe"),
        rangebreaks=config["rangebreaks"],
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#334155",
        tickfont=dict(color="#cbd5e1", size=12),
        title_font=dict(color="#bfdbfe"),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
    chart_rendered = True

st.divider()
st.subheader("Data connection check")

with st.expander("Show diagnostics", expanded=False):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Connector used: `{connector_used}`")
    st.write(f"Ticker: `{selected_stock}`")
    st.write(f"Selected timeframe: `{selected_period}`")
    st.write(f"Data status: `{data_status}`")
    st.write(f"Rows returned: `{len(df)}`")
    st.write(f"Chart rendered: `{chart_rendered}`")
    if not df.empty:
        st.dataframe(df.tail(10), use_container_width=True)
