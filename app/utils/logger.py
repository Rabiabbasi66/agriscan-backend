import logging
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=fmt,
        datefmt=date_fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/agriscan.log", encoding="utf-8"),
        ],
    )

    # Quiet noisy libs
    for lib in ("motor", "pymongo", "urllib3", "botocore", "boto3", "s3transfer"):
        logging.getLogger(lib).setLevel(logging.WARNING)
