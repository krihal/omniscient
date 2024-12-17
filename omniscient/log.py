import logging

try:
    from flask import current_app
except ImportError:
    current_app = None


def get_logger() -> logging.Logger:
    """
    Get the logger for the current flask app, or a default logger
    if not available.
    """

    if current_app:
        logger = current_app.logger
    else:
        logger = logging.getLogger("omniscient")
        if not logger.handlers:
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
            )

            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
