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

APP_VERSION = "v0.3.11-active-bubble-daily-change"
MAX_BUBBLES = 4
PROFILE_PATH = Path("data/profiles.json")
BUBBLE_TYPES = ["Price Chart"]
CHANGE_MODES = ["percent", "dollars", "market_cap"]

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

st.markdown("""
<style>
.stApp{background:#0b1220;color:#f8fafc}header[data-testid="stHeader"]{background:rgba(11,18,32,.86)!important;backdrop-filter:blur(8px)}.block-container{padding-top:2.4rem;max-width:1720px}h1,h2,h3,h4,p,label,span,div{color:#f8fafc}section[data-testid="stSidebar"]{background:#0f172a;border-right:2px solid #bfdbfe}section[data-testid="stSidebar"] *{color:#dbeafe!important}
header[data-testid="stHeader"] button,button[title*="sidebar"],button[aria-label*="sidebar"]{background:#60a5fa!important;border:2px solid #f8fafc!important;border-radius:12px!important;color:#fff!important;fill:#fff!important;box-shadow:0 0 14px rgba(96,165,250,.65)!important;opacity:1!important}

/* Simple, reliable bubble border. Active bubble gets stronger contrast via :has marker. */
div[data-testid="stVerticalBlockBorderWrapper"]{border:4px solid rgba(241,245,249,.82)!important;border-radius:24px!important;background:#0f172a!important;padding:16px 18px!important;margin-bottom:24px!important;box-shadow:0 10px 28px rgba(0,0,0,.34),0 0 0 1px rgba(255,255,255,.18)!important;overflow:hidden!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(#active-bubble-marker){border:6px solid #f8fafc!important;box-shadow:0 12px 32px rgba(0,0,0,.42),0 0 0 2px rgba(96,165,250,.62),0 0 24px rgba(147,197,253,.60)!important;background:#111827!important}

/* Readable controls without broad leakage. */
div[data-testid="stButton"] button,div[data-testid="stButton"] button *{color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap!important;text-shadow:none!important}div[data-testid="stButton"] button{background:#fff!important;border:1px solid #60a5fa!important;border-radius:10px!important;font-weight:800!important;min-height:38px!important}div[data-testid="stButton"] button:hover{background:#dbeafe!important;border-color:#2563eb!important}div[data-testid="stButton"] button:disabled,div[data-testid="stButton"] button:disabled *{background:#e2e8f0!important;color:#334155!important;-webkit-text-fill-color:#334155!important;opacity:1!important}
input,textarea,input *,textarea *{color:#020617!important;-webkit-text-fill-color:#020617!important;caret-color:#020617!important}input::placeholder,textarea::placeholder{color:#475569!important;opacity:1!important}div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,div[data-baseweb="textarea"]>div{background:#fff!important;color:#020617!important;border:1px solid #cbd5e1!important}div[data-baseweb="select"],div[data-baseweb="select"] *,div[data-baseweb="input"],div[data-baseweb="input"] *,div[data-baseweb="textarea"],div[data-baseweb="textarea"] *{color:#020617!important;fill:#020617!important;-webkit-text-fill-color:#020617!important}div[data-baseweb="popover"],div[data-baseweb="popover"] *,div[data-baseweb="menu"],div[data-baseweb="menu"] *,ul[role="listbox"],ul[role="listbox"] *,div[role="option"],div[role="option"] *,li[role="option"],li[role="option"] *{background:#fff!important;color:#020617!important;-webkit-text-fill-color:#020617!important;opacity:1!important}div[role="option"]:hover,li[role="option"]:hover{background:#dbeafe!important}
div[data-testid="stCheckbox"] label,div[data-testid="stCheckbox"] label *{color:#bfdbfe!important;font-weight:700!important}div[data-testid="stCheckbox"] input[type="checkbox"]{accent-color:#60a5fa!important}div[data-testid="stCheckbox"] [data-baseweb="checkbox"]>div:first-child{border:2px solid #93c5fd!important;background:#0f172a!important}div[data-testid="stCheckbox"] [aria-checked="true"]>div:first-child,div[data-testid="stCheckbox"] [data-checked="true"]>div:first-child{background:#60a5fa!important;border-color:#dbeafe!important}div[data-testid="stCheckbox"] svg{color:#020617!important;fill:#020617!important;stroke:#020617!important}
div[data-testid="stExpander"]{background:#111827!important;border:1px solid #64748b!important;border-radius:14px!important}div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary *,div[data-testid="stExpander"] details,div[data-testid="stExpander"] p,div[data-testid="stExpander"] span{background:transparent!important;color:#f8fafc!important;fill:#f8fafc!important}code,pre,code *,pre *{background:#0f172a!important;color:#86efac!important;-webkit-text-fill-color:#86efac!important;text-shadow:none!important}
.bubble-title{font-size:1.05rem;font-weight:900;color:#f8fafc!important;margin-bottom:4px}.bubble-subtitle{font-size:.78rem;color:#93c5fd!important;margin-bottom:10px}.bubble-footer{font-size:.75rem;color:#bfdbfe!important;border-top:1px solid rgba(191,219,254,.34);margin-top:8px;padding-top:8px}div[data-testid="stMetric"]{background:#111827;border:1px solid #94a3b8;border-radius:16px;padding:10px}div[data-testid="stMetricLabel"] p{color:#93c5fd!important;font-weight:700}div[data-testid="stMetricValue"]{color:#f8fafc!important}.stRadio label,.stSelectbox label,.stTextInput label{color:#bfdbfe!important;font-weight:700}
</style>
""", unsafe_allow_html=True)


