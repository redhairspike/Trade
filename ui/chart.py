import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from engine.order import Trade


def build_candlestick_chart(
    df: pd.DataFrame,
    trades: list[Trade] | None = None,
    overlays: list[str] | None = None,
    sub_indicators: list[str] | None = None,
) -> go.Figure:
    """Build the main candlestick chart with overlays and sub-charts."""
    # Determine number of rows
    sub_indicators = sub_indicators or []
    n_subs = len(sub_indicators)
    total_rows = 1 + n_subs + 1  # candlestick + sub-indicators + volume

    row_heights = [0.5] + [0.15] * n_subs + [0.1]
    # Normalize
    total = sum(row_heights)
    row_heights = [h / total for h in row_heights]

    subplot_titles = [""] + sub_indicators + ["Volume"]

    fig = make_subplots(
        rows=total_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="K線",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    # Overlay indicators (MA, EMA, Bollinger, Pivot, SR)
    overlay_colors = ["#FFD700", "#00BFFF", "#FF69B4", "#32CD32", "#FFA500"]

    # Dedicated styles for Pivot and SR overlays
    _pivot_sr_styles = {
        "Pivot_P":  {"color": "#FFFFFF", "dash": "dot",  "width": 1.2},
        "Pivot_R1": {"color": "#ef5350", "dash": "dash", "width": 0.8},
        "Pivot_R2": {"color": "#ef5350", "dash": "dash", "width": 0.8},
        "Pivot_R3": {"color": "#c62828", "dash": "dash", "width": 0.8},
        "Pivot_S1": {"color": "#26a69a", "dash": "dash", "width": 0.8},
        "Pivot_S2": {"color": "#26a69a", "dash": "dash", "width": 0.8},
        "Pivot_S3": {"color": "#00796b", "dash": "dash", "width": 0.8},
        "SR_resistance": {"color": "#ef5350", "dash": "dashdot", "width": 1},
        "SR_support":    {"color": "#26a69a", "dash": "dashdot", "width": 1},
    }

    general_idx = 0
    if overlays:
        for col_name in overlays:
            if col_name in df.columns:
                style = _pivot_sr_styles.get(col_name)
                if style:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index, y=df[col_name],
                            name=col_name,
                            line=dict(width=style["width"], color=style["color"], dash=style["dash"]),
                            connectgaps=False,
                        ),
                        row=1, col=1,
                    )
                else:
                    color = overlay_colors[general_idx % len(overlay_colors)]
                    general_idx += 1
                    fig.add_trace(
                        go.Scatter(
                            x=df.index, y=df[col_name],
                            name=col_name, line=dict(width=1, color=color),
                        ),
                        row=1, col=1,
                    )

    # Trade markers
    if trades:
        entries_long = [(t.entry_fill.timestamp, t.entry_fill.price) for t in trades if t.side == "long"]
        entries_short = [(t.entry_fill.timestamp, t.entry_fill.price) for t in trades if t.side == "short"]
        exits = [(t.exit_fill.timestamp, t.exit_fill.price) for t in trades]

        if entries_long:
            fig.add_trace(
                go.Scatter(
                    x=[e[0] for e in entries_long],
                    y=[e[1] for e in entries_long],
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=10, color="#26a69a"),
                    name="買入",
                ),
                row=1, col=1,
            )
        if entries_short:
            fig.add_trace(
                go.Scatter(
                    x=[e[0] for e in entries_short],
                    y=[e[1] for e in entries_short],
                    mode="markers",
                    marker=dict(symbol="triangle-down", size=10, color="#ef5350"),
                    name="放空",
                ),
                row=1, col=1,
            )
        if exits:
            fig.add_trace(
                go.Scatter(
                    x=[e[0] for e in exits],
                    y=[e[1] for e in exits],
                    mode="markers",
                    marker=dict(symbol="x", size=8, color="#FFA500"),
                    name="平倉",
                ),
                row=1, col=1,
            )

    # Sub-indicator charts
    sub_colors = {
        "RSI": "#E040FB",
        "MACD_line": "#00BCD4", "MACD_signal": "#FF9800", "MACD_hist": "#78909C",
        "K": "#FFD700", "D": "#00BFFF",
        "ATR": "#66BB6A",
    }

    for idx, sub_name in enumerate(sub_indicators):
        row = idx + 2
        if sub_name == "RSI" and "RSI" in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                           line=dict(color=sub_colors.get("RSI", "#E040FB"))),
                row=row, col=1,
            )
            fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", opacity=0.5, row=row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", opacity=0.5, row=row, col=1)

        elif sub_name == "MACD":
            for col in ["MACD_line", "MACD_signal"]:
                if col in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df[col], name=col,
                                   line=dict(color=sub_colors.get(col, "#888"))),
                        row=row, col=1,
                    )
            if "MACD_hist" in df.columns:
                colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"]]
                fig.add_trace(
                    go.Bar(x=df.index, y=df["MACD_hist"], name="MACD Hist",
                           marker_color=colors),
                    row=row, col=1,
                )

        elif sub_name == "KD":
            for col in ["K", "D"]:
                if col in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df[col], name=col,
                                   line=dict(color=sub_colors.get(col, "#888"))),
                        row=row, col=1,
                    )
            fig.add_hline(y=80, line_dash="dash", line_color="#ef5350", opacity=0.5, row=row, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="#26a69a", opacity=0.5, row=row, col=1)

        elif sub_name == "ATR" and "ATR" in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df["ATR"], name="ATR",
                           line=dict(color=sub_colors.get("ATR", "#66BB6A"))),
                row=row, col=1,
            )

    # Volume
    if "Volume" in df.columns:
        vol_colors = ["#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
                       for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name="成交量", marker_color=vol_colors),
            row=total_rows, col=1,
        )

    fig.update_layout(
        template="plotly_dark",
        height=200 + 250 * total_rows,
        showlegend=True,
        legend=dict(orientation="h", y=1.02, x=0),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=20, t=40, b=30),
    )

    return fig


def build_equity_chart(equity_curve: pd.DataFrame) -> go.Figure:
    """Build equity curve chart."""
    fig = go.Figure()

    if not equity_curve.empty and "equity" in equity_curve.columns:
        fig.add_trace(go.Scatter(
            x=equity_curve.index,
            y=equity_curve["equity"],
            name="權益曲線",
            line=dict(color="#4CAF50", width=2),
            fill="tozeroy",
            fillcolor="rgba(76, 175, 80, 0.1)",
        ))

        # Drawdown
        cummax = equity_curve["equity"].cummax()
        drawdown = (equity_curve["equity"] - cummax) / cummax * 100
        fig.add_trace(go.Scatter(
            x=equity_curve.index,
            y=drawdown,
            name="回撤 %",
            line=dict(color="#ef5350", width=1),
            yaxis="y2",
        ))

    fig.update_layout(
        template="plotly_dark",
        height=300,
        showlegend=True,
        legend=dict(orientation="h", y=1.1),
        yaxis=dict(title="權益"),
        yaxis2=dict(title="回撤 %", overlaying="y", side="right"),
        margin=dict(l=50, r=50, t=20, b=30),
    )

    return fig
