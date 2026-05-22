import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# --------------------
# Styling
# --------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0f1117;
        color: white;
    }
    section[data-testid="stSidebar"] {
        background-color: #161b22;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------
# Load profiles
# --------------------
with open("data/profiles.json", "r") as f:
    profiles = json.load(f)

# --------------------
# Sidebar
# --------------------
st.sidebar.title("Stock Profiles")

profile_names = list(profiles.keys())
selected_profile = st.sidebar.selectbox("Select Profile", profile_names)

new_ticker = st.sidebar.text_input("Add Ticker")
if st.sidebar.button("Add To Profile"):
    ticker = new_ticker.upper().strip()
    if ticker and ticker not in profiles[selected_profile]:
        profiles[selected_profile].append(ticker)
        with open("data/profiles.json", "w") as f:
            json.dump(profiles, f, indent=2)
        st.sidebar.success(f"Added {ticker}")

selected_stock = st.sidebar.selectbox(
    "Select Stock",
    profiles[selected_profile]
)

# --------------------
# Timeframes
# --------------------
period_map = {
    "1D": "1d",
    "5D": "5d",
    "1M": "1mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
    "MAX": "max",
}

selected_period = st.selectbox(
    "Timeframe",
    list(period_map.keys()),
    index=4,
)

# --------------------
# Data
# --------------------
stock = yf.Ticker(selected_stock)
df = stock.history(period=period_map[selected_period])

# --------------------
# Moving Averages
# --------------------
if selected_period not in ["1D", "5D"]:
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()

# --------------------
# Chart
# --------------------
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["Close"],
        mode="lines",
        name="Price",
    )
)

if selected_period not in ["1D", "5D"]:
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], mode="lines", name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines", name="MA50"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], mode="lines", name="MA200"))

fig.update_layout(
    title=f"{selected_stock} Price Chart",
    template="plotly_dark",
    height=700,
    xaxis_title="Date",
    yaxis_title="Price",
)

st.title("Stock Dashboard")
st.plotly_chart(fig, use_container_width=True)
