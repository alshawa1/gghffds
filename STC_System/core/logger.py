import logging
import sys

def setup_logger(name='AmalSystem', level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = setup_logger()
