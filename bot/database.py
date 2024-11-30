"""
В модуле реализуется подключение к базе данных
На данный момент в этом качестве выступают Google-Таблицы
"""
import pathlib
import logging
from datetime import datetime

import pygsheets

from bot.settings import Config

logger = logging.getLogger(__name__)


def get_ids() -> list[int]:
    """
    returns a list of all existing task_ids
    """
    logger.debug("Getting all existing task_ids")
    ids = task_sheet.get_col(Config.task_columns['task_id'], include_tailing_empty=False)[1:]
    return [int(i) for i in ids]


def get_rows_amount(amount: int = 1000):
    """
    returns a list of nonzero rows where each row is a list of task attributes
    """
    logger.debug("Getting all rows from the table")
    return task_sheet.get_values((2, Config.task_columns['task_id']),
                                 (amount, Config.task_columns['comments']),
                                 # include_tailing_empty=False,
                                 include_tailing_empty_rows=False)


# TODO найти способ открывать и закрывать подключение по аналогиями с сессиями db (асинхронными?)
client = pygsheets.authorize(service_account_file=Config.SERVICE_FILE_PATH)
task_table: pygsheets.Spreadsheet = client.open_by_key(Config.TASKS_GSHEET_KEY)
logger.info('Connection succeeded to Google-Table `Задачи Admin 1060`')
logger.debug(f'List of worksheets: {task_table.worksheets()}')
task_sheet: pygsheets.worksheet.Worksheet = task_table.worksheet(value=Config.TASKS_PAGE_INDEX)
task_map_sheet: pygsheets.worksheet.Worksheet = task_table.worksheet(value=Config.TASKS_SETTINGS_PAGE_INDEX)
task_users_sheet: pygsheets.worksheet.Worksheet = task_table.worksheet(value=Config.TASKS_USERS_PAGE_INDEX)
# TODO сделать статусы и админов словариками, забираемыми из task_map_sheet


if __name__ == '__main__':
    # now = datetime.now()
    # range = get_rows_amount(1000)
    # print(f'Requested 1000 rows in {datetime.now() - now}')
    # for item in range:
    #     print(item)
    # now = datetime.now()
    # col = get_ids()
    # print(f'Requested all ids in {datetime.now() - now}')
    # now = datetime.now()
    # range = get_rows_amount(len(col))
    # print(f'Requested {len(col)} rows in {datetime.now() - now}')
    # # for item in range:
    # #     print(item)
    row = len(task_users_sheet.get_col(1, include_tailing_empty=False)) + 1
    print(f'{row=}')

