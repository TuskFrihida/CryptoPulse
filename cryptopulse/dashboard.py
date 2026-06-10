"""
Interactive dashboard — the "visualize" stage of the pipeline.

Numbers in a database are invisible to a human until you draw them. This module
renders the stored price history into a single self-contained HTML file with
interactive charts (zoom, pan, hover tooltips) powered by Plotly. No web server
needed — just open reports/dashboard.html in any browser.

That single file is perfect portfolio material: you can screenshot it, screen-
record it, or host it on GitHub Pages.

Automation skills demonstrated here:
  * Generating charts programmatically from data (Plotly graph objects)
  * Combining multiple coins into one figure with a price + moving-average line
  * Building an HTML report from a template and writing it to disk
  * Producing a portable artifact other people / systems can consume
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import plot

from .analysis import CoinSummary, add_moving_average, load_history_df, summarise_all
from .config import REPORTS_DIR, load_settings
from .logging_setup import get_logger
from .storage import PriceStore

log = get_logger(__name__)

DASHBOARD_PATH = REPORTS_DIR / "dashboard.html"


def _price_figure(coins: list[str], store: PriceStore, window: int = 5) -> go.Figure:
    """Build one Plotly figure overlaying each coin's price and moving average."""
    fig = go.Figure()

    for coin in coins:
        df = load_history_df(coin, store)
        if df.empty:
            continue
        df = add_moving_average(df, window=window)

        # The actual price line.
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["price"],
                mode="lines+markers",
                name=f"{coin} price",
            )
        )
        # The smoothed trend line, dashed so it's visually distinct.
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["moving_avg"],
                mode="lines",
                name=f"{coin} MA{window}",
                line=dict(dash="dash"),
            )
        )

    fig.update_layout(
        title="CryptoPulse — Price History & Trend",
        xaxis_title="Time (UTC)",
        yaxis_title="Price",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _summary_table_html(summaries: list[CoinSummary]) -> str:
    """Render the per-coin summary list as a small HTML table."""
    arrows = {"up": "▲", "down": "▼", "flat": "▬"}
    colors = {"up": "#26a69a", "down": "#ef5350", "flat": "#999999"}

    rows = []
    for s in summaries:
        change = f"{s.change_24h:+.2f}%" if s.change_24h is not None else "n/a"
        color = colors.get(s.trend, "#999999")
        rows.append(
            f"<tr>"
            f"<td>{s.coin}</td>"
            f"<td style='text-align:right'>{s.latest_price:,.2f}</td>"
            f"<td style='text-align:right'>{s.moving_avg:,.2f}</td>"
            f"<td style='text-align:right;color:{color}'>{arrows.get(s.trend, '')} {s.trend}</td>"
            f"<td style='text-align:right'>{change}</td>"
            f"<td style='text-align:right'>{s.samples}</td>"
            f"</tr>"
        )

    return (
        "<table>"
        "<thead><tr>"
        "<th>Coin</th><th>Latest</th><th>Moving avg</th>"
        "<th>Trend</th><th>24h change</th><th>Samples</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _render_html(chart_div: str, table_html: str, vs_currency: str) -> str:
    """Assemble the full HTML page from the chart and summary table."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CryptoPulse Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#0e1117; color:#e6e6e6;
            margin:0; padding:24px; }}
    h1 {{ margin:0 0 4px; }}
    .subtitle {{ color:#888; margin-bottom:24px; }}
    table {{ border-collapse:collapse; width:100%; margin-top:24px;
             background:#161b22; border-radius:8px; overflow:hidden; }}
    th, td {{ padding:10px 14px; border-bottom:1px solid #21262d; }}
    th {{ background:#21262d; text-align:left; }}
    .footer {{ color:#666; margin-top:24px; font-size:13px; }}
  </style>
</head>
<body>
  <h1>🪙 CryptoPulse Dashboard</h1>
  <div class="subtitle">Prices shown in {vs_currency.upper()} · generated {generated}</div>
  {chart_div}
  {table_html}
  <div class="footer">Generated automatically by CryptoPulse.</div>
</body>
</html>
"""


def build_dashboard(
    coins: list[str] | None = None,
    vs_currency: str | None = None,
    store: PriceStore | None = None,
    window: int = 5,
) -> Path:
    """Build the HTML dashboard from stored data and return its file path."""
    settings = load_settings()
    coins = coins or settings.coins
    vs_currency = vs_currency or settings.vs_currency
    store = store or PriceStore()

    summaries = summarise_all(coins, store, window=window)
    figure = _price_figure(coins, store, window=window)

    # output_type="div" returns just the chart HTML (with its JS), so we can
    # embed it inside our own page instead of a full standalone Plotly file.
    chart_div = plot(figure, output_type="div", include_plotlyjs="cdn")
    table_html = _summary_table_html(summaries)
    html = _render_html(chart_div, table_html, vs_currency)

    DASHBOARD_PATH.write_text(html, encoding="utf-8")
    log.info("Dashboard written to %s", DASHBOARD_PATH)
    return DASHBOARD_PATH


# Build the dashboard from whatever is currently stored.
# Run with:  python -m cryptopulse.dashboard
if __name__ == "__main__":
    path = build_dashboard()
    print(f"Dashboard ready: {path}")
    print("Open it in your browser to view the interactive charts.")
