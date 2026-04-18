import base64
from dash import Input, Output, State, callback, no_update, ALL, dcc
import pandas as pd

from screener.fundamental import (
    get_fundamentals_batch, load_fundamentals_csv, format_tw_symbol,
)
from screener.tw_fundamental import get_tw_fundamentals, enrich_with_gross_margin
from screener.filter import FilterRule, screen
from config import SP500_SAMPLE, FUNDAMENTAL_FIELDS


def register_screener_callbacks(app):
    """Register all screener-related callbacks."""

    # Show/hide stock pool input fields
    @app.callback(
        Output("custom-symbols-container", "style"),
        Output("screener-csv-container", "style"),
        Input("stock-pool-select", "value"),
    )
    def toggle_pool_inputs(pool):
        custom_style = {"display": "block"} if pool == "custom" else {"display": "none"}
        csv_style = {"display": "block"} if pool == "csv" else {"display": "none"}
        return custom_style, csv_style



    # Run screener
    @app.callback(
        Output("screener-results-table", "columns"),
        Output("screener-results-table", "data"),
        Output("screener-data-store", "data"),
        Output("screener-status", "children"),
        Input("run-screener-btn", "n_clicks"),
        State("stock-pool-select", "value"),
        State("custom-symbols-input", "value"),
        State("screener-csv-upload", "contents"),
        State("screener-csv-upload", "filename"),
        State({"type": "screener-field", "index": ALL}, "value"),
        State({"type": "screener-op", "index": ALL}, "value"),
        State({"type": "screener-val", "index": ALL}, "value"),
        prevent_initial_call=True,
    )
    def run_screener(
        n_clicks, pool, custom_symbols, csv_contents, csv_filename,
        filter_fields, filter_ops, filter_vals,
    ):
        if not n_clicks:
            return no_update, no_update, no_update, no_update

        try:
            # Get fundamentals data
            if pool == "csv" and csv_contents:
                content_type, content_string = csv_contents.split(",")
                decoded = base64.b64decode(content_string).decode("utf-8")
                df = load_fundamentals_csv(content=decoded)
            elif pool == "custom" and custom_symbols:
                raw = [s.strip() for s in custom_symbols.replace("，", ",").split(",") if s.strip()]
                if not raw:
                    return no_update, no_update, no_update, "請輸入股票代碼"
                # Auto-append .TW for purely numeric codes
                symbols = [format_tw_symbol(s) if s.isdigit() else s for s in raw]
                df = get_fundamentals_batch(symbols)
            elif pool in ("tw_twse", "tw_tpex", "tw_all"):
                market_map = {"tw_twse": "twse", "tw_tpex": "tpex", "tw_all": "all"}
                df = get_tw_fundamentals(market=market_map[pool])
                if df.empty:
                    return no_update, no_update, no_update, "無法取得台股資料，請檢查網路"
            else:  # sp500_sample
                df = get_fundamentals_batch(SP500_SAMPLE)

            if df.empty:
                return no_update, no_update, no_update, "無法取得資料"

            # Build filter rules
            rules = []
            for field, op, val in zip(
                filter_fields or [], filter_ops or [], filter_vals or []
            ):
                if field and op and val is not None:
                    rules.append(FilterRule(field=field, operator=op, value=float(val)))

            # Apply filters
            if rules:
                filtered = screen(df, rules)
            else:
                filtered = df

            # For Taiwan stocks: enrich filtered result with MOPS gross margin
            # (only for filtered subset to keep requests manageable)
            if pool in ("tw_twse", "tw_tpex", "tw_all") and not filtered.empty:
                filtered = enrich_with_gross_margin(filtered)

            # Format for display
            display_cols = ["Symbol", "Name"] + [
                k for k in FUNDAMENTAL_FIELDS.keys() if k in filtered.columns
            ]
            display_df = filtered[[c for c in display_cols if c in filtered.columns]]

            # Round numeric columns
            for col in display_df.columns:
                if col not in ["Symbol", "Name"] and display_df[col].dtype in ["float64", "float32"]:
                    display_df[col] = display_df[col].round(4)

            columns = [{"name": _get_col_label(c), "id": c} for c in display_df.columns]
            data = display_df.to_dict("records")

            status = f"找到 {len(filtered)} 檔符合條件的股票 (共 {len(df)} 檔)"
            store = display_df.to_json(date_format="iso")

            return columns, data, store, status

        except Exception as e:
            return no_update, no_update, no_update, f"錯誤: {str(e)}"

    # Send selected symbols to backtest
    @app.callback(
        Output("selected-symbols-store", "data"),
        Output("main-tabs", "value"),
        Input("send-to-backtest-btn", "n_clicks"),
        State("screener-results-table", "data"),
        State("screener-results-table", "selected_rows"),
        prevent_initial_call=True,
    )
    def send_to_backtest(n_clicks, table_data, selected_rows):
        if not n_clicks or not table_data or not selected_rows:
            return no_update, no_update

        symbols = [table_data[i]["Symbol"] for i in selected_rows if i < len(table_data)]
        if symbols:
            # Send first selected symbol to backtest (single-symbol backtest)
            return symbols[0], "backtest"
        return no_update, no_update


    # Download screener results as CSV
    @app.callback(
        Output("screener-download", "data"),
        Input("download-screener-btn", "n_clicks"),
        State("screener-data-store", "data"),
        prevent_initial_call=True,
    )
    def download_screener_csv(n_clicks, store_json):
        if not n_clicks or not store_json:
            return no_update
        df = pd.read_json(store_json)
        return dcc.send_data_frame(df.to_csv, "screener_results.csv", index=False)


def _get_col_label(col: str) -> str:
    """Get display label for column name."""
    labels = {
        "Symbol": "代碼",
        "Name": "名稱",
        **{k: v["label"] for k, v in FUNDAMENTAL_FIELDS.items()},
    }
    return labels.get(col, col)
