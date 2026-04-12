import io
import base64
from dash import Input, Output, State, callback, html, no_update, ALL, ctx
import pandas as pd

from data.loader import DataLoader
from strategy.signal import Signal, Rule, MAFilter
from strategy.strategy import Strategy
from engine.portfolio import Portfolio
from engine.backtest import BacktestEngine
from indicators.base import get_indicator_fields, INDICATOR_REGISTRY
from ui.layout import (
    build_chart_panel, build_trades_panel, build_metrics_panel,
)
from ui.chart import build_candlestick_chart, build_volume_chart
from ui.components import build_rule_row
from config import INDICATOR_DEFAULTS


def register_callbacks(app):
    """Register all backtest-related callbacks."""

    # Tab visibility switching (all tabs always in DOM)
    @app.callback(
        Output("tab-download", "style"),
        Output("tab-screener", "style"),
        Output("tab-backtest", "style"),
        Input("main-tabs", "value"),
    )
    def toggle_tabs(tab):
        show = {"display": "block"}
        hide = {"display": "none"}
        return (
            show if tab == "download" else hide,
            show if tab == "screener" else hide,
            show if tab == "backtest" else hide,
        )

    # Show/hide elements based on market selection
    @app.callback(
        Output("csv-upload-container", "style"),
        Output("symbol-input-container", "style"),
        Output("downloaded-data-section", "style"),
        Output("downloaded-file-select", "options"),
        Input("market-select", "value"),
    )
    def toggle_market_ui(market):
        import os
        csv_style = {"display": "block"} if market == "csv" else {"display": "none"}
        symbol_style = {"display": "none"} if market == "downloaded" else {"display": "block"}
        dl_style = {"display": "none"}
        file_options = []

        if market == "downloaded":
            dl_style = {"display": "block"}
            csv_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "csv")
            if os.path.isdir(csv_dir):
                files = sorted(
                    [f for f in os.listdir(csv_dir) if f.endswith(".csv")],
                    reverse=True,
                )
                file_options = [{"label": f, "value": f} for f in files]

        return csv_style, symbol_style, dl_style, file_options

    # Auto-fill symbol from screener/download selection
    @app.callback(
        Output("symbol-input", "value"),
        Input("selected-symbols-store", "data"),
        State("symbol-input", "value"),
    )
    def fill_symbol_from_screener(selected, current):
        if selected:
            return selected
        return current or "AAPL"

    # Auto-switch to "downloaded" and pre-select file when coming from download page
    @app.callback(
        Output("market-select", "value"),
        Output("downloaded-file-select", "value"),
        Input("downloaded-csv-store", "data"),
        State("market-select", "value"),
        prevent_initial_call=True,
    )
    def auto_switch_to_downloaded(dl_store, current_market):
        if dl_store and "filename" in dl_store:
            return "downloaded", dl_store["filename"]
        return no_update, no_update

    # Toggle MA position filter params visibility
    @app.callback(
        Output("ma-position-filter-params", "style"),
        Input("ma-position-filter-enable", "value"),
    )
    def toggle_ma_pos_filter(value):
        if value and "enabled" in value:
            return {"display": "block", "marginLeft": "20px"}
        return {"display": "none", "marginLeft": "20px"}

    # Toggle MA direction filter params visibility
    @app.callback(
        Output("ma-direction-filter-params", "style"),
        Input("ma-direction-filter-enable", "value"),
    )
    def toggle_ma_dir_filter(value):
        if value and "enabled" in value:
            return {"display": "block", "marginLeft": "20px"}
        return {"display": "none", "marginLeft": "20px"}

    # Dynamic entry rule rows
    @app.callback(
        Output("entry-rules-container", "children"),
        Input("add-entry-rule", "n_clicks"),
        State("entry-rules-container", "children"),
    )
    def add_entry_rule(n_clicks, children):
        if n_clicks and children:
            new_index = len(children)
            children.append(build_rule_row("entry", new_index))
        return children

    # Dynamic exit rule rows
    @app.callback(
        Output("exit-rules-container", "children"),
        Input("add-exit-rule", "n_clicks"),
        State("exit-rules-container", "children"),
    )
    def add_exit_rule(n_clicks, children):
        if n_clicks and children:
            new_index = len(children)
            children.append(build_rule_row("exit", new_index))
        return children

    # Update field dropdown and auto-fill params when indicator is selected
    @app.callback(
        Output({"type": "entry-field", "index": ALL}, "options"),
        Output({"type": "entry-param", "index": ALL}, "value"),
        Input({"type": "entry-indicator", "index": ALL}, "value"),
    )
    def update_entry_fields(indicators):
        field_results = []
        param_results = []
        for ind in indicators:
            if ind and ind in INDICATOR_REGISTRY:
                fields = get_indicator_fields(ind)
                field_results.append([{"label": f, "value": f} for f in fields])
                param_results.append(_format_default_params(ind))
            else:
                field_results.append([])
                param_results.append("")
        return field_results, param_results

    @app.callback(
        Output({"type": "exit-field", "index": ALL}, "options"),
        Output({"type": "exit-param", "index": ALL}, "value"),
        Input({"type": "exit-indicator", "index": ALL}, "value"),
    )
    def update_exit_fields(indicators):
        field_results = []
        param_results = []
        for ind in indicators:
            if ind and ind in INDICATOR_REGISTRY:
                fields = get_indicator_fields(ind)
                field_results.append([{"label": f, "value": f} for f in fields])
                param_results.append(_format_default_params(ind))
            else:
                field_results.append([])
                param_results.append("")
        return field_results, param_results

    # Run backtest
    @app.callback(
        Output("backtest-result-store", "data"),
        Output("backtest-status", "children"),
        Input("run-backtest-btn", "n_clicks"),
        State("market-select", "value"),
        State("symbol-input", "value"),
        State("date-range", "start_date"),
        State("date-range", "end_date"),
        State("interval-select", "value"),
        State("csv-upload", "contents"),
        State("csv-upload", "filename"),
        State("direction-select", "value"),
        State({"type": "entry-indicator", "index": ALL}, "value"),
        State({"type": "entry-field", "index": ALL}, "value"),
        State({"type": "entry-param", "index": ALL}, "value"),
        State({"type": "entry-operator", "index": ALL}, "value"),
        State({"type": "entry-value", "index": ALL}, "value"),
        State({"type": "exit-indicator", "index": ALL}, "value"),
        State({"type": "exit-field", "index": ALL}, "value"),
        State({"type": "exit-param", "index": ALL}, "value"),
        State({"type": "exit-operator", "index": ALL}, "value"),
        State({"type": "exit-value", "index": ALL}, "value"),
        State("stop-loss-input", "value"),
        State("take-profit-input", "value"),
        State("position-size-input", "value"),
        State("capital-input", "value"),
        State("commission-input", "value"),
        State("slippage-input", "value"),
        State("downloaded-file-select", "value"),
        # MA filter states
        State("ma-position-filter-enable", "value"),
        State("ma-position-filter-type", "value"),
        State("ma-position-filter-period", "value"),
        State("ma-direction-filter-enable", "value"),
        State("ma-direction-filter-type", "value"),
        State("ma-direction-filter-period", "value"),
        prevent_initial_call=True,
    )
    def run_backtest(
        n_clicks, market, symbol, start_date, end_date, interval,
        csv_contents, csv_filename,
        direction,
        entry_indicators, entry_fields, entry_params, entry_operators, entry_values,
        exit_indicators, exit_fields, exit_params, exit_operators, exit_values,
        stop_loss, take_profit, position_size, capital, commission, slippage,
        downloaded_file,
        ma_pos_enable, ma_pos_type, ma_pos_period,
        ma_dir_enable, ma_dir_type, ma_dir_period,
    ):
        if not n_clicks:
            return no_update, no_update

        try:
            # Load data
            if market == "downloaded" and downloaded_file:
                import os
                csv_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "csv")
                filepath = os.path.join(csv_dir, downloaded_file)
                df = DataLoader.from_csv(filepath)
            elif market == "downloaded":
                return no_update, "請選擇已下載的 CSV 檔案"
            elif market == "csv" and csv_contents:
                content_type, content_string = csv_contents.split(",")
                decoded = base64.b64decode(content_string).decode("utf-8")
                df = DataLoader.from_csv_content(decoded)
            else:
                df = DataLoader.from_yfinance(symbol, start_date, end_date, interval)

            # Build entry rules
            entry_rules = _build_rules(
                entry_indicators, entry_fields, entry_params,
                entry_operators, entry_values,
            )

            # Build exit rules
            exit_rules = _build_rules(
                exit_indicators, exit_fields, exit_params,
                exit_operators, exit_values,
            )

            if not entry_rules:
                return no_update, "請至少設定一個進場條件"

            # Build MA filters
            ma_position_filter = MAFilter(
                enabled=bool(ma_pos_enable and "enabled" in ma_pos_enable),
                period=int(ma_pos_period or 20),
                ma_type=ma_pos_type or "MA",
            )
            ma_direction_filter = MAFilter(
                enabled=bool(ma_dir_enable and "enabled" in ma_dir_enable),
                period=int(ma_dir_period or 20),
                ma_type=ma_dir_type or "MA",
            )

            # Build strategy
            signal = Signal(
                direction=direction,
                entry_rules=entry_rules,
                exit_rules=exit_rules,
                ma_position_filter=ma_position_filter,
                ma_direction_filter=ma_direction_filter,
            )

            sl_pct = stop_loss / 100 if stop_loss else None
            tp_pct = take_profit / 100 if take_profit else None
            pos_pct = (position_size or 100) / 100

            strategy = Strategy(signal, sl_pct, tp_pct, pos_pct)

            # Build portfolio
            portfolio = Portfolio(
                initial_capital=capital or 1_000_000,
                commission_rate=(commission or 0.1) / 100,
                slippage_rate=(slippage or 0.05) / 100,
            )

            # Run backtest
            engine = BacktestEngine(df, strategy, portfolio)
            result = engine.run()

            # Serialize result for storage
            store_data = {
                "equity_curve": result.equity_curve.reset_index().to_json(date_format="iso"),
                "trades": _serialize_trades(result.trades),
                "prepared_df": result.prepared_df.reset_index().to_json(date_format="iso"),
                "metrics": result.metrics,
            }

            status = f"回測完成！共 {result.metrics['trade_count']} 筆交易"
            return store_data, status

        except Exception as e:
            return no_update, f"錯誤: {str(e)}"

    # Result tab switching
    @app.callback(
        Output("result-tab-content", "children"),
        Input("result-tabs", "value"),
    )
    def render_result_tab(tab):
        if tab == "chart":
            return build_chart_panel()
        elif tab == "trades":
            return build_trades_panel()
        return build_metrics_panel()

    # Update chart
    @app.callback(
        Output("main-chart", "figure"),
        Output("equity-chart", "figure"),
        Input("backtest-result-store", "data"),
    )
    def update_charts(store_data):
        if not store_data:
            return _empty_chart("尚無回測結果"), _empty_chart("")

        prepared_df = pd.read_json(io.StringIO(store_data["prepared_df"]))
        if "Date" in prepared_df.columns:
            prepared_df = prepared_df.set_index("Date")

        equity_df = pd.read_json(io.StringIO(store_data["equity_curve"]))
        if "date" in equity_df.columns:
            equity_df = equity_df.set_index("date")

        trades = _deserialize_trades(store_data["trades"])

        # Determine overlays and sub-indicators
        overlays = []
        sub_indicators = []
        for col in prepared_df.columns:
            if col in ["Open", "High", "Low", "Close", "Volume"]:
                continue
            # Skip internal filter slope columns
            if col.endswith("_slope"):
                continue
            if col in ["MA", "EMA", "BB_upper", "BB_middle", "BB_lower"]:
                overlays.append(col)
            elif col.startswith("Pivot_") or col.startswith("SR_"):
                overlays.append(col)
            elif col in ["DT_neckline", "DB_neckline"]:
                overlays.append(col)
            elif col in ["DT_signal", "DB_signal", "DT_target", "DB_target"]:
                continue  # handled as markers in chart.py
            elif col == "_filter_ma_pos":
                prepared_df = prepared_df.rename(columns={col: "FilterMA(位置)"})
                overlays.append("FilterMA(位置)")
            elif col == "_filter_ma_dir":
                prepared_df = prepared_df.rename(columns={col: "FilterMA(方向)"})
                overlays.append("FilterMA(方向)")
            elif col == "RSI":
                sub_indicators.append("RSI")
            elif col == "MACD_line":
                sub_indicators.append("MACD")
            elif col == "K":
                sub_indicators.append("KD")
            elif col == "ATR":
                sub_indicators.append("ATR")

        # Deduplicate
        sub_indicators = list(dict.fromkeys(sub_indicators))

        main_fig = build_candlestick_chart(prepared_df, trades, overlays, sub_indicators, equity_df)
        volume_fig = build_volume_chart(prepared_df)

        return main_fig, volume_fig

    # Update trades table
    @app.callback(
        Output("trades-table", "data"),
        Input("backtest-result-store", "data"),
    )
    def update_trades_table(store_data):
        if not store_data:
            return []

        trades_data = store_data["trades"]
        rows = []
        for i, t in enumerate(trades_data):
            rows.append({
                "idx": i + 1,
                "side": "做多" if t["side"] == "long" else "做空",
                "entry_time": t["entry_time"][:10] if t["entry_time"] else "",
                "entry_price": f'{t["entry_price"]:.2f}',
                "exit_time": t["exit_time"][:10] if t["exit_time"] else "",
                "exit_price": f'{t["exit_price"]:.2f}',
                "quantity": f'{t["quantity"]:.2f}',
                "pnl": f'{t["pnl"]:.2f}',
                "return_pct": f'{t["return_pct"] * 100:.2f}',
            })
        return rows

    # Update metrics
    @app.callback(
        Output("metric-total-return", "children"),
        Output("metric-annual-return", "children"),
        Output("metric-sharpe", "children"),
        Output("metric-max-dd", "children"),
        Output("metric-win-rate", "children"),
        Output("metric-profit-factor", "children"),
        Output("metric-trade-count", "children"),
        Output("metric-avg-return", "children"),
        Output("metric-long-count", "children"),
        Output("metric-short-count", "children"),
        Input("backtest-result-store", "data"),
    )
    def update_metrics(store_data):
        if not store_data:
            return ("--",) * 10

        m = store_data["metrics"]

        def _safe(val, default=0):
            """Return default if val is None (from JSON inf/NaN)."""
            return default if val is None else val

        return (
            f'{_safe(m["total_return"]) * 100:.2f}%',
            f'{_safe(m["annualized_return"]) * 100:.2f}%',
            f'{_safe(m["sharpe_ratio"]):.2f}',
            f'{_safe(m["max_drawdown"]) * 100:.2f}%',
            f'{_safe(m["win_rate"]) * 100:.1f}%',
            f'{_safe(m["profit_factor"]):.2f}',
            str(_safe(m["trade_count"], 0)),
            f'{_safe(m["avg_trade_return"]) * 100:.2f}%',
            str(_safe(m["long_count"], 0)),
            str(_safe(m["short_count"], 0)),
        )


