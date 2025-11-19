"""Entry point for the live trading bot."""
from __future__ import annotations

import argparse
import signal
import sys
import time

from config.settings import Settings, get_settings
from .auth import UpstoxSessionManager
from .data import MarketDataStream
from .event_filter import ExternalEventFilter
from .logging_utils import configure_logging, get_logger
from .orders import OrderManager
from .portfolio import PortfolioManager
from .risk import RiskManager
from .strategy import StrategyEngine
from .trade_logger import TradeLogger

logger = get_logger(__name__)


def build_components(settings: Settings, auth_code: str | None) -> MarketDataStream:
    session_manager = UpstoxSessionManager(settings)
    if auth_code:
        session_manager.initialize_session(auth_code)
    else:
        session_manager.get_client()

    portfolio = PortfolioManager(settings, session_manager)
    order_manager = OrderManager(settings, session_manager)
    strategy = StrategyEngine(settings)
    risk_manager = RiskManager(settings, portfolio)
    trade_logger = TradeLogger(settings)
    event_filter = ExternalEventFilter(settings)
    event_filter.load_from_file(settings.data_dir / "macro_events.json")

    return MarketDataStream(
        settings=settings,
        strategy=strategy,
        order_manager=order_manager,
        portfolio=portfolio,
        risk_manager=risk_manager,
        trade_logger=trade_logger,
        event_filter=event_filter,
    )


def run_bot(auth_code: str | None = None) -> None:
    settings = get_settings()
    configure_logging(settings)
    stream = build_components(settings, auth_code)

    stop_requested = False

    def handle_signal(signum, frame):  # noqa: ANN001
        nonlocal stop_requested
        stop_requested = True
        logger.warning("Received signal %s. Stopping bot.", signum)
        stream.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    stream.start()
    logger.info("Bot started. Monitoring between %s and %s IST.", settings.trading_start_ist, settings.trading_end_ist)
    try:
        while not stop_requested:
            time.sleep(5)
    finally:
        stream.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upstox algorithmic trading bot")
    parser.add_argument("--auth-code", help="Authorization code for initial token exchange", default=None)
    args = parser.parse_args(argv)
    run_bot(args.auth_code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
