import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)]
)

def create_logger():
    return logging.getLogger(__name__)