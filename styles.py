"""CSS and HTML styling helpers for StockDashboard."""
from datetime import datetime


def get_app_css() -> str:
    return """
<style>
.stApp{background:#0b1220;color:#f8fafc}.block-container{padding-top:2.4rem;max-width:1720px}h1,h2,h3,h4,p,label,span,div{color:#f8fafc}section[data-testid="stSidebar"]{background:#0f172a;border-right:2px solid #bfdbfe}section[data-testid="stSidebar"] *{color:#dbeafe!important}header[data-testid="stHeader"]{background:rgba(11,18,32,.86)!important}header[data-testid="stHeader"] button,button[title*="sidebar"],button[aria-label*="sidebar"]{background:#60a5fa!important;border:2px solid #f8fafc!important;border-radius:12px!important;color:#fff!important;fill:#fff!important}
div[data-testid="stVerticalBlockBorderWrapper"]{border:4px solid rgba(241,245,249,.82)!important;border-radius:24px!important;background:#0f172a!important;padding:16px 18px!important;margin-bottom:24px!important;box-shadow:0 10px 28px rgba(0,0,0,.34)!important;overflow:hidden!important}
/* General action buttons stay readable. */
div[data-testid="stButton"] button,div[data-testid="stButton"] button *{color:#020617!important;-webkit-text-fill-color:#020617!important;white-space:nowrap!important}div[data-testid="stButton"] button{background:#fff!important;border:1px solid #60a5fa!important;border-radius:10px!important;font-weight:800!important;min-height:38px!important}div[data-testid="stButton"] button:hover{background:#dbeafe!important}
/* White form fields with dark text. */
input,textarea,input *,textarea *,div[data-baseweb="select"],div[data-baseweb="select"] *,div[data-baseweb="input"],div[data-baseweb="input"] *{color:#020617!important;-webkit-text-fill-color:#020617!important}div[data-baseweb="select"]>div,div[data-baseweb="input"]>div{background:#fff!important;color:#020617!important;border:1px solid #cbd5e1!important}ul[role="listbox"],ul[role="listbox"] *,div[role="option"],div[role="option"] *,li[role="option"],li[role="option"] *{background:#fff!important;color:#020617!important;-webkit-text-fill-color:#020617!important}
/* Popover/dropdown menu shell. */
div[data-testid="stPopover"] button{background:#111827!important;border:1px solid #64748b!important;border-radius:12px!important;color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important;font-weight:850!important}div[data-testid="stPopover"] button *{color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important}
div[data-baseweb="popover"]>div{background:#0f172a!important;border:1px solid #64748b!important;border-radius:16px!important;box-shadow:0 18px 44px rgba(0,0,0,.55),0 0 0 1px rgba(147,197,253,.18)!important}div[data-baseweb="popover"] div[data-testid="stVerticalBlock"],div[data-baseweb="popover"] section{background:#0f172a!important;color:#f8fafc!important}div[data-baseweb="popover"] label,div[data-baseweb="popover"] p,div[data-baseweb="popover"] span:not([role="option"] span){color:#dbeafe!important;-webkit-text-fill-color:#dbeafe!important;font-weight:700!important}div[data-baseweb="popover"] div[data-testid="stButton"] button,div[data-baseweb="popover"] div[data-testid="stButton"] button *{background:#fff!important;color:#020617!important;-webkit-text-fill-color:#020617!important}
div[data-testid="stCheckbox"] label,div[data-testid="stCheckbox"] label *{color:#bfdbfe!important;font-weight:700!important}div[data-testid="stCheckbox"] input[type="checkbox"]{accent-color:#60a5fa!important}div[data-testid="stExpander"]{background:#111827!important;border:1px solid #64748b!important;border-radius:14px!important}code,pre,code *,pre *{background:#0f172a!important;color:#86efac!important;-webkit-text-fill-color:#86efac!important}
/* Compact dark timeframe radio row. */
div[role="radiogroup"]{background:rgba(15,23,42,.52);border:1px solid #334155;border-radius:10px;padding:6px 8px;gap:8px}div[role="radiogroup"] label{background:#1e293b!important;border:1px solid #475569!important;border-radius:8px!important;padding:4px 10px!important;margin-right:4px!important}div[role="radiogroup"] label *{color:#cbd5e1!important;font-weight:800!important}div[role="radiogroup"] label:has(input:checked){background:#60a5fa!important;border-color:#93c5fd!important}div[role="radiogroup"] label:has(input:checked) *{color:#020617!important;-webkit-text-fill-color:#020617!important}
.stock-panel-header{background:linear-gradient(135deg,#101827 0%,#172234 100%);padding:14px 16px;border-radius:14px;margin-bottom:12px;border:1px solid #334155;border-left:4px solid #60a5fa}.stock-id{display:flex;align-items:baseline;gap:10px}.stock-ticker{font-size:1.35rem;font-weight:900;color:#f8fafc}.company-name{font-size:.9rem;color:#94a3b8}.price-row{display:flex;align-items:baseline;gap:12px;margin:8px 0}.stock-price{font-size:2rem;font-weight:800;color:#f8fafc}.currency{font-size:.82rem;color:#cbd5e1}.change-up{color:#22c55e;font-weight:800}.change-down{color:#ef4444;font-weight:800}.market-row{display:flex;justify-content:space-between;border-top:1px solid #334155;padding-top:8px;font-size:.82rem;color:#cbd5e1}.market-open{color:#22c55e;font-weight:800}.market-closed{color:#f59e0b;font-weight:800}.active-pill{font-size:.7rem;font-weight:800;color:#020617;background:#93c5fd;border-radius:999px;padding:3px 8px}
.stats-strip{display:grid;grid-template-columns:repeat(6,1fr);background:rgba(15,23,42,.62);border:1px solid #334155;border-radius:10px;margin-bottom:10px;overflow:hidden}.stat-cell{padding:8px 10px;border-right:1px solid #334155}.stat-cell:last-child{border-right:none}.stat-label{font-size:.7rem;color:#94a3b8;text-transform:uppercase;margin-bottom:3px}.stat-value{font-size:.92rem;color:#f8fafc;font-weight:700}.timeframe-caption{font-size:.75rem;color:#94a3b8;margin-right:8px}.bubble-footer{font-size:.75rem;color:#bfdbfe!important;border-top:1px solid rgba(191,219,254,.34);margin-top:8px;padding-top:8px}
</style>
"""


