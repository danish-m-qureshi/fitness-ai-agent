import logging
import sys

from app.core.middleware import request_id_context


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get("-")
        return True


def configure_logging(log_level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=(
            "%(asctime)s | %(levelname)s | request_id=%(request_id)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[handler],
        force=True,
    )
