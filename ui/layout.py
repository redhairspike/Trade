from dash import html, dcc, dash_table
from ui.components import build_sidebar, build_screener_panel, build_download_panel, build_metric_card


def build_layout() -> html.Div:
    """Build the main application layout.

    All tab contents are rendered statically and toggled via CSS display.
    This ensures all component IDs always exist in the DOM for callbacks.
    """
    return html.Div(
        [
            # Global data stores (always in DOM)
            dcc.Store(id="backtest-result-store"),
            dcc.Store(id="screener-data-store"),
            dcc.Store(id="selected-symbols-store"),
            dcc.Store(id="downloaded-csv-store"),
            dcc.Store(id="dl-data-store"),
            dcc.Download(id="dl-csv-download"),

            # Download status toast (global, always in DOM)
            html.Div(id="dl-download-status", style={
                "position": "fixed", "top": "8px", "right": "20px",
                "backgroundColor": "#1e1e2f", "borderRadius": "8px",
                "padding": "10px 18px", "zIndex": "9999",
                "border": "1px solid #333", "fontSize": "14px",
                "display": "none",
            }),
            dcc.Interval(id="dl-toast-timer", interval=3000, max_intervals=1, disabled=True),

            # Main tabs
            dcc.Tabs(
                id="main-tabs",
                value="download",
                children=[
                    dcc.Tab(label="資料下載", value="download", style=_tab_style(), selected_style=_tab_selected()),
                    dcc.Tab(label="選股", value="screener", style=_tab_style(), selected_style=_tab_selected()),
                    dcc.Tab(label="回測", value="backtest", style=_tab_style(), selected_style=_tab_selected()),
                ],
                style={"backgroundColor": "#0d0d1a"},
            ),

            # All tab contents rendered statically, toggled by callback
            html.Div(id="tab-download", children=[build_download_panel()]),
            html.Div(id="tab-screener", children=[build_screener_panel()], style={"display": "none"}),
            html.Div(id="tab-backtest", children=[_build_backtest_content()], style={"display": "none"}),
        ],
        style={
            "backgroundColor": "#0d0d1a",
            "minHeight": "100vh",
            "fontFamily": "'Segoe UI', 'Microsoft JhengHei', sans-serif",
        },
    )


def _build_backtest_content() -> html.Div:
    """Build backtest tab with sidebar and main area (all sub-panels included)."""
    return html.Div(
        [
            build_sidebar(),
            html.Div(
                [
                    dcc.Tabs(
                        id="result-tabs",
                        value="chart",
                        children=[
                            dcc.Tab(label="Chart", value="chart",
                                    style=_tab_style(), selected_style=_tab_selected()),
                            dcc.Tab(label="Trades", value="trades",
                                    style=_tab_style(), selected_style=_tab_selected()),
                            dcc.Tab(label="Metrics", value="metrics",
                                    style=_tab_style(), selected_style=_tab_selected()),
                        ],
                    ),
                    html.Div(id="result-tab-content", style={"padding": "10px"}),
                ],
                style={"flex": "1", "overflow": "auto"},
            ),
        ],
        style={"display": "flex", "height": "calc(100vh - 50px)"},
    )


def build_chart_panel() -> html.Div:
    """Build chart display panel."""
    return html.Div([
        dcc.Loading(
            id="chart-loading",
            children=[
                dcc.Graph(id="main-chart", style={"height": "500px"}),
                dcc.Graph(id="equity-chart", style={"height": "300px"}),
            ],
            type="circle",
        ),
    ])


def build_trades_panel() -> html.Div:
    """Build trades table panel."""
    return html.Div([
        dash_table.DataTable(
            id="trades-table",
            columns=[
                {"name": "#", "id": "idx"},
                {"name": "方向", "id": "side"},
                {"name": "進場時間", "id": "entry_time"},
                {"name": "進場價", "id": "entry_price"},
                {"name": "出場時間", "id": "exit_time"},
                {"name": "出場價", "id": "exit_price"},
                {"name": "數量", "id": "quantity"},
                {"name": "損益", "id": "pnl"},
                {"name": "報酬率 %", "id": "return_pct"},
            ],
            data=[],
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#1e1e2f",
                "color": "#fff",
                "fontWeight": "bold",
            },
            style_cell={
                "backgroundColor": "#12121f",
                "color": "#ddd",
                "border": "1px solid #333",
                "textAlign": "center",
                "padding": "8px",
            },
            style_data_conditional=[
                {"if": {"filter_query": "{pnl} > 0"}, "color": "#26a69a"},
                {"if": {"filter_query": "{pnl} < 0"}, "color": "#ef5350"},
            ],
            sort_action="native",
            page_size=25,
        ),
    ])


def build_metrics_panel() -> html.Div:
    """Build metrics display panel."""
    metric_ids = [
        ("總報酬率", "metric-total-return"),
        ("年化報酬率", "metric-annual-return"),
        ("Sharpe Ratio", "metric-sharpe"),
        ("最大回撤", "metric-max-dd"),
        ("勝率", "metric-win-rate"),
        ("獲利因子", "metric-profit-factor"),
        ("交易次數", "metric-trade-count"),
        ("平均報酬", "metric-avg-return"),
        ("做多次數", "metric-long-count"),
        ("做空次數", "metric-short-count"),
    ]

    return html.Div(
        [build_metric_card(label, "--", card_id) for label, card_id in metric_ids],
        style={
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "12px",
            "padding": "20px",
        },
    )


def _tab_style():
    return {
        "backgroundColor": "#161625",
        "color": "#888",
        "borderBottom": "2px solid #333",
        "padding": "10px 20px",
    }


def _tab_selected():
    return {
        "backgroundColor": "#1e1e2f",
        "color": "#fff",
        "borderBottom": "2px solid #4CAF50",
        "padding": "10px 20px",
    }
