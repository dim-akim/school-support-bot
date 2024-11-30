import logging
from dataclasses import dataclass
from datetime import datetime

from telegram.ext import Application, ContextTypes

from bot.settings import Config
from bot.database import task_users_sheet


logger = logging.getLogger(__name__)


@dataclass
class User:
    telegram_id: int
    fullname: str
    username: str
    role: str

    def __post_init__(self):
        self.telegram_id = int(self.telegram_id)
        if self.fullname == self.username:
            self.username = ''


@dataclass
class UserInTable(User):
    history: str


def get_users_from_table(app: Application, amount: int = 200) -> None:
    logger.debug(f'Getting {amount} users from the table')
    users_raw = task_users_sheet.get_values((2, Config.user_columns['telegram_id']),
                                            (amount, Config.user_columns['role']),
                                            # include_tailing_empty=False,
                                            include_tailing_empty_rows=False)
    app.bot_data['users'] = {int(data[0]): User(*data) for data in users_raw}
    logger.info(f"Got {len(users_raw)} users from table")
    return


def user_is_teacher(user_data: dict) -> bool:
    return user_data.get('role') == 'Учитель'


def is_admin(user: User) -> bool:
    return user.role in ('Админ', 'Суперадмин')


def get_user_by_id(telegram_id: int, users: dict[int, User]) -> User:
    for user_id, user in users.items():
        if telegram_id == user.telegram_id:
            return user


def delete_user_from_dict(telegram_id, users: dict[int, User]) -> User:
    for user_id, user in users.items():
        if telegram_id == user.telegram_id:
            return users.pop(telegram_id)


def write_user_to_table(user: User, who_approved_fullname: str) -> None:
    logger.info(f"Finding first empty row")
    row = len(task_users_sheet.get_col(1, include_tailing_empty=False)) + 1
    date_str = datetime.now().strftime(Config.TIMESTAMP)
    #
    history_str = f'[{date_str}] {who_approved_fullname} назначил роль {user.role}'
    task_users_sheet.update_row(
        row,
        [user.telegram_id, user.fullname, user.username, user.role, history_str]
    )
    logger.info(f"Success: {user} added to the table")