def load_profiles() -> dict:
    if not PROFILE_PATH.exists():
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps({"AI Stocks": ["NVDA", "AMD", "MSFT"], "Space": ["RKLB", "LUNR"]}, indent=2))
    return json.loads(PROFILE_PATH.read_text())


def save_profiles(profiles: dict) -> None:
    PROFILE_PATH.write_text(json.dumps(profiles, indent=2))


def get_all_tickers(profiles: dict) -> list[str]:
    return sorted({ticker for group in profiles.values() for ticker in group}) or ["NVDA"]


def default_bubble(ticker: str = "NVDA") -> dict:
    return {"id": str(uuid.uuid4())[:8], "ticker": ticker, "timeframe": "6M", "bubble_type": "Price Chart", "show_ma": True, "show_volume": True, "change_mode": "percent"}


def cycle_change_mode(mode: str) -> str:
    return CHANGE_MODES[(CHANGE_MODES.index(mode) + 1) % len(CHANGE_MODES)] if mode in CHANGE_MODES else "percent"


def format_large_money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    sign = "+" if value >= 0 else "-"
    value = abs(value)
    if value >= 1_000_000_000_000:
        return f"{sign}${value/1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000:
        return f"{sign}${value/1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{sign}${value/1_000_000:.2f}M"
    return f"{sign}${value:,.0f}"


@st.cache_data(ttl=1800, show_spinner=False)
def get_market_cap(ticker: str) -> float | None:
    try:
        fast_info = yf.Ticker(ticker).fast_info
        return fast_info.get("market_cap") if fast_info else None
    except Exception:
        return None


def yahoo_direct_request(ticker: str, interval: str, range_value: str) -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    response = requests.get(url, params={"interval": interval, "range": range_value, "includePrePost": "false"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
    df = pd.DataFrame({"Open": quote.get("open", []), "High": quote.get("high", []), "Low": quote.get("low", []), "Close": quote.get("close", []), "Volume": quote.get("volume", [])})
    df.index = pd.to_datetime(timestamps, unit="s")
    return df.dropna(subset=["Open", "High", "Low", "Close"])


@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period: str, interval: str):
    connector = "yfinance"
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    except Exception:
        data = pd.DataFrame()
    if not data.empty:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.dropna(subset=["Open", "High", "Low", "Close"])
    if data.empty:
        connector = "Yahoo Direct API"
        try:
            data = yahoo_direct_request(ticker, interval, period)
        except Exception as exc:
            return pd.DataFrame(), f"All connectors failed: {exc}", connector
    if data.empty:
        return pd.DataFrame(), "No rows returned by either connector.", connector
    return data, "OK", connector


def build_price_chart(df: pd.DataFrame, bubble: dict, config: dict, chart_height: int):
    rows = 2 if bubble["show_volume"] else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.74, 0.26] if rows == 2 else [1])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price", increasing_line_color="#22c55e", decreasing_line_color="#ef4444"), row=1, col=1)
    if bubble["show_ma"] and config["allow_ma"]:
        for label, window, color in [("20 MA", 20, "#f97316"), ("50 MA", 50, "#14b8a6"), ("200 MA", 200, "#8b5cf6")]:
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"].rolling(window=window, min_periods=1).mean(), mode="lines", name=label, line=dict(color=color, width=1.8)), row=1, col=1)
    if bubble["show_volume"]:
        colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", opacity=0.55, marker_color=colors), row=2, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_layout(template="plotly_dark", height=chart_height, paper_bgcolor="rgba(17,24,39,0)", plot_bgcolor="rgba(17,24,39,.78)", font=dict(color="#e5e7eb", size=12), legend=dict(font=dict(color="#e5e7eb", size=11), orientation="h", yanchor="bottom", y=1.08, xanchor="left", x=0), xaxis_rangeslider_visible=False, margin=dict(l=18, r=18, t=40, b=18), hovermode="x unified")
    fig.update_xaxes(showgrid=True, gridcolor="#334155", tickfont=dict(color="#cbd5e1", size=11), rangebreaks=config["rangebreaks"])
    fig.update_yaxes(showgrid=True, gridcolor="#334155", tickfont=dict(color="#cbd5e1", size=11))
    fig.update_yaxes(title_text="Price", row=1, col=1)
    return fig