def get_bubble_header_html(ticker: str, company_name: str, price: float, price_change: float, pct_change: float, market_status: str, is_active: bool = False, last_update: datetime | None = None) -> str:
    if last_update is None:
        last_update = datetime.now()
    change_class = "change-up" if price_change >= 0 else "change-down"
    sign = "+" if price_change >= 0 else ""
    market_class = "market-open" if "Open" in market_status else "market-closed"
    active = '<span class="active-pill">ACTIVE</span>' if is_active else ""
    safe_price = price if price is not None else 0
    return f'<div class="stock-panel-header"><div class="stock-id"><span class="stock-ticker">{ticker}</span><span class="company-name">{company_name}</span>{active}</div><div class="price-row"><span class="stock-price">{safe_price:,.2f}</span><span class="currency">USD</span><span class="{change_class}">{sign}{price_change:,.2f}</span><span class="{change_class}">({sign}{pct_change:.2f}%)</span></div><div class="market-row"><span class="{market_class}">{market_status}</span><span>{last_update.strftime("%b %d, %Y %I:%M %p")}</span></div></div>'


def get_stats_strip_html(open_price, high, low, prev_close, volume: str, market_cap: str) -> str:
    def money(value):
        return f"${value:,.2f}" if value is not None else "N/A"
    stats = [("Open", money(open_price)), ("High", money(high)), ("Low", money(low)), ("Prev Close", money(prev_close)), ("Volume", volume), ("Market Cap", market_cap)]
    cells = "".join(f'<div class="stat-cell"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>' for label, value in stats)
    return f'<div class="stats-strip">{cells}</div>'


def get_timeframe_buttons_html(timeframes: list[str], active_timeframe: str, bubble_id: str) -> str:
    chips = []
    for tf in timeframes:
        cls = " timeframe-chip-active" if tf == active_timeframe else ""
        chips.append(f'<span class="timeframe-chip{cls}">{tf}</span>')
    return f'<div class="timeframe-shell"><span class="timeframe-caption">Timeframe</span>{"".join(chips)}</div>'
