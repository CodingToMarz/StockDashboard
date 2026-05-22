"""
CSS and HTML styling for StockDashboard bubbles and components.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_app_css() -> str:
    """Get main application CSS."""
    return """
<style>
.stApp{background:#0b1220;color:#f8fafc}header[data-testid="stHeader"]{background:rgba(11,18,32,.86)!important;backdrop-filter:blur(8px)}.block-container{padding-top:2.4rem;max-width:1720px}h1,h2,[...]
header[data-testid="stHeader"] button,button[title*="sidebar"],button[aria-label*="sidebar"]{background:#60a5fa!important;border:2px solid #f8fafc!important;border-radius:12px!important;color:#fff[...]

/* Simple window border: remove experimental layered frame effects. */
div[data-testid="stVerticalBlockBorderWrapper"]{border:4px solid rgba(241,245,249,.82)!important;border-radius:24px!important;background:#0f172a!important;padding:16px 18px!important;margin-bottom[...]

/* Readable controls without broad leakage. */
div[data-testid="stButton"] button,div[data-testid="stButton"] button *{color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap!important;text-shadow:none!important}di[...]
input,textarea,input *,textarea *{color:#020617!important;-webkit-text-fill-color:#020617!important;caret-color:#020617!important}input::placeholder,textarea::placeholder{color:#475569!important;o[...]
div[data-testid="stCheckbox"] label,div[data-testid="stCheckbox"] label *{color:#bfdbfe!important;font-weight:700!important}div[data-testid="stCheckbox"] input[type="checkbox"]{accent-color:#60a5f[...]
div[data-testid="stExpander"]{background:#111827!important;border:1px solid #64748b!important;border-radius:14px!important}div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summa[...]
.bubble-title{font-size:1.05rem;font-weight:900;color:#f8fafc!important;margin-bottom:4px}.bubble-subtitle{font-size:.78rem;color:#93c5fd!important;margin-bottom:10px}.bubble-footer{font-size:.75r[...]
</style>
"""


def get_bubble_header_html(
    ticker: str,
    company_name: str,
    price: float,
    price_change: float,
    pct_change: float,
    market_status: str,
    last_update: datetime | None = None
) -> str:
    """
    Create TradingView-style bubble header HTML.
    
    Shows:
    - TICKER   Company Name
    - Current Price USD   +$ Change   +% Change
    - Market Status   Live Date + Time
    """
    if last_update is None:
        last_update = datetime.now()
    
    update_time = last_update.strftime("%H:%M:%S")
    update_date = last_update.strftime("%Y-%m-%d")
    
    # Color coding for changes
    change_color = "#22c55e" if price_change >= 0 else "#ef4444"
    change_symbol = "+" if price_change >= 0 else ""
    
    html = f"""
    <div style="
        background: linear-gradient(135deg, #111827 0%, #1a2637 100%);
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 12px;
        border-left: 4px solid #60a5fa;
    ">
        <!-- Ticker and Company Name -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        ">
            <div>
                <span style="
                    font-size: 1.3rem;
                    font-weight: 900;
                    color: #f8fafc;
                    margin-right: 16px;
                ">{ticker}</span>
                <span style="
                    font-size: 0.95rem;
                    color: #94a3b8;
                ">{company_name}</span>
            </div>
        </div>
        
        <!-- Price and Changes -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 12px;
            gap: 24px;
        ">
            <div>
                <span style="
                    font-size: 1.8rem;
                    font-weight: 700;
                    color: #f8fafc;
                ">${price:,.2f}</span>
                <span style="
                    font-size: 0.85rem;
                    color: #cbd5e1;
                    margin-left: 8px;
                ">USD</span>
            </div>
            <div style="
                display: flex;
                gap: 16px;
                align-items: baseline;
            ">
                <span style="
                    color: {change_color};
                    font-weight: 600;
                    font-size: 1rem;
                ">{change_symbol}${price_change:,.2f}</span>
                <span style="
                    color: {change_color};
                    font-weight: 600;
                    font-size: 1rem;
                ">{change_symbol}{pct_change:.2f}%</span>
            </div>
        </div>
        
        <!-- Market Status and Time -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: #cbd5e1;
            border-top: 1px solid #334155;
            padding-top: 8px;
        ">
            <span>{market_status}</span>
            <span>{update_date} {update_time}</span>
        </div>
    </div>
    """
    
    return html


def get_stats_strip_html(
    open_price: float | None,
    high: float | None,
    low: float | None,
    prev_close: float | None,
    volume: str,
    market_cap: str
) -> str:
    """
    Create HTML for financial stats strip.
    
    Shows: Open | High | Low | Prev Close | Volume | Market Cap
    """
    stats = [
        ("Open", f"${open_price:,.2f}" if open_price else "N/A"),
        ("High", f"${high:,.2f}" if high else "N/A"),
        ("Low", f"${low:,.2f}" if low else "N/A"),
        ("Prev Close", f"${prev_close:,.2f}" if prev_close else "N/A"),
        ("Volume", volume),
        ("Market Cap", market_cap)
    ]
    
    stats_html = ""
    for label, value in stats:
        stats_html += f"""
        <div style="
            flex: 1;
            text-align: center;
            padding: 8px;
            border-right: 1px solid #334155;
        ">
            <div style="
                font-size: 0.75rem;
                color: #94a3b8;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            ">{label}</div>
            <div style="
                font-size: 0.95rem;
                color: #f8fafc;
                font-weight: 600;
            ">{value}</div>
        </div>
        """
    
    # Remove last border-right
    stats_html = stats_html.replace(
        'border-right: 1px solid #334155;\n        ">', 
        '\n        ">', 
        1
    )
    
    html = f"""
    <div style="
        display: flex;
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid #334155;
        border-radius: 8px;
        margin-bottom: 12px;
        overflow: hidden;
    ">
        {stats_html}
    </div>
    """
    
    return html


def get_timeframe_buttons_html(
    timeframes: list[str],
    active_timeframe: str,
    bubble_id: str
) -> str:
    """
    Create HTML for timeframe selector buttons.
    
    Shows: 1D  5D  1M  6M  1Y  5Y  MAX
    Active timeframe is highlighted.
    """
    buttons_html = ""
    
    for tf in timeframes:
        is_active = tf == active_timeframe
        bg_color = "#60a5fa" if is_active else "#334155"
        text_color = "#020617" if is_active else "#cbd5e1"
        border_color = "#60a5fa" if is_active else "#475569"
        
        buttons_html += f"""
        <button
            onclick="Streamlit.setComponentValue('{{\'timeframe\': \'{tf}\', \'bubble_id\': \'{bubble_id}\'}})"
            style="
                background: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                margin-right: 6px;
                transition: all 0.2s;
            "
            onmouseover="this.style.opacity='0.8'"
            onmouseout="this.style.opacity='1'"
        >
            {tf}
        </button>
        """
    
    html = f"""
    <div style="
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        padding: 8px;
        background: rgba(15, 23, 42, 0.5);
        border-radius: 8px;
        border: 1px solid #334155;
    ">
        {buttons_html}
    </div>
    """
    
    return html