def _format_default_params(indicator: str) -> str:
    """Format default params for display, e.g. 'period=14' or 'fast=12,slow=26,signal=9'."""
    params = INDICATOR_DEFAULTS.get(indicator, {})
    if not params:
        return ""
    if len(params) == 1:
        k, v = next(iter(params.items()))
        return f"{k}={v}"
    return ",".join(f"{k}={v}" for k, v in params.items())


def _build_rules(indicators, fields, params, operators, values) -> list[Rule]:
    """Build Rule list from parallel arrays of UI values."""
    rules = []
    for ind, field, param, op, val in zip(
        indicators or [], fields or [], params or [],
        operators or [], values or [],
    ):
        if not ind or not field or not op or val is None or val == "":
            continue

        # Parse params
        indicator_params = INDICATOR_DEFAULTS.get(ind, {}).copy()
        if param:
            try:
                # Accept format like "period=20" or just "20" for single-param indicators
                if "=" in str(param):
                    for kv in str(param).split(","):
                        k, v = kv.strip().split("=")
                        indicator_params[k.strip()] = int(v.strip())
                else:
                    # Single value: apply to first param
                    first_key = list(indicator_params.keys())[0] if indicator_params else None
                    if first_key:
                        indicator_params[first_key] = int(param)
            except (ValueError, IndexError):
                pass

        # Parse value - could be number or column name
        try:
            parsed_value = float(val)
        except (ValueError, TypeError):
            parsed_value = str(val)

        rules.append(Rule(
            indicator=ind,
            params=indicator_params,
            field=field,
            operator=op,
            value=parsed_value,
        ))

    return rules


