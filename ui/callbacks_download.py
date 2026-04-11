from dash import Input, Output, State, callback, html, no_update, dcc
import plotly.graph_objects as go
import pandas as pd
import io

from data.downloader import DataDownloader


def register_download_callbacks(app):
    """Register all data download callbacks."""

    # Toggle yfinance / TW sections based on source
    @app.callback(
        Output("dl-yfinance-section", "style"),
        Output("dl-tw-section", "style"),
        Input("dl-source", "value"),
    )
    def toggle_source_sections(source):
        if source == "yfinance":
            return {"display": "block"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block"}

    # Quick-select fills symbol input (yfinance)
    @app.callback(
        Output("dl-symbol-input", "value"),
        Input("dl-quick-select", "value"),
        prevent_initial_call=True,
    )
    def fill_yf_symbol(symbol):
        return symbol or ""

    # Quick-select fills TW stock ID
    @app.callback(
        Output("dl-tw-stock-id", "value"),
        Input("dl-tw-quick-select", "value"),
        prevent_initial_call=True,
    )
    def fill_tw_symbol(stock_id):
        return stock_id or ""

    # Preview data
    @app.callback(
        Output("dl-preview-chart", "figure"),
        Output("dl-preview-table", "columns"),
        Output("dl-preview-table", "data"),
        Output("dl-data-store", "data"),
        Output("dl-status", "children", allow_duplicate=True),
        Output("dl-info-card", "children"),
        Input("dl-preview-btn", "n_clicks"),
        State("dl-source", "value"),
        State("dl-symbol-input", "value"),
        State("dl-tw-stock-id", "value"),
        State("dl-date-range", "start_date"),
        State("dl-date-range", "end_date"),
        State("dl-interval", "value"),
        prevent_initial_call=True,
    )
    def preview_data(n_clicks, source, yf_symbol, tw_stock_id, start_date, end_date, interval):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update

        try:
            if source == "yfinance":
                if not yf_symbol:
                    return no_update, no_update, no_update, no_update, "請輸入標的代碼", no_update
                df = DataDownloader.from_yfinance(yf_symbol, start_date, end_date, interval)
                symbol_display = yf_symbol
                info = DataDownloader.get_symbol_info(yf_symbol)
            else:
                if not tw_stock_id:
                    return no_update, no_update, no_update, no_update, "請輸入股票代碼", no_update
                start_dt = pd.Timestamp(start_date)
                end_dt = pd.Timestamp(end_date)
                market = "twse" if source == "twse" else "tpex"
                df = DataDownloader.download_tw_range(
                    tw_stock_id,
                    start_dt.year, start_dt.month,
                    end_dt.year, end_dt.month,
                    market=market,
                )
                symbol_display = tw_stock_id
                source_label = "證交所" if source == "twse" else "櫃買中心"
                info = {"name": tw_stock_id, "type": "Stock", "currency": "TWD", "exchange": source_label}

            # Build preview chart (candlestick)
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
            )])
            fig.update_layout(
                template="plotly_dark",
                title=f"{symbol_display} - {len(df)} 根 K 棒",
                xaxis_rangeslider_visible=False,
                height=400,
                margin=dict(l=50, r=20, t=40, b=30),
            )

            # Table data (show latest 50 rows)
            table_df = df.tail(50).copy()
            table_df = table_df.round(2)
            table_df.index = table_df.index.strftime("%Y-%m-%d")
            table_df = table_df.reset_index()
            table_df.columns = ["日期", "開盤", "最高", "最低", "收盤", "成交量"]

            columns = [{"name": c, "id": c} for c in table_df.columns]
            data = table_df.to_dict("records")

            # Store full data as JSON
            store = df.reset_index().to_json(date_format="iso")

            status = f"已載入 {symbol_display}：{len(df)} 筆資料 ({df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')})"

            # Info card
            info_card = html.Div([
                html.Span(f"📊 {info['name']}", style={"fontWeight": "bold", "marginRight": "16px"}),
                html.Span(f"類型: {info['type']}", style={"marginRight": "16px"}),
                html.Span(f"幣別: {info['currency']}", style={"marginRight": "16px"}),
                html.Span(f"交易所: {info['exchange']}"),
            ], style={
                "backgroundColor": "#1e1e2f",
                "borderRadius": "8px",
                "padding": "10px 16px",
                "color": "#ddd",
                "fontSize": "14px",
            })

            return fig, columns, data, store, status, info_card

        except Exception as e:
            empty_fig = go.Figure()
            empty_fig.update_layout(template="plotly_dark", height=400)
            return empty_fig, no_update, no_update, no_update, f"錯誤: {str(e)}", no_update

    # Download CSV — save to project data/csv/ folder
    @app.callback(
        Output("dl-csv-download", "data"),
        Input("dl-download-btn", "n_clicks"),
        State("dl-data-store", "data"),
        State("dl-source", "value"),
        State("dl-symbol-input", "value"),
        State("dl-tw-stock-id", "value"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, store_data, source, yf_symbol, tw_stock_id):
        import os
        if not n_clicks or not store_data:
            return no_update

        df = pd.read_json(io.StringIO(store_data))
        if "Date" in df.columns:
            df = df.set_index("Date")

        symbol = yf_symbol if source == "yfinance" else tw_stock_id
        filename = f"{symbol}_{df.index[0].strftime('%Y%m%d')}_{df.index[-1].strftime('%Y%m%d')}.csv"

        # Save to project data/csv/ folder
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "csv")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        df.to_csv(save_path)

        return no_update

    # Download CSV — show toast + start timer
    @app.callback(
        Output("dl-download-status", "children"),
        Output("dl-download-status", "style"),
        Output("dl-toast-timer", "disabled"),
        Output("dl-toast-timer", "n_intervals"),
        Input("dl-download-btn", "n_clicks"),
        State("dl-data-store", "data"),
        State("dl-source", "value"),
        State("dl-symbol-input", "value"),
        State("dl-tw-stock-id", "value"),
        prevent_initial_call=True,
    )
    def download_csv_status(n_clicks, store_data, source, yf_symbol, tw_stock_id):
        import os
        show_style = {
            "position": "fixed", "top": "8px", "right": "20px",
            "backgroundColor": "#1e1e2f", "borderRadius": "8px",
            "padding": "10px 18px", "zIndex": "9999",
            "border": "1px solid #333", "fontSize": "14px",
            "display": "block",
        }
        if not n_clicks:
            return no_update, no_update, no_update, no_update
        if not store_data:
            return "請先預覽資料再下載", show_style, False, 0

        df = pd.read_json(io.StringIO(store_data))
        if "Date" in df.columns:
            df = df.set_index("Date")

        symbol = yf_symbol if source == "yfinance" else tw_stock_id
        filename = f"{symbol}_{df.index[0].strftime('%Y%m%d')}_{df.index[-1].strftime('%Y%m%d')}.csv"
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "csv")
        save_path = os.path.join(save_dir, filename)

        content = html.Div([
            html.Div([
                html.Span("CSV 下載完成! ", style={"color": "#4CAF50", "fontWeight": "bold"}),
                html.Span(f"{len(df)} 筆資料", style={"color": "#aaa"}),
            ]),
            html.Div(
                f"儲存位置: {save_path}",
                style={"color": "#888", "fontSize": "11px", "marginTop": "4px"},
            ),
        ])
        return content, show_style, False, 0

    # Hide toast after timer fires
    @app.callback(
        Output("dl-download-status", "style", allow_duplicate=True),
        Output("dl-toast-timer", "disabled", allow_duplicate=True),
        Input("dl-toast-timer", "n_intervals"),
        prevent_initial_call=True,
    )
    def hide_toast(n_intervals):
        if n_intervals and n_intervals >= 1:
            hide_style = {
                "position": "fixed", "top": "8px", "right": "20px",
                "display": "none",
            }
            return hide_style, True
        return no_update, no_update

    # Send to backtest — save CSV first, then switch tab with filename
    @app.callback(
        Output("downloaded-csv-store", "data"),
        Output("selected-symbols-store", "data", allow_duplicate=True),
        Output("main-tabs", "value", allow_duplicate=True),
        Input("dl-to-backtest-btn", "n_clicks"),
        State("dl-source", "value"),
        State("dl-symbol-input", "value"),
        State("dl-tw-stock-id", "value"),
        State("dl-data-store", "data"),
        prevent_initial_call=True,
    )
    def dl_to_backtest(n_clicks, source, yf_symbol, tw_stock_id, store_data):
        import os
        if not n_clicks or not store_data:
            return no_update, no_update, no_update

        if source == "yfinance" and yf_symbol:
            symbol = yf_symbol
        elif tw_stock_id:
            symbol = tw_stock_id
        else:
            return no_update, no_update, no_update

        # Save data to data/csv/ folder (if not already saved)
        df = pd.read_json(io.StringIO(store_data))
        if "Date" in df.columns:
            df = df.set_index("Date")

        filename = f"{symbol}_{df.index[0].strftime('%Y%m%d')}_{df.index[-1].strftime('%Y%m%d')}.csv"
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "csv")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
        if not os.path.exists(save_path):
            df.to_csv(save_path)

        # Pass filename to backtest page (triggers auto_switch_to_downloaded)
        csv_store = {"filename": filename, "symbol": symbol}
        return csv_store, symbol, "backtest"
