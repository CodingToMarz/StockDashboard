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

APP_VERSION = "v0.3.9-visible-bubble-frame"
MAX_BUBBLES = 4
PROFILE_PATH = Path("data/profiles.json")
BUBBLE_TYPES = ["Price Chart"]

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
.stApp{background:radial-gradient(circle at 18% 0%,rgba(59,130,246,.24),transparent 34%),radial-gradient(circle at 86% 10%,rgba(125,211,252,.10),transparent 28%),#0b1220;color:#f8fafc;}
header[data-testid="stHeader"]{background:rgba(11,18,32,.84)!important;backdrop-filter:blur(8px)}
header[data-testid="stHeader"] button,button[title*="sidebar"],button[aria-label*="sidebar"]{background:rgba(96,165,250,.72)!important;border:2px solid rgba(219,234,254,.88)!important;border-radius:12px!important;box-shadow:0 0 16px rgba(96,165,250,.62),inset 0 1px 0 rgba(255,255,255,.38)!important;color:#f8fafc!important;fill:#f8fafc!important;opacity:1!important;}
section[data-testid="stSidebar"]{background:#0f172a;border-right:2px solid rgba(147,197,253,.58)}
section[data-testid="stSidebar"] *{color:#dbeafe!important}.block-container{padding-top:2.4rem;max-width:1720px}h1,h2,h3,h4,p,label,span,div{color:#f8fafc}

/* Visible bubble frame: target outer container and first child so the edge actually shows. */
div[data-testid="stVerticalBlockBorderWrapper"]{border:5px solid rgba(226,232,240,.72)!important;border-radius:34px!important;padding:18px 20px 14px 20px!important;margin-bottom:30px!important;overflow:visible!important;background:linear-gradient(145deg,rgba(255,255,255,.12),rgba(255,255,255,.035) 38%,rgba(96,165,250,.13)),radial-gradient(circle at 14% 0%,rgba(248,250,252,.34),transparent 36%),linear-gradient(180deg,rgba(17,24,39,.96),rgba(15,23,42,.99))!important;box-shadow:0 24px 54px rgba(0,0,0,.46),0 0 0 2px rgba(255,255,255,.16),0 0 34px rgba(226,232,240,.30),0 0 70px rgba(96,165,250,.22),inset 0 2px 0 rgba(255,255,255,.42),inset 0 0 28px rgba(226,232,240,.14),inset 0 -26px 46px rgba(15,23,42,.50)!important;}
div[data-testid="stVerticalBlockBorderWrapper"]>div,div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"]{border-radius:26px!important;box-shadow:inset 0 0 0 2px rgba(241,245,249,.34),inset 0 1px 0 rgba(255,255,255,.32)!important;background:rgba(15,23,42,.25)!important;}
div[data-testid="stVerticalBlockBorderWrapper"]::before{content:"";display:block;height:3px;border-radius:999px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.76),rgba(191,219,254,.50),transparent);margin-bottom:10px;}
div[data-testid="stVerticalBlockBorderWrapper"]::after{content:"";display:block;height:2px;border-radius:999px;background:linear-gradient(90deg,transparent,rgba(226,232,240,.38),rgba(96,165,250,.26),transparent);margin-top:10px;}

/* High contrast controls. */
div[data-testid="stButton"] button,div[data-testid="stButton"] button *{color:#020617!important;-webkit-text-fill-color:#020617!important;background-image:none!important;text-shadow:none!important;opacity:1!important;white-space:nowrap!important}div[data-testid="stButton"] button{background:#fff!important;border:1px solid #60a5fa!important;border-radius:10px!important;font-weight:850!important;min-height:38px!important}div[data-testid="stButton"] button:hover{background:#dbeafe!important;border-color:#2563eb!important}div[data-testid="stButton"] button:disabled,div[data-testid="stButton"] button:disabled *{background:#e2e8f0!important;color:#334155!important;-webkit-text-fill-color:#334155!important;opacity:1!important}
input,textarea,input *,textarea *{color:#020617!important;-webkit-text-fill-color:#020617!important;caret-color:#020617!important}input::placeholder,textarea::placeholder{color:#475569!important;opacity:1!important}div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,div[data-baseweb="textarea"]>div{background:#fff!important;color:#020617!important;border:1px solid #cbd5e1!important}div[data-baseweb="select"],div[data-baseweb="select"] *,div[data-baseweb="input"],div[data-baseweb="input"] *,div[data-baseweb="textarea"],div[data-baseweb="textarea"] *{color:#020617!important;fill:#020617!important;-webkit-text-fill-color:#020617!important}div[data-baseweb="popover"],div[data-baseweb="popover"] *,div[data-baseweb="menu"],div[data-baseweb="menu"] *,ul[role="listbox"],ul[role="listbox"] *,div[role="option"],div[role="option"] *,li[role="option"],li[role="option"] *{background:#fff!important;color:#020617!important;-webkit-text-fill-color:#020617!important;opacity:1!important}div[role="option"]:hover,li[role="option"]:hover{background:#dbeafe!important}
div[data-testid="stCheckbox"] label,div[data-testid="stCheckbox"] label *{color:#bfdbfe!important;font-weight:700!important}div[data-testid="stCheckbox"] input[type="checkbox"]{accent-color:#60a5fa!important}div[data-testid="stCheckbox"] [data-baseweb="checkbox"]>div:first-child{border:2px solid #93c5fd!important;background:#0f172a!important;box-shadow:0 0 10px rgba(147,197,253,.22)!important}div[data-testid="stCheckbox"] [aria-checked="true"]>div:first-child,div[data-testid="stCheckbox"] [data-checked="true"]>div:first-child{background:#60a5fa!important;border-color:#dbeafe!important;box-shadow:0 0 0 2px rgba(96,165,250,.28),0 0 16px rgba(147,197,253,.42)!important}div[data-testid="stCheckbox"] svg{color:#020617!important;fill:#020617!important;stroke:#020617!important}
div[data-testid="stExpander"]{background:rgba(17,24,39,.96)!important;border:1px solid rgba(147,197,253,.36)!important;border-radius:14px!important}div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary *,div[data-testid="stExpander"] details,div[data-testid="stExpander"] p,div[data-testid="stExpander"] span{background:transparent!important;color:#f8fafc!important;fill:#f8fafc!important}code,pre,code *,pre *{background:#0f172a!important;color:#86efac!important;-webkit-text-fill-color:#86efac!important;text-shadow:none!important}
.bubble-title{font-size:1.05rem;font-weight:900;color:#f8fafc!important;margin-bottom:4px}.bubble-subtitle{font-size:.78rem;color:#93c5fd!important;margin-bottom:10px}.bubble-footer{font-size:.75rem;color:#bfdbfe!important;border-top:1px solid rgba(191,219,254,.34);margin-top:8px;padding-top:8px}div[data-testid="stMetric"]{background:rgba(15,23,42,.92);border:1px solid rgba(147,197,253,.45);border-radius:16px;padding:10px}div[data-testid="stMetricLabel"] p{color:#93c5fd!important;font-weight:700}div[data-testid="stMetricValue"]{color:#f8fafc!important}.stRadio label,.stSelectbox label,.stTextInput label{color:#bfdbfe!important;font-weight:700}
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
    return {"id": str(uuid.uuid4())[:8], "ticker": ticker, "timeframe": "6M", "bubble_type": "Price Chart", "show_ma": True, "show_volume": True}


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


def render_bubble(bubble: dict, all_tickers: list[str], chart_height: int):
    bubble_id = bubble["id"]
    config = PERIOD_CONFIG[bubble["timeframe"]]
    with st.container(border=True):
        title_col, menu_col = st.columns([0.68, 0.32], vertical_alignment="top")
        with title_col:
            st.markdown(f'<div class="bubble-title">{bubble["ticker"]} • {bubble["bubble_type"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bubble-subtitle">{bubble["timeframe"]} · independent dashboard bubble</div>', unsafe_allow_html=True)
        with menu_col:
            with st.expander("Menu", expanded=False):
                selected_ticker = st.selectbox("Stock ticker", all_tickers, index=all_tickers.index(bubble["ticker"]) if bubble["ticker"] in all_tickers else 0, key=f"ticker_{bubble_id}")
                custom_ticker = st.text_input("Or type ticker", value="", key=f"custom_ticker_{bubble_id}")
                selected_timeframe = st.selectbox("Timeframe", list(PERIOD_CONFIG.keys()), index=list(PERIOD_CONFIG.keys()).index(bubble["timeframe"]), key=f"timeframe_{bubble_id}")
                selected_type = st.selectbox("Bubble type", BUBBLE_TYPES, index=0, key=f"type_{bubble_id}")
                show_ma = st.checkbox("Moving averages", value=bubble["show_ma"], key=f"ma_{bubble_id}")
                show_volume = st.checkbox("Volume", value=bubble["show_volume"], key=f"volume_{bubble_id}")
                if st.button("Apply", key=f"apply_{bubble_id}", use_container_width=True):
                    bubble.update({"ticker": custom_ticker.upper().strip() or selected_ticker, "timeframe": selected_timeframe, "bubble_type": selected_type, "show_ma": show_ma, "show_volume": show_volume})
                    st.rerun()
                c1, c2 = st.columns([1.25, 1.0])
                with c1:
                    if st.button("Duplicate", key=f"duplicate_{bubble_id}", use_container_width=True):
                        if len(st.session_state.bubbles) < MAX_BUBBLES:
                            new_bubble = bubble.copy(); new_bubble["id"] = str(uuid.uuid4())[:8]
                            st.session_state.bubbles.append(new_bubble); st.rerun()
                        else:
                            st.warning("Maximum of 4 bubbles reached.")
                with c2:
                    if st.button("Remove", key=f"remove_{bubble_id}", use_container_width=True):
                        if len(st.session_state.bubbles) > 1:
                            st.session_state.bubbles = [b for b in st.session_state.bubbles if b["id"] != bubble_id]; st.rerun()
                        else:
                            st.warning("Keep at least one bubble.")
        with st.spinner(f"Loading {bubble['ticker']}..."):
            df, status, connector = get_price_data(bubble["ticker"], config["period"], config["interval"])
        if df.empty:
            st.warning("No valid price data available for this bubble.")
        else:
            latest = df.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Ticker", bubble["ticker"]); m2.metric("Last Price", f"${latest['Close']:,.2f}"); m3.metric("Rows", f"{len(df):,}")
            st.plotly_chart(build_price_chart(df.copy(), bubble, config, chart_height), use_container_width=True, key=f"chart_{bubble_id}", config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
        st.markdown(f'<div class="bubble-footer">Source: {connector} · Status: {status} · Updated: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)


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
        profiles[selected_profile].append(ticker); save_profiles(profiles); st.sidebar.success(f"Added {ticker}"); st.rerun()
if st.sidebar.button("+ Add Bubble"):
    if len(st.session_state.bubbles) < MAX_BUBBLES:
        st.session_state.bubbles.append(default_bubble(profiles[selected_profile][0] if profiles[selected_profile] else all_tickers[0])); st.rerun()
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
    st.write(f"Active bubbles: `{len(st.session_state.bubbles)}`")
    st.write(st.session_state.bubbles)
