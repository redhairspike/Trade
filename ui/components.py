from dash import html, dcc, dash_table
from config import INDICATOR_DEFAULTS, OPERATORS, FUNDAMENTAL_FIELDS
from data.downloader import FUTURES_SYMBOLS, TW_POPULAR_STOCKS


def build_metric_card(label: str, value: str, card_id: str = "") -> html.Div:
    """Build a single metric display card."""
    return html.Div(
        [
            html.P(label, style={"margin": "0", "fontSize": "12px", "color": "#888"}),
            html.H4(value, id=card_id, style={"margin": "4px 0", "color": "#fff"}),
        ],
        style={
            "backgroundColor": "#1e1e2f",
            "borderRadius": "8px",
            "padding": "12px 16px",
            "minWidth": "140px",
            "textAlign": "center",
        },
    )


def _param_slot(prefix: str, index: int, slot: int) -> html.Div:
    """Build a single param slot (label + number input), initially hidden."""
    _input_style = {
        "width": "58px",
        "backgroundColor": "#1a1a2e",
        "color": "#ddd",
        "border": "1px solid #444",
        "borderRadius": "4px",
        "padding": "3px 6px",
        "fontSize": "12px",
    }
    return html.Div(
        [
            html.Label(
                "",
                id={"type": f"{prefix}-pk{slot}", "index": index},
                style={"color": "#999", "fontSize": "11px", "marginRight": "2px", "whiteSpace": "nowrap"},
            ),
            dcc.Input(
                id={"type": f"{prefix}-pv{slot}", "index": index},
                type="number",
                step="any",
                style=_input_style,
            ),
        ],
        id={"type": f"{prefix}-ps{slot}", "index": index},
        style={"display": "none", "alignItems": "center", "gap": "2px"},
    )


