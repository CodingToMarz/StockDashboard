"""
Chart building functions for StockDashboard.
"""
import logging

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def build_price_chart(
    df: pd.DataFrame,
    bubble: dict,
    config: dict,
    chart_height: int
) -> go.Figure:
    """
    Build candlestick chart with optional moving averages and volume.
    
    Args:
        df: Price data with Open, High, Low, Close, Volume columns
        bubble: Bubble config with show_ma and show_volume flags
        config: Period config with allow_ma and rangebreaks
        chart_height: Chart height in pixels
    
    Returns:
        Plotly figure object
    """
    rows = 2 if bubble["show_volume"] else 1
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.74, 0.26] if rows == 2 else [1]
    )
    
    # Candlestick trace
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
    
    # Moving averages (if enabled and allowed)
    if bubble["show_ma"] and config["allow_ma"]:
        for label, window, color in [
            ("20 MA", 20, "#f97316"),
            ("50 MA", 50, "#14b8a6"),
            ("200 MA", 200, "#8b5cf6")
        ]:
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
    
    # Volume bars (if enabled)
    if bubble["show_volume"]:
        colors = [
            "#22c55e" if c >= o else "#ef4444"
            for c, o in zip(df["Close"], df["Open"])
        ]
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
    
    # Layout styling
    fig.update_layout(
        template="plotly_dark",
        height=chart_height,
        paper_bgcolor="rgba(17,24,39,0)",
        plot_bgcolor="rgba(17,24,39,.78)",
        font=dict(color="#e5e7eb", size=12),
        legend=dict(
            font=dict(size=11),
            x=0.01,
            y=0.99,
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="#334155",
            borderwidth=1
        ),
        margin=dict(l=60, r=20, t=40, b=40),
        hovermode="x unified"
    )
    
    # Axes styling
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#334155",
        gridwidth=0.5,
        tickfont=dict(color="#cbd5e1", size=11),
        rangebreaks=config["rangebreaks"]
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#334155",
        gridwidth=0.5,
        tickfont=dict(color="#cbd5e1", size=11)
    )
    
    fig.update_yaxes(title_text="Price", row=1, col=1)
    
    logger.info(f"Built price chart with {len(df)} candles, MA={bubble['show_ma']}, Volume={bubble['show_volume']}")
    return fig
