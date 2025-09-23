import logging
import os
import sys
from pythonjsonlogger import jsonlogger


LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class RequestIdFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._local = {}

    def set(self, request_id: str | None):
        self._local["request_id"] = request_id

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore
        record.request_id = self._local.get("request_id")
        return True


request_id_filter = RequestIdFilter()


def configure_logging():
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(request_id_filter)
    if LOG_FORMAT == "json":
        fmt = jsonlogger.JsonFormatter("%(levelname)s %(message)s %(asctime)s %(name)s %(request_id)s")
        handler.setFormatter(fmt)
    else:
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s] %(message)s")
        handler.setFormatter(fmt)

    root.addHandler(handler)


def set_request_id(value: str | None):
    request_id_filter.set(value)

