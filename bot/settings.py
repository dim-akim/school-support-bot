"""
Здесь собираются
    Общие настройки бота
    Настройки модуля задач в классе ConfigTasks

    TODO использовать pydantic_settings?
"""
import os
import json
import logging
from dotenv import load_dotenv
from pathlib import Path

from bot.utils.log import configure_logging, BASE_DIR

load_dotenv()

configure_logging(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)


# settings_file = 'key/settings.json'
# with open(settings_file) as file:
#     # Google-таблицы (их ключи)
#     settings = json.load(file)


class ConversationStates:
    (
        FLOOR, ROOM, DEVICE, DATE, DONE,
        WAIT_ACTION, WAIT_PROBLEM, WAIT_DESCRIPTION, WAIT_ROOM, WAIT_PRIORITY
    ) = range(10)


class ConfigTasks:
    TASKS_GSHEET_KEY = os.getenv('TASKS_GSHEET_KEY')  # Задачи Admin 1060
    TASKS_PAGE_INDEX = 0  # Индекс листа с задачами таблицы `Задачи Admin 1060`
    TASKS_SETTINGS_PAGE_INDEX = 1  # Индекс листа с настройками таблицы `Задачи Admin 1060`
    TASKS_USERS_PAGE_INDEX = 2  # Индекс листа с настройками таблицы `Задачи Admin 1060`

    TIMESTAMP = '%d.%m.%Y %H:%M'
    # TIMESTAMP = '%d.%m.%Y %H:%M:%S'
    # TODO автоматизировать получение mappings либо вынести в таблицу

    STATUS_NOT_TAKEN, STATUS_TAKEN, STATUS_COMPLETED, STATUS_CANCELED = range(4)

    TASKS_CALLBACK_PREFIX = 'tasks_'

    mappings = {
        # Статус
        0: 'Не начато',
        1: 'Взято',
        2: 'Выполнено',
        3: 'Отменено',
        262388958: 'Акимов Дмитрий',
        1983129117: 'Глобин Никита'
    }

    task_columns = {
        'task_id': 1,  # id              A
        'room': 2,  # Кабинет            B
        'text': 3,  # Задача             C
        'created_at': 4,  # Создана      D
        'author': 5,  # Автор            E
        'priority': 6,  # Приоритет      F
        'status': 7,  # Статус           G
        'executor': 8,  # Исполнитель    H
        'taken_at': 9,  # Дата_взятия    I
        'complete_until': 10,  # Срок    J
        'completed_at': 11,  # Выполнено K
        'comments': 12,  # Примечания    L
        'is_blocked': 13  # Блок         M
    }

    user_columns = {
        'telegram_id': 1,        # id          A
        'fullname': 2,           # Кабинет     B
        'username': 3,           # Задача      C
        'role': 4,               # Создана     D
        'history': 5,            # Исполнитель H
    }

    @classmethod
    def get_from_mappings(cls, value) -> int | str:
        for key, i in cls.mappings.items():
            if key == value or i == value:
                if key == value:
                    return i
                return key


class Config(ConfigTasks):
    APP_ENV = os.getenv('APP_ENV')
    BASE_DIR = BASE_DIR

    SERVICE_FILE_PATH = BASE_DIR / 'bot' / os.getenv('GOOGLE_SERVICE_FILE')  # путь к файлу доступа к Google-Таблицам

    PRINTERS_GSHEET_KEY = os.getenv('PRINTERS_GSHEET_KEY')  # Реестр Принтеров
    macbook_gsheet_key = os.getenv('MACBOOK_GSHEET_KEY')  # Реестр MacBook
    depo_gsheet_key = os.getenv('DEPO_GSHEET_KEY')  # Реестр Depo
    lenovo_gsheet_key = os.getenv('LENOVO_GSHEET_KEY')  # Реестр Lenovo
    technics_gsheet_key = os.getenv('TECHNICS_GSHEET_KEY')  # Учет техники 1060
    SCORES_GSHEET_KEY = os.getenv('SCORES_GSHEET_KEY')  # Успеваемость (1 триместр) 24-25

    # Telegram-бот
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ECHO_TOKEN = os.getenv('ECHO_TOKEN')

    SUPERUSER_ID = int(os.getenv('SUPERUSER_ID'))
    SUPERUSER_USERNAME = os.getenv('SUPERUSER_USERNAME')

    USERS_CALLBACK_PREFIX = 'users_'

    def __init__(self, **kwargs):
        pass


if __name__ == '__main__':
    print(Config.PRINTERS_GSHEET_KEY)
    print(f'{Config.TASKS_PAGE_INDEX=}')
    print(f'{Config.TASKS_CALLBACK_PREFIX}' 'Задачи')
    print(Path.cwd())
