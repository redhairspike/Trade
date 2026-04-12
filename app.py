import dash
from ui.layout import build_layout
from ui.callbacks import register_callbacks
from ui.callbacks_screener import register_screener_callbacks
from ui.callbacks_download import register_download_callbacks

# Import indicators to trigger registration
import indicators.moving_averages  # noqa: F401
import indicators.oscillators      # noqa: F401
import indicators.volatility           # noqa: F401
import indicators.support_resistance  # noqa: F401
import indicators.patterns            # noqa: F401

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="交易回測系統",
)

app.layout = build_layout()

register_callbacks(app)
register_screener_callbacks(app)
register_download_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
