import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

APP_VERSION = "v0.2.2-layout-debug-bottom"

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


@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period: str, interval: str) -> tuple[pd.DataFrame, str]:
    """Return price data and a status message for debugging."""
    try:
        data = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception as exc:
        return pd.DataFrame(), f"yf.download exception: {exc}"

    if data.empty:
        # Fallback through Ticker.history sometimes succeeds when download returns empty.
        try:
            data = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        except Exception as exc:
            return pd.DataFrame(), f"yf.download empty; Ticker.history exception: {exc}"

    if data.empty:
        return pd.DataFrame(), "No rows returned by yfinance."

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required_columns = ["Open", "High", "Low", "Close"]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        return pd.DataFrame(), f"Missing expected yfinance columns: {missing_columns}. Raw columns: {list(data.columns)}"

    data = data.dropna(subset=required_columns)
    if data.empty:
        return pd.DataFrame(), "Rows existed but were removed after dropping blank OHLC values."

    return data, "OK"


profiles = load_profiles()

st.sidebar.title("Stock Profiles")
st.sidebar.caption(f"Version: {APP_VERSION}")

selected_profile = st.sidebar.selectbox("Select Profile", list(profiles.keys()))

with st.sidebar.expander("Create New Profile"):
    new_profile_name = st.text_input("Profile Name")
    if st.button("Create Profile"):
        clean_name = new_profile_name.strip()
        if clean_name and clean_name not in profiles:
            profiles[clean_name] = []
            save_profiles(profiles)
            st.success(f"Created {clean_name}. Refresh if it does not appear immediately.")

new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add To Profile"):
    ticker = new_ticker.upper().strip()
    if ticker and ticker not in profiles[selected_profile]:
        profiles[selected_profile].append(ticker)
        save_profiles(profiles)
        st.sidebar.success(f"Added {ticker}. Refresh if it does not appear immediately.")

if not profiles[selected_profile]:
    st.warning("This profile has no tickers yet. Add one from the sidebar.")
    st.stop()

selected_stock = st.sidebar.selectbox("Select Stock", profiles[selected_profile])
selected_period = st.sidebar.radio("Timeframe", list(PERIOD_CONFIG.keys()), index=4)
config = PERIOD_CONFIG[selected_period]

st.markdown(f'<span class="version-pill">{APP_VERSION}</span>', unsafe_allow_html=True)
st.title("Stock Dashboard")
st.caption("Python + Streamlit + yfinance MVP")

with st.spinner(f"Loading {selected_stock} market data..."):
    df, data_status = get_price_data(selected_stock, config["period"], config["interval"])

chart_rendered = False

if df.empty:
    st.markdown('<div class="status-card">Chart area reserved. No valid price data is available yet.</div>', unsafe_allow_html=True)
    st.error(
        f"No price data returned for {selected_stock}. Try 1Y/6M first. Intraday 1D can fail more often depending on Yahoo/yfinance availability."
    )
else:
    latest = df.iloc[-1]
    previous_close = df["Close"].iloc[-2] if len(df) > 1 else latest["Close"]
    price_change = latest["Close"] - previous_close
    price_change_pct = (price_change / previous_close) * 100 if previous_close else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ticker", selected_stock)
    col2.metric("Last Price", f"${latest['Close']:,.2f}", f"{price_change:+.2f} / {price_change_pct:+.2f}%")
    col3.metric("Volume", f"{latest.get('Volume', 0):,.0f}")
    col4.metric("Rows Loaded", f"{len(df):,}")

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
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA20"], mode="lines", name="20 MA", line=dict(width=1.6)), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA50"], mode="lines", name="50 MA", line=dict(width=1.6)), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], mode="lines", name="200 MA", line=dict(width=1.8)), row=1, col=1)

    volume_colors = ["#22c55e" if close >= open_ else "#ef4444" for close, open_ in zip(chart_df["Close"], chart_df["Open"])]
    fig.add_trace(
        go.Bar(
            x=chart_df.index,
            y=chart_df["Volume"],
            marker_color=volume_colors,
            name="Volume",
            opacity=0.55,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=f"{selected_stock} • {selected_period} Chart",
        template="plotly_dark",
        height=740,
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        margin=dict(l=20, r=20, t=55, b=25),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
    )

    fig.update_xaxes(showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
    chart_rendered = True

st.divider()
st.subheader("Data connection check")

with st.expander("Show diagnostics", expanded=True):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Ticker: `{selected_stock}`")
    st.write(f"Selected timeframe: `{selected_period}`")
    st.write(f"yfinance period: `{config['period']}`")
    st.write(f"yfinance interval: `{config['interval']}`")
    st.write(f"Data status: `{data_status}`")
    st.write(f"Rows returned: `{len(df)}`")
    st.write(f"Columns returned: `{list(df.columns) if not df.empty else []}`")
    st.write(f"Chart rendered: `{chart_rendered}`")
    if not df.empty:
        st.dataframe(df.tail(10), use_container_width=True)