def _serialize_trades(trades) -> list[dict]:
    """Serialize Trade objects to dicts for JSON storage."""
    result = []
    for t in trades:
        result.append({
            "side": t.side,
            "entry_time": str(t.entry_fill.timestamp),
            "entry_price": t.entry_fill.price,
            "exit_time": str(t.exit_fill.timestamp),
            "exit_price": t.exit_fill.price,
            "quantity": t.entry_fill.quantity,
            "pnl": t.pnl,
            "return_pct": t.return_pct,
        })
    return result


def _deserialize_trades(trades_data) -> list:
    """Minimal deserialization for chart markers."""
    from engine.order import Fill, Trade
    from datetime import datetime

    result = []
    for t in trades_data:
        entry_fill = Fill(
            timestamp=pd.Timestamp(t["entry_time"]),
            side="buy" if t["side"] == "long" else "sell",
            price=t["entry_price"],
            quantity=t["quantity"],
            commission=0,
        )
        exit_fill = Fill(
            timestamp=pd.Timestamp(t["exit_time"]),
            side="sell" if t["side"] == "long" else "buy",
            price=t["exit_price"],
            quantity=t["quantity"],
            commission=0,
        )
        trade = Trade.__new__(Trade)
        trade.entry_fill = entry_fill
        trade.exit_fill = exit_fill
        trade.side = t["side"]
        trade.pnl = t["pnl"]
        trade.return_pct = t["return_pct"]
        result.append(trade)
    return result


def _empty_chart(title=""):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        annotations=[dict(text=title, showarrow=False, font=dict(size=16, color="#888"))],
        height=400,
    )
    return fig
