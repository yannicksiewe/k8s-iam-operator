import logging


class No200Filter(logging.Filter):
    def filter(self, record):
        return '200 OK' not in record.getMessage()
