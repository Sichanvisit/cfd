"""
Application entrypoint.
"""

import logging
import traceback

from backend.app.trading_application import TradingApplication

logger = logging.getLogger(__name__)


def main():
    try:
        app = TradingApplication()
        app.run()
    except KeyboardInterrupt:
        logger.info("Trading application stopped by user.")
    except Exception:
        logger.critical("Trading application crashed:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
