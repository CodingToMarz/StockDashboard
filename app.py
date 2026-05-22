import json
import time
import uuid
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

APP_VERSION = "v0.3.1-dropdown-contrast-fix"
MAX_BUBBLES = 4

# Future bubble roadmap reminder:
# - Technical Analysis
# - Company Fundamentals
# - News
# - Sector News
# - Earnings / Cash Flow
# - AI Summary
# Future menu actions:
# - Compare against another ticker
# - Open related news
# - Open technical analysis
# - Open fundamentals

st.set_page_config(page_title="Stock Dashboard", layout="wide")

PROFILE_PATH = Path("data/profiles.json")

PERIOD_CONFIG = {
    "1D": {"period": "1d", "interval": "5m", "allow_ma": False, "rangebreaks": [dict(bounds=[16, 9.5], pattern="hour")]},
    "5D": {"period": "5d", "interval": "15m", "allow_ma": False, "rangebreaks": [dict(bounds=["sat", "mon"]), dict(bounds=[16, 9.5], pattern="hour")]},
    "1M": {"period": "1mo", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "6M": {"period": "6mo", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "1Y": {"period": "1y", "interval": "1d", "allow_ma": True, "rangebreaks": [dict(bounds=["sat", "mon"])]},
    "5Y": {"period": "5y", "interval": "1wk", "allow_ma": True, "rangebreaks": []},
    "MAX": {"period": "max", "interval": "1mo", "allow_ma": True, "rangebreaks": []},
}

BUBBLE_TYPES = ["Price Chart"]

st.markdown(
    """
    <style>
    header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
    }
    #MainMenu, footer { visibility: hidden !important; }
    .stApp { background: #0b1220; color: #f8fafc; }
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #2563eb;
    }
    .block-container {
        padding-top: 1.0rem;
        padding-bottom: 2.5rem;
        max-width: 1720px;
    }
    h1, h2, h3, h4, p, label, span, div { color: #f8fafc; }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div { color: #dbeafe !important; }

    /* HARDENED FORM CONTROL CONTRAST */
    input, textarea,
    input *, textarea * {
        color: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
        caret-color: #020617 !important;
    }
    input::placeholder, textarea::placeholder {
        color: #475569 !important;
        -webkit-text-fill-color: #475569 !important;
        opacity: 1 !important;
    }

    /* Select/input containers */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #ffffff !important;
        color: #020617 !important;
        border: 1px solid #cbd5e1 !important;
    }

    /* Everything inside select controls, including sidebar + bubble menus */
    div[data-baseweb="select"],
    div[data-baseweb="select"] *,
    div[data-baseweb="input"],
    div[data-baseweb="input"] *,
    div[data-baseweb="textarea"],
    div[data-baseweb="textarea"] * {
        color: #020617 !important;
        fill: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
    }

    /* BaseWeb popover/dropdown menus render outside the local widget tree */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"],
    div[data-baseweb="menu"] *,
    div[data-baseweb="select-dropdown"],
    div[data-baseweb="select-dropdown"] *,
    ul[role="listbox"],
    ul[role="listbox"] *,
    div[role="listbox"],
    div[role="listbox"] *,
    li[role="option"],
    li[role="option"] *,
    div[role="option"],
    div[role="option"] * {
        background-color: #ffffff !important;
        color: #020617 !important;
        fill: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
        opacity: 1 !important;
    }
    li[role="option"]:hover,
    div[role="option"]:hover,
    li[aria-selected="true"],
    div[aria-selected="true"] {
        background-color: #dbeafe !important;
        color: #020617 !important;
        -webkit-text-fill-color: #020617 !important;
    }

    /* Disabled-looking BaseWeb text still needs to be readable */
    [aria-disabled="true"],
    [aria-disabled="true"] *,
    div[data-disabled="true"],
    div[data-disabled="true"] * {
        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;
        opacity: 1 !important;
    }

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
    button[data-testid="baseButton-secondary"] span { color: #020617 !important; }
    .stButton > button:hover,
    button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #dbeafe !important;
        color: #020617 !important;
        border-color: #60a5fa !important;
    }

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
    div[data-testid="stExpander"] summary svg {
        color: #f8fafc !important;
        fill: #f8fafc !important;
    }
    div[data-testid="stExpander"] div,
    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] span { color: #f8fafc !important; }

    .bubble-shell {
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.98), rgba(15, 23, 42, 0.98));
        border: 1px solid #334155;
        border-radius: 24px;
        box-shadow: 0 18px 36px rgba(0,0,0,0.28);
        padding: 16px 18px 12px 18px;
        margin-bottom: 18px;
        overflow: hidden;
    }
    .bubble-title {
        font-size: 1.05rem;
        font-weight: 900;
        color: #f8fafc !important;
        letter-spacing: 0.01em;
        margin-bottom: 4px;
    }
    .bubble-subtitle {
        font-size: 0.78rem;
        color: #93c5fd !important;
        margin-bottom: 10px;
    }
    .bubble-footer {
        font-size: 0.75rem;
        color: #94a3b8 !important;
        border-top: 1px solid #1f2937;
        margin-top: 8px;
        padding-top: 8px;
    }
    div[data-testid="stMetric"] {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 10px;
    }
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricValue"] { color: #f8fafc !important; }
    div[data-testid="stMetricLabel"] p {
        color: #93c5fd !important;
        font-weight: 700;
    }
    .stRadio label, .stSelectbox label, .stTextInput label, .stCheckbox label {
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


def get_all_tickers(profiles: dict) -> list[str]:
    tickers = []
    for items in profiles.values():
        tickers.extend(items)
    return sorted(set(tickers)) or ["NVDA"]


def default_bubble(ticker: str = "NVDA") -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "ticker": ticker,
        "timeframe": "6M",
        "bubble_type": "Price Chart",
        "show_ma": True,
        "show_volume": True,
    }


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


def build_price_chart(chart_df: pd.DataFrame, bubble: dict, config: dict, chart_height: int):
    rows = 2 if bubble["show_volume"] else 1
    row_heights = [0.74, 0.26] if bubble["show_volume"] else [1]

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
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

    if bubble["show_ma"] and config["allow_ma"]:
        chart_df["MA20"] = chart_df["Close"].rolling(window=20, min_periods=1).mean()
        chart_df["MA50"] = chart_df["Close"].rolling(window=50, min_periods=1).mean()
        chart_df["MA200"] = chart_df["Close"].rolling(window=200, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA20"], mode="lines", name="20 MA", line=dict(color="#f97316", width=1.8)), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA50"], mode="lines", name="50 MA", line=dict(color="#14b8a6", width=1.8)), row=1, col=1)
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["MA200"], mode="lines", name="200 MA", line=dict(color="#8b5cf6", width=1.8)), row=1, col=1)

    if bubble["show_volume"]:
        volume_colors = ["#22c55e" if close >= open_ else "#ef4444" for close, open_ in zip(chart_df["Close"], chart_df["Open"])]
        fig.add_trace(
            go.Bar(x=chart_df.index, y=chart_df["Volume"], name="Volume", opacity=0.55, marker_color=volume_colors),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Volume", row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=chart_height,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb", size=12),
        legend=dict(font=dict(color="#e5e7eb", size=11), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        margin=dict(l=18, r=18, t=18, b=18),
        hovermode="x unified",
    )

    fig.update_xaxes(showgrid=True, gridcolor="#334155", tickfont=dict(color="#cbd5e1", size=11), rangebreaks=config["rangebreaks"])
    fig.update_yaxes(showgrid=True, gridcolor="#334155", tickfont=dict(color="#cbd5e1", size=11))
    fig.update_yaxes(title_text="Price", row=1, col=1)

    return fig


def render_bubble(bubble: dict, all_tickers: list[str], chart_height: int):
    bubble_id = bubble["id"]
    config = PERIOD_CONFIG[bubble["timeframe"]]

    st.markdown('<div class="bubble-shell">', unsafe_allow_html=True)

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
                key=f"ticker_{bubble_id}",
            )
            custom_ticker = st.text_input("Or type ticker", value="", key=f"custom_ticker_{bubble_id}")
            selected_timeframe = st.selectbox(
                "Timeframe",
                list(PERIOD_CONFIG.keys()),
                index=list(PERIOD_CONFIG.keys()).index(bubble["timeframe"]),
                key=f"timeframe_{bubble_id}",
            )
            selected_type = st.selectbox(
                "Bubble type",
                BUBBLE_TYPES,
                index=0,
                key=f"type_{bubble_id}",
            )
            show_ma = st.checkbox("Moving averages", value=bubble["show_ma"], key=f"ma_{bubble_id}")
            show_volume = st.checkbox("Volume", value=bubble["show_volume"], key=f"volume_{bubble_id}")

            if st.button("Apply", key=f"apply_{bubble_id}"):
                ticker_value = custom_ticker.upper().strip() or selected_ticker
                bubble["ticker"] = ticker_value
                bubble["timeframe"] = selected_timeframe
                bubble["bubble_type"] = selected_type
                bubble["show_ma"] = show_ma
                bubble["show_volume"] = show_volume
                st.rerun()

            action_col_1, action_col_2 = st.columns(2)
            with action_col_1:
                if st.button("Duplicate", key=f"duplicate_{bubble_id}"):
                    if len(st.session_state.bubbles) < MAX_BUBBLES:
                        new_bubble = bubble.copy()
                        new_bubble["id"] = str(uuid.uuid4())[:8]
                        st.session_state.bubbles.append(new_bubble)
                        st.rerun()
                    else:
                        st.warning("Maximum of 4 bubbles reached.")
            with action_col_2:
                if st.button("Remove", key=f"remove_{bubble_id}"):
                    if len(st.session_state.bubbles) > 1:
                        st.session_state.bubbles = [b for b in st.session_state.bubbles if b["id"] != bubble_id]
                        st.rerun()
                    else:
                        st.warning("Keep at least one bubble.")

    with st.spinner(f"Loading {bubble['ticker']}..."):
        df, data_status, connector_used = get_price_data(bubble["ticker"], config["period"], config["interval"])

    if df.empty:
        st.markdown('<div class="status-card">No valid price data available for this bubble.</div>', unsafe_allow_html=True)
    else:
        latest = df.iloc[-1]
        metric_cols = st.columns(3)
        metric_cols[0].metric("Ticker", bubble["ticker"])
        metric_cols[1].metric("Last Price", f"${latest['Close']:,.2f}")
        metric_cols[2].metric("Rows", f"{len(df):,}")

        fig = build_price_chart(df.copy(), bubble, config, chart_height)
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{bubble_id}")

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(
        f'<div class="bubble-footer">Source: {connector_used} · Status: {data_status} · Updated: {timestamp}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


profiles = load_profiles()
all_tickers = get_all_tickers(profiles)

if "bubbles" not in st.session_state:
    st.session_state.bubbles = [default_bubble(all_tickers[0])]

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
        st.rerun()

if st.sidebar.button("+ Add Bubble"):
    if len(st.session_state.bubbles) < MAX_BUBBLES:
        default_ticker = profiles[selected_profile][0] if profiles[selected_profile] else all_tickers[0]
        st.session_state.bubbles.append(default_bubble(default_ticker))
        st.rerun()
    else:
        st.sidebar.warning("Maximum of 4 bubbles reached.")

st.sidebar.caption(f"Active bubbles: {len(st.session_state.bubbles)} / {MAX_BUBBLES}")

st.title("Stock Dashboard")
st.caption("Bubble-based dashboard layout · each bubble is an independent chart instance")

bubble_count = len(st.session_state.bubbles)
chart_height = 520 if bubble_count <= 2 else 430

if bubble_count == 1:
    render_bubble(st.session_state.bubbles[0], all_tickers, chart_height)
elif bubble_count == 2:
    cols = st.columns(2)
    for index, bubble in enumerate(st.session_state.bubbles):
        with cols[index]:
            render_bubble(bubble, all_tickers, chart_height)
elif bubble_count == 3:
    top_cols = st.columns(2)
    with top_cols[0]:
        render_bubble(st.session_state.bubbles[0], all_tickers, chart_height)
    with top_cols[1]:
        render_bubble(st.session_state.bubbles[1], all_tickers, chart_height)
    render_bubble(st.session_state.bubbles[2], all_tickers, chart_height)
else:
    top_cols = st.columns(2)
    bottom_cols = st.columns(2)
    with top_cols[0]:
        render_bubble(st.session_state.bubbles[0], all_tickers, chart_height)
    with top_cols[1]:
        render_bubble(st.session_state.bubbles[1], all_tickers, chart_height)
    with bottom_cols[0]:
        render_bubble(st.session_state.bubbles[2], all_tickers, chart_height)
    with bottom_cols[1]:
        render_bubble(st.session_state.bubbles[3], all_tickers, chart_height)

st.divider()
st.subheader("Data connection check")
with st.expander("Show diagnostics", expanded=False):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Active bubbles: `{len(st.session_state.bubbles)}`")
    st.write(st.session_state.bubbles)