def render_change_button(bubble: dict, df: pd.DataFrame, bubble_id: str):
    close = df["Close"].dropna()
    if len(close) < 2:
        label = "Daily Change: N/A"
    else:
        current, previous = float(close.iloc[-1]), float(close.iloc[-2])
        dollar_change = current - previous
        pct_change = (dollar_change / previous) * 100 if previous else 0
        mode = bubble.get("change_mode", "percent")
        if mode == "dollars":
            label = f"Daily $: {dollar_change:+.2f}"
        elif mode == "market_cap":
            market_cap = get_market_cap(bubble["ticker"])
            estimated_move = market_cap * (pct_change / 100) if market_cap else None
            label = f"Mkt Cap Est: {format_large_money(estimated_move)}"
        else:
            label = f"Daily %: {pct_change:+.2f}%"
    if st.button(label, key=f"change_metric_{bubble_id}", use_container_width=True):
        bubble["change_mode"] = cycle_change_mode(bubble.get("change_mode", "percent"))
        st.session_state.active_bubble_id = bubble_id
        st.rerun()


def render_bubble(bubble: dict, all_tickers: list[str], chart_height: int):
    bubble_id = bubble["id"]
    bubble.setdefault("change_mode", "percent")
    config = PERIOD_CONFIG[bubble["timeframe"]]
    with st.container(border=True):
        if st.session_state.get("active_bubble_id") == bubble_id:
            st.markdown('<span id="active-bubble-marker"></span>', unsafe_allow_html=True)
        title_col, menu_col = st.columns([0.68, 0.32], vertical_alignment="top")
        with title_col:
            active_label = " · ACTIVE" if st.session_state.get("active_bubble_id") == bubble_id else ""
            st.markdown(f'<div class="bubble-title">{bubble["ticker"]} • {bubble["bubble_type"]}{active_label}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bubble-subtitle">{bubble["timeframe"]} · independent dashboard bubble</div>', unsafe_allow_html=True)
        with menu_col:
            with st.expander("Menu", expanded=False):
                if st.button("Set Active", key=f"active_{bubble_id}", use_container_width=True):
                    st.session_state.active_bubble_id = bubble_id
                    st.rerun()
                selected_ticker = st.selectbox("Stock ticker", all_tickers, index=all_tickers.index(bubble["ticker"]) if bubble["ticker"] in all_tickers else 0, key=f"ticker_{bubble_id}")
                custom_ticker = st.text_input("Or type ticker", value="", key=f"custom_ticker_{bubble_id}")
                selected_timeframe = st.selectbox("Timeframe", list(PERIOD_CONFIG.keys()), index=list(PERIOD_CONFIG.keys()).index(bubble["timeframe"]), key=f"timeframe_{bubble_id}")
                selected_type = st.selectbox("Bubble type", BUBBLE_TYPES, index=0, key=f"type_{bubble_id}")
                show_ma = st.checkbox("Moving averages", value=bubble["show_ma"], key=f"ma_{bubble_id}")
                show_volume = st.checkbox("Volume", value=bubble["show_volume"], key=f"volume_{bubble_id}")
                if st.button("Apply", key=f"apply_{bubble_id}", use_container_width=True):
                    bubble.update({"ticker": custom_ticker.upper().strip() or selected_ticker, "timeframe": selected_timeframe, "bubble_type": selected_type, "show_ma": show_ma, "show_volume": show_volume})
                    st.session_state.active_bubble_id = bubble_id
                    st.rerun()
                c1, c2 = st.columns([1.25, 1.0])
                with c1:
                    if st.button("Duplicate", key=f"duplicate_{bubble_id}", use_container_width=True):
                        if len(st.session_state.bubbles) < MAX_BUBBLES:
                            new_bubble = bubble.copy(); new_bubble["id"] = str(uuid.uuid4())[:8]
                            st.session_state.bubbles.append(new_bubble)
                            st.session_state.active_bubble_id = new_bubble["id"]
                            st.rerun()
                        else:
                            st.warning("Maximum of 4 bubbles reached.")
                with c2:
                    if st.button("Remove", key=f"remove_{bubble_id}", use_container_width=True):
                        if len(st.session_state.bubbles) > 1:
                            st.session_state.bubbles = [b for b in st.session_state.bubbles if b["id"] != bubble_id]
                            st.session_state.active_bubble_id = st.session_state.bubbles[0]["id"]
                            st.rerun()
                        else:
                            st.warning("Keep at least one bubble.")
        with st.spinner(f"Loading {bubble['ticker']}..."):
            df, status, connector = get_price_data(bubble["ticker"], config["period"], config["interval"])
        if df.empty:
            st.warning("No valid price data available for this bubble.")
        else:
            latest = df.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Ticker", bubble["ticker"])
            m2.metric("Last Price", f"${latest['Close']:,.2f}")
            with m3:
                render_change_button(bubble, df, bubble_id)
            st.plotly_chart(build_price_chart(df.copy(), bubble, config, chart_height), use_container_width=True, key=f"chart_{bubble_id}", config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
        st.markdown(f'<div class="bubble-footer">Source: {connector} · Status: {status} · Updated: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)


profiles = load_profiles()
all_tickers = get_all_tickers(profiles)
if "bubbles" not in st.session_state:
    st.session_state.bubbles = [default_bubble(all_tickers[0])]
if "active_bubble_id" not in st.session_state:
    st.session_state.active_bubble_id = st.session_state.bubbles[0]["id"]

st.sidebar.title("Stock Profiles")
st.sidebar.caption(f"Version: {APP_VERSION}")
selected_profile = st.sidebar.selectbox("Select Profile", list(profiles.keys()))
new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add To Profile"):
    ticker = new_ticker.upper().strip()
    if ticker and ticker not in profiles[selected_profile]:
        profiles[selected_profile].append(ticker); save_profiles(profiles); st.sidebar.success(f"Added {ticker}"); st.rerun()
if st.sidebar.button("+ Add Bubble"):
    if len(st.session_state.bubbles) < MAX_BUBBLES:
        new_bubble = default_bubble(profiles[selected_profile][0] if profiles[selected_profile] else all_tickers[0])
        st.session_state.bubbles.append(new_bubble)
        st.session_state.active_bubble_id = new_bubble["id"]
        st.rerun()
    else:
        st.sidebar.warning("Maximum of 4 bubbles reached.")
st.sidebar.caption(f"Active bubbles: {len(st.session_state.bubbles)} / {MAX_BUBBLES}")

st.title("Stock Dashboard")
st.caption("Bubble-based dashboard layout · each bubble is an independent chart instance")

count = len(st.session_state.bubbles)
height = 520 if count <= 2 else 430
if count == 1:
    render_bubble(st.session_state.bubbles[0], all_tickers, height)
elif count == 2:
    cols = st.columns(2)
    for i, bubble in enumerate(st.session_state.bubbles):
        with cols[i]: render_bubble(bubble, all_tickers, height)
elif count == 3:
    top = st.columns(2)
    with top[0]: render_bubble(st.session_state.bubbles[0], all_tickers, height)
    with top[1]: render_bubble(st.session_state.bubbles[1], all_tickers, height)
    render_bubble(st.session_state.bubbles[2], all_tickers, height)
else:
    top, bottom = st.columns(2), st.columns(2)
    with top[0]: render_bubble(st.session_state.bubbles[0], all_tickers, height)
    with top[1]: render_bubble(st.session_state.bubbles[1], all_tickers, height)
    with bottom[0]: render_bubble(st.session_state.bubbles[2], all_tickers, height)
    with bottom[1]: render_bubble(st.session_state.bubbles[3], all_tickers, height)

st.divider()
st.subheader("Data connection check")
with st.expander("Show diagnostics", expanded=False):
    st.write(f"App version: `{APP_VERSION}`")
    st.write(f"Active bubble: `{st.session_state.active_bubble_id}`")
    st.write(f"Active bubbles: `{len(st.session_state.bubbles)}`")
    st.write(st.session_state.bubbles)
