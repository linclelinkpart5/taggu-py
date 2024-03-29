import logging


def get_logger(name: str) -> logging.Logger:
    """Gets logger instance, and sets options for consistency."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # This prevents duplicated log messages when reloading modules.
    if not len(logger.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        logger.addHandler(ch)

    return logger
