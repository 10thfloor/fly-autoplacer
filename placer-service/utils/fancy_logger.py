"""Logging setup without filesystem side effects during imports."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(data_dir="data"):
    log_file = Path(data_dir).resolve() / "logs" / "auto_placer.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    for handler in list(logger.handlers):
        if getattr(handler, "_autoplacer_file", False):
            if handler.baseFilename == str(log_file):
                return
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
    handler._autoplacer_file = True
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


def log_action(action, region, dry_run):
    logging.info("%s%s in region: %s", "[DRY RUN] Would " if dry_run else "", action, region)


def get_logger(name):
    return logging.getLogger(name)
