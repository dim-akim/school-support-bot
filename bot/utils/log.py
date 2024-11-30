
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


BASE_DIR = Path.cwd()
LOG_FOLDER = BASE_DIR / 'logs'  # имя папки с логами
LOG_FOLDER.mkdir(exist_ok=True)  # создаем папку для логов. exist_ok - если папка уже есть, не будет ошибки

LOG_FILE = 'support-bot.log'  # имя для общего лог-файла

file_handler = logging.FileHandler(LOG_FOLDER / LOG_FILE)
# file_handler.setFormatter(FORMATTER)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
# console_handler.setFormatter(FORMATTER)
console_handler.setLevel(logging.DEBUG)


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-7s | %(name)-30s [%(lineno)4d] - %(message)s",
        level=level,
        handlers=[file_handler, console_handler]
    )


class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
