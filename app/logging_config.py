import logging
from pythonjsonlogger import jsonlogger


def setup_logging():
    logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', level=logging.INFO)
