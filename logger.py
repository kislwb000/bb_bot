import logging
import os

LOG_DIR = "logs"
LOG_FILE = "bot.log"

# Убедимся, что папка logs существует
os.makedirs(LOG_DIR, exist_ok=True)

# Формат логов
log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/{LOG_FILE}", encoding='utf-8'),
        logging.StreamHandler()  # Также выводит в консоль
    ]
)

# Отдельные именованные логгеры
app_logger = logging.getLogger("bot.app")
db_logger = logging.getLogger("bot.db")