def build_rule_row(prefix: str, index: int) -> html.Div:
    """Build a single rule row (indicator + field + operator + value) with param detail row."""
    indicator_options = [{"label": k, "value": k} for k in INDICATOR_DEFAULTS.keys()]
    operator_options = [{"label": op, "value": op} for op in OPERATORS]

    return html.Div(
        [
            # Row 1: indicator + field (full width, each flex:1)
            html.Div(
                [
                    dcc.Dropdown(
                        id={"type": f"{prefix}-indicator", "index": index},
                        options=indicator_options,
                        placeholder="指標",
                        style={"flex": "1", "minWidth": "0"},
                    ),
                    dcc.Dropdown(
                        id={"type": f"{prefix}-field", "index": index},
                        options=[],
                        placeholder="欄位",
                        style={"flex": "1", "minWidth": "0"},
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "6px",
                    "alignItems": "center",
                },
            ),
            # Row 2: operator + value
            html.Div(
                [
                    dcc.Dropdown(
                        id={"type": f"{prefix}-operator", "index": index},
                        options=operator_options,
                        placeholder="條件",
                        style={"flex": "1", "minWidth": "0"},
                    ),
                    dcc.Input(
                        id={"type": f"{prefix}-value", "index": index},
                        type="text",
                        placeholder="值",
                        style={"width": "80px", "flexShrink": "0"},
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "6px",
                    "alignItems": "center",
                    "marginTop": "4px",
                },
            ),
            # Row 3: param detail slots (up to 3, shown/hidden by callback)
            html.Div(
                [
                    _param_slot(prefix, index, 0),
                    _param_slot(prefix, index, 1),
                    _param_slot(prefix, index, 2),
                ],
                style={
                    "display": "flex",
                    "gap": "10px",
                    "marginTop": "3px",
                    "marginLeft": "4px",
                    "minHeight": "0px",
                },
            ),
        ],
        style={"marginBottom": "10px"},
    )


def build_sidebar() -> html.Div:
    """Build the backtest configuration sidebar."""
    return html.Div(
        [
            html.H3("回測設定", style={"color": "#fff", "marginTop": "0"}),

            # Market selection
            html.Label("資料來源", style={"color": "#ccc"}),
            dcc.Dropdown(
                id="market-select",
                options=[
                    {"label": "國際市場 (yfinance)", "value": "yfinance"},
                    {"label": "已下載資料", "value": "downloaded"},
                    {"label": "CSV 匯入", "value": "csv"},
                ],
                value="yfinance",
                style={"marginBottom": "10px"},
            ),

            # Downloaded data file selector
            html.Div(
                id="downloaded-data-section",
                children=[
                    html.Label("選擇已下載檔案", style={"color": "#ccc"}),
                    dcc.Dropdown(
                        id="downloaded-file-select",
                        options=[],
                        placeholder="選擇 CSV 檔案...",
                        style={"marginBottom": "6px"},
                    ),
                    html.Div(id="downloaded-data-info", style={"fontSize": "12px"}),
                ],
                style={"display": "none", "marginBottom": "10px"},
            ),

            # Symbol input
            html.Div(
                id="symbol-input-container",
                children=[
                    html.Label("標的代碼", style={"color": "#ccc"}),
                    dcc.Input(
                        id="symbol-input",
                        type="text",
                        value="AAPL",
                        placeholder="例: AAPL, 2330.TW",
                        style={"width": "100%", "marginBottom": "10px"},
                    ),
                ],
            ),

            # CSV upload
            html.Div(
                id="csv-upload-container",
                children=[
                    dcc.Upload(
                        id="csv-upload",
                        children=html.Div(["拖放或 ", html.A("選擇 CSV 檔案")]),
                        style={
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "borderColor": "#555",
                            "textAlign": "center",
                            "padding": "10px",
                            "color": "#aaa",
                            "marginBottom": "10px",
                        },
                    ),
                ],
                style={"display": "none"},
            ),

            # Date range
            html.Label("日期範圍", style={"color": "#ccc"}),
            dcc.DatePickerRange(
                id="date-range",
                start_date="2023-01-01",
                end_date="2024-12-31",
                style={"marginBottom": "10px"},
            ),

            # Interval
            html.Label("K 線週期", style={"color": "#ccc"}),
            dcc.Dropdown(
                id="interval-select",
                options=[
                    {"label": "日線", "value": "1d"},
                    {"label": "週線", "value": "1wk"},
                    {"label": "月線", "value": "1mo"},
                ],
                value="1d",
                style={"marginBottom": "14px"},
            ),

            html.Hr(style={"borderColor": "#444"}),

            # Strategy direction
            html.Label("方向", style={"color": "#ccc"}),
            dcc.Dropdown(
                id="direction-select",
                options=[
                    {"label": "做多 (Long)", "value": "long"},
                    {"label": "做空 (Short)", "value": "short"},
                ],
                value="long",
                style={"marginBottom": "10px"},
            ),

            # --- MA Filter Section ---
            html.Label("均線濾網", style={"color": "#ccc", "fontWeight": "bold"}),

            # MA Position Filter
            html.Div([
                dcc.Checklist(
                    id="ma-position-filter-enable",
                    options=[{"label": " 均線位置濾網", "value": "enabled"}],
                    value=[],
                    style={"color": "#ddd", "fontSize": "13px"},
                ),
                html.Div(
                    id="ma-position-filter-params",
                    children=[
                        html.Div([
                            html.Span("收盤價在 ", style={"color": "#aaa", "fontSize": "12px"}),
                            dcc.Dropdown(
                                id="ma-position-filter-type",
                                options=[
                                    {"label": "MA", "value": "MA"},
                                    {"label": "EMA", "value": "EMA"},
                                ],
                                value="MA",
                                style={"width": "70px", "display": "inline-block"},
                                clearable=False,
                            ),
                            dcc.Input(
                                id="ma-position-filter-period",
                                type="number",
                                value=20,
                                min=2,
                                style={"width": "50px", "marginLeft": "4px"},
                            ),
                            html.Span(" 之上做多 / 之下做空", style={"color": "#aaa", "fontSize": "12px", "marginLeft": "4px"}),
                        ], style={"display": "flex", "alignItems": "center", "gap": "4px", "marginTop": "4px"}),
                    ],
                    style={"display": "none", "marginLeft": "20px"},
                ),
            ], style={"marginBottom": "6px"}),

            # MA Direction Filter
            html.Div([
                dcc.Checklist(
                    id="ma-direction-filter-enable",
                    options=[{"label": " 均線方向濾網", "value": "enabled"}],
                    value=[],
                    style={"color": "#ddd", "fontSize": "13px"},
                ),
                html.Div(
                    id="ma-direction-filter-params",
                    children=[
                        html.Div([
                            dcc.Dropdown(
                                id="ma-direction-filter-type",
                                options=[
                                    {"label": "MA", "value": "MA"},
                                    {"label": "EMA", "value": "EMA"},
                                ],
                                value="MA",
                                style={"width": "70px", "display": "inline-block"},
                                clearable=False,
                            ),
                            dcc.Input(
                                id="ma-direction-filter-period",
                                type="number",
                                value=20,
                                min=2,
                                style={"width": "50px", "marginLeft": "4px"},
                            ),
                            html.Span(" 上彎做多 / 下彎做空", style={"color": "#aaa", "fontSize": "12px", "marginLeft": "4px"}),
                        ], style={"display": "flex", "alignItems": "center", "gap": "4px", "marginTop": "4px"}),
                    ],
                    style={"display": "none", "marginLeft": "20px"},
                ),
            ], style={"marginBottom": "10px"}),

            html.Hr(style={"borderColor": "#444"}),

            # Entry rules
            html.Div(
                [
                    html.Label("進場條件 (AND)", style={"color": "#ccc"}),
                    html.Button("+", id="add-entry-rule", n_clicks=0,
                                style={"marginLeft": "8px", "fontSize": "12px"}),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "6px"},
            ),
            html.Div(id="entry-rules-container", children=[build_rule_row("entry", 0)]),

            # Exit rules
            html.Div(
                [
                    html.Label("出場條件 (OR)", style={"color": "#ccc"}),
                    html.Button("+", id="add-exit-rule", n_clicks=0,
                                style={"marginLeft": "8px", "fontSize": "12px"}),
                ],
                style={"display": "flex", "alignItems": "center", "marginTop": "10px", "marginBottom": "6px"},
            ),
            html.Div(id="exit-rules-container", children=[build_rule_row("exit", 0)]),

            html.Hr(style={"borderColor": "#444"}),

            # Risk parameters
            html.Label("風控設定", style={"color": "#ccc", "fontWeight": "bold"}),

            html.Div([
                html.Div([
                    html.Label("停損 %", style={"color": "#aaa", "fontSize": "12px"}),
                    dcc.Input(id="stop-loss-input", type="number", value=None,
                              placeholder="例: 5", style={"width": "100%"}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("停利 %", style={"color": "#aaa", "fontSize": "12px"}),
                    dcc.Input(id="take-profit-input", type="number", value=None,
                              placeholder="例: 10", style={"width": "100%"}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "8px", "marginBottom": "8px", "marginTop": "6px"}),

            html.Div([
                html.Div([
                    html.Label("部位比例 %", style={"color": "#aaa", "fontSize": "12px"}),
                    dcc.Input(id="position-size-input", type="number", value=100,
                              style={"width": "100%"}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("初始資金", style={"color": "#aaa", "fontSize": "12px"}),
                    dcc.Input(id="capital-input", type="number", value=1000000,
                              style={"width": "100%"}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "8px", "marginBottom": "8px"}),

            html.Div([
                html.Div([
                    html.Label("手續費 %", style={"color": "#aaa", "fontSize": "12px"}),
                    dcc.Input(id="commission-input", type="number", value=0.1,
                              style={"width": "100%"}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("滑價 %", style={"color": "#aaa", "fontSize": "12px"}),
                    dcc.Input(id="slippage-input", type="number", value=0.05,
                              style={"width": "100%"}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "8px", "marginBottom": "14px"}),

            # Run button
            html.Button(
                "執行回測",
                id="run-backtest-btn",
                n_clicks=0,
                style={
                    "width": "100%",
                    "padding": "12px",
                    "fontSize": "16px",
                    "backgroundColor": "#4CAF50",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "6px",
                    "cursor": "pointer",
                    "fontWeight": "bold",
                },
            ),

            html.Div(id="backtest-status", style={"color": "#ff6b6b", "marginTop": "8px", "fontSize": "13px"}),
        ],
        style={
            "width": "320px",
            "minWidth": "320px",
            "padding": "16px",
            "backgroundColor": "#161625",
            "overflowY": "auto",
            "height": "100vh",
            "boxSizing": "border-box",
        },
    )


def build_screener_panel() -> html.Div:
    """Build the stock screener panel."""
    # Group fields by 'group' key, with disabled separator headers
    field_options = []
    current_group = None
    for k, v in FUNDAMENTAL_FIELDS.items():
        grp = v.get("group", "")
        if grp != current_group:
            current_group = grp
            field_options.append({"label": f"── {grp} ──", "value": f"__sep_{grp}", "disabled": True})
        field_options.append({"label": v["label"], "value": k})

    operator_options = [
        {"label": op, "value": op}
        for op in [">", "<", ">=", "<="]
    ]

    return html.Div([
        html.H3("選股篩選", style={"color": "#fff", "marginTop": "0"}),

        # Stock pool selection
        html.Label("股票池", style={"color": "#ccc"}),
        dcc.Dropdown(
            id="stock-pool-select",
            options=[
                {"label": "── 美股 ──", "value": "", "disabled": True},
                {"label": "美股範例 (30檔)", "value": "sp500_sample"},
                {"label": "── 台股 ──", "value": "", "disabled": True},
                {"label": "台股上市 (TWSE)", "value": "tw_twse"},
                {"label": "台股上櫃 (TPEx)", "value": "tw_tpex"},
                {"label": "台股全部 (上市+上櫃)", "value": "tw_all"},
                {"label": "── 自訂 ──", "value": "", "disabled": True},
                {"label": "自訂清單", "value": "custom"},
                {"label": "CSV 匯入", "value": "csv"},
            ],
            value="sp500_sample",
            style={"marginBottom": "10px"},
        ),

        # Custom symbol list
        html.Div(
            id="custom-symbols-container",
            children=[
                dcc.Textarea(
                    id="custom-symbols-input",
                    placeholder="輸入股票代碼，以逗號分隔\n美股: AAPL, MSFT\n台股: 2330, 2317 (自動補 .TW)",
                    style={"width": "100%", "height": "70px", "marginBottom": "10px"},
                ),
            ],
            style={"display": "none"},
        ),

        # CSV upload for fundamentals
        html.Div(
            id="screener-csv-container",
            children=[
                dcc.Upload(
                    id="screener-csv-upload",
                    children=html.Div(["拖放或 ", html.A("選擇基本面 CSV")]),
                    style={
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "borderColor": "#555",
                        "textAlign": "center",
                        "padding": "10px",
                        "color": "#aaa",
                        "marginBottom": "10px",
                    },
                ),
            ],
            style={"display": "none"},
        ),

        # Filter rules
        html.Label("篩選條件", style={"color": "#ccc"}),
        html.Div(
            id="screener-rules-container",
            children=[
                html.Div([
                    dcc.Dropdown(
                        id={"type": "screener-field", "index": i},
                        options=field_options,
                        placeholder="指標",
                        style={"width": "160px"},
                    ),
                    dcc.Dropdown(
                        id={"type": "screener-op", "index": i},
                        options=operator_options,
                        placeholder="條件",
                        style={"width": "80px"},
                    ),
                    dcc.Input(
                        id={"type": "screener-val", "index": i},
                        type="number",
                        placeholder="值",
                        style={"width": "80px"},
                    ),
                ], style={"display": "flex", "gap": "6px", "marginBottom": "6px"})
                for i in range(3)
            ],
        ),

        html.Div([
            html.Button("篩選", id="run-screener-btn", n_clicks=0, style={
                "padding": "8px 20px", "backgroundColor": "#2196F3", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold", "marginRight": "8px",
            }),
            html.Button("補毛利率", id="enrich-grossmargin-btn", n_clicks=0, style={
                "padding": "8px 20px", "backgroundColor": "#9C27B0", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold", "marginRight": "8px",
            }),
            html.Button("⬇ 下載 CSV", id="download-screener-btn", n_clicks=0, style={
                "padding": "8px 20px", "backgroundColor": "#4CAF50", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold", "marginRight": "8px",
            }),
            html.Button("送入回測 →", id="send-to-backtest-btn", n_clicks=0, style={
                "padding": "8px 20px", "backgroundColor": "#FF9800", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold",
            }),
            dcc.Download(id="screener-download"),
        ], style={"marginTop": "10px", "marginBottom": "10px"}),

        # Loading wrapper — shows spinner while screener is running
        dcc.Loading(
            type="circle",
            color="#2196F3",
            children=[
                html.Div(id="screener-status", style={"color": "#aaa", "fontSize": "13px", "marginBottom": "10px"}),
                dash_table.DataTable(
            id="screener-results-table",
            columns=[],
            data=[],
            row_selectable="multi",
            selected_rows=[],
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
            style_data_conditional=[{
                "if": {"state": "selected"},
                "backgroundColor": "#2a2a4a",
                "border": "1px solid #4CAF50",
            }],
            sort_action="native",
            page_size=20,
        ),
            ],  # end dcc.Loading children
        ),      # end dcc.Loading
    ], style={"padding": "20px"})


def build_download_panel() -> html.Div:
    """Build the data download panel."""
    # Futures quick-select options
    futures_options = [
        {"label": f"{sym} - {name}", "value": sym}
        for sym, name in FUTURES_SYMBOLS.items()
    ]
    tw_options = [
        {"label": f"{code} {name}", "value": code}
        for code, name in TW_POPULAR_STOCKS.items()
    ]

    return html.Div([
        html.H3("資料下載", style={"color": "#fff", "marginTop": "0"}),

        # Source selection
        html.Div([
            html.Div([
                html.Label("資料來源", style={"color": "#ccc", "fontWeight": "bold"}),
                dcc.RadioItems(
                    id="dl-source",
                    options=[
                        {"label": " yfinance (美股/期貨/加密貨幣)", "value": "yfinance"},
                        {"label": " TWSE 台灣證交所 (上市)", "value": "twse"},
                        {"label": " TPEx 櫃買中心 (上櫃)", "value": "tpex"},
                    ],
                    value="yfinance",
                    style={"color": "#ddd", "marginBottom": "14px"},
                    labelStyle={"display": "block", "marginBottom": "6px"},
                ),
            ], style={"flex": "1"}),
        ]),

        html.Hr(style={"borderColor": "#444"}),

        # yfinance section
        html.Div(
            id="dl-yfinance-section",
            children=[
                html.Label("快速選擇", style={"color": "#ccc"}),
                dcc.Dropdown(
                    id="dl-quick-select",
                    options=[
                        {"label": "── 期貨 ──", "value": "", "disabled": True},
                        *futures_options,
                    ],
                    placeholder="選擇常用標的...",
                    style={"marginBottom": "10px"},
                ),
                html.Label("或輸入代碼", style={"color": "#ccc"}),
                dcc.Input(
                    id="dl-symbol-input",
                    type="text",
                    placeholder="例: AAPL, ES=F, 2330.TW, BTC-USD",
                    style={"width": "100%", "marginBottom": "10px"},
                ),
                html.Label("K 線週期", style={"color": "#ccc"}),
                dcc.Dropdown(
                    id="dl-interval",
                    options=[
                        {"label": "1 分鐘", "value": "1m"},
                        {"label": "5 分鐘", "value": "5m"},
                        {"label": "15 分鐘", "value": "15m"},
                        {"label": "30 分鐘", "value": "30m"},
                        {"label": "1 小時", "value": "1h"},
                        {"label": "日線", "value": "1d"},
                        {"label": "週線", "value": "1wk"},
                        {"label": "月線", "value": "1mo"},
                    ],
                    value="1d",
                    style={"marginBottom": "10px"},
                ),
            ],
        ),

        # TWSE/TPEx section
        html.Div(
            id="dl-tw-section",
            children=[
                html.Label("快速選擇", style={"color": "#ccc"}),
                dcc.Dropdown(
                    id="dl-tw-quick-select",
                    options=tw_options,
                    placeholder="選擇常用台股...",
                    style={"marginBottom": "10px"},
                ),
                html.Label("或輸入股票代碼", style={"color": "#ccc"}),
                dcc.Input(
                    id="dl-tw-stock-id",
                    type="text",
                    placeholder="例: 2330",
                    style={"width": "100%", "marginBottom": "10px"},
                ),
            ],
            style={"display": "none"},
        ),

        # Date range
        html.Label("日期範圍", style={"color": "#ccc"}),
        html.Div([
            dcc.DatePickerRange(
                id="dl-date-range",
                start_date="2024-01-01",
                end_date="2025-12-31",
                style={"marginBottom": "10px"},
            ),
        ]),

        # Action buttons
        html.Div([
            html.Button("預覽資料", id="dl-preview-btn", n_clicks=0, style={
                "padding": "10px 24px", "backgroundColor": "#2196F3", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold", "marginRight": "10px",
            }),
            html.Button("下載 CSV", id="dl-download-btn", n_clicks=0, style={
                "padding": "10px 24px", "backgroundColor": "#4CAF50", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold", "marginRight": "10px",
            }),
            html.Button("送入回測 →", id="dl-to-backtest-btn", n_clicks=0, style={
                "padding": "10px 24px", "backgroundColor": "#FF9800", "color": "white",
                "border": "none", "borderRadius": "4px", "cursor": "pointer",
                "fontWeight": "bold",
            }),
        ], style={"marginTop": "14px", "marginBottom": "10px"}),

        html.Div(id="dl-status", style={
            "color": "#aaa", "fontSize": "13px", "marginTop": "8px", "marginBottom": "10px",
        }),

        # Symbol info card
        html.Div(id="dl-info-card", style={"marginBottom": "14px"}),

        # Preview chart
        dcc.Loading(
            id="dl-chart-loading",
            children=[
                dcc.Graph(id="dl-preview-chart", style={"height": "400px"}),
            ],
            type="circle",
        ),

        # Preview table
        html.Div(id="dl-preview-table-container", children=[
            dash_table.DataTable(
                id="dl-preview-table",
                columns=[],
                data=[],
                style_table={"overflowX": "auto", "maxHeight": "300px", "overflowY": "auto"},
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
                    "padding": "6px",
                    "minWidth": "80px",
                },
                sort_action="native",
                page_size=15,
            ),
        ]),

    ], style={"padding": "20px", "maxWidth": "1200px", "margin": "0 auto"})
