import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

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
        background: linear-gradient(180deg, #0b0f19 0%, #111827 100%);
        color: #e5e7eb;
    }
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #f8fafc;
    }
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 14px;
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
def get_price_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    data = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data.empty:
        return data

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    return data


profiles = load_profiles()

st.sidebar.title("Stock Profiles")

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
selected_period = st.sidebar.radio("Timeframe", list(PERIOD_CONFIG.keys()), index=4, horizontal=False)
config = PERIOD_CONFIG[selected_period]

st.title("Stock Dashboard")
st.caption("Python + Streamlit + yfinance MVP")

with st.spinner(f"Loading {selected_stock} market data..."):
    df = get_price_data(selected_stock, config["period"], config["interval"])

if df.empty:
    st.error(
        f"No price data returned for {selected_stock}. This usually means yfinance could not reach Yahoo Finance, "
        "the ticker is invalid, or the selected interval is temporarily unavailable."
    )
    st.info("Try refreshing the app, choosing another timeframe, or testing a very common ticker like AAPL/MSFT/NVDA.")
    st.stop()

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
    height=760,
    paper_bgcolor="#0b0f19",
    plot_bgcolor="#0b0f19",
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

with st.expander("Data connection check"):
    st.write(f"Ticker: `{selected_stock}`")
    st.write(f"yfinance period: `{config['period']}`")
    st.write(f"yfinance interval: `{config['interval']}`")
    st.write(f"Rows returned: `{len(df)}`")
    st.dataframe(df.tail(10), use_container_width=True)
