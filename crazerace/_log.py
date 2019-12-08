import logging


_logger = None


def info(message: str) -> None:
    log("info", message)


def warning(message: str) -> None:
    log("warning", message)


def log(type: str, message: str, *args, **kwargs) -> None:
    """Log into the internal werkzeug logger."""
    global _logger
    if _logger is None:
        import logging

        _logger = logging.getLogger("crazerace")
        if _logger.level == logging.NOTSET:
            _logger.setLevel(logging.INFO)
        if not logging.root.handlers:
            handler = logging.StreamHandler()
            _logger.addHandler(handler)
    getattr(_logger, type)(message.rstrip(), *args, **kwargs)
