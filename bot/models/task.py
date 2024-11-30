"""
Класс Task, который описывает задачу для Google-таблицы "Задачи Admin 1060"

Столбцы (поля):
    id          A - 1
    Кабинет     B - 2
    Задача      C - 3
    Создана	    D - 4
    Автор       E - 5
    Приоритет   F - 6
    Статус      G - 7
    Исполнитель H - 8
    Дата_взятия I - 9
    Срок        J - 10
    Выполнено   K - 11
    Примечания  L - 12
    Блок        M - 13
"""
import dataclasses
import logging
from datetime import datetime

import bot.database as database
from bot.settings import Config


logger = logging.getLogger(__name__)


class Task:
    # TODO метод - фиксация ячейки в поле Зафиксировано
    # TODO оптимизация методов - изменения отдельно, запись в таблицу отдельно
    def __repr__(self):
        return f'<Task: id={self.task_id} created_at {self.created_at}>'

    def __init__(self,
                 task_id: int | str,
                 room: int | str,
                 text: str,
                 created_at: datetime,
                 author: str,
                 priority: int,
                 status: int = 0,
                 executor: str | int = None,
                 taken_at: datetime | str = None,
                 complete_until: datetime | str = None,
                 completed_at: datetime | str = None,
                 comments: str = None,
                 is_blocked: bool = False):
        self.task_id = int(task_id)
        self.room = int(room)
        self.text = text
        if isinstance(created_at, str):
            created_at = datetime.strptime(created_at, Config.TIMESTAMP)
        self.created_at = created_at
        self.author = author
        self.priority = priority
        if isinstance(status, str):
            status = Config.get_from_mappings(status)
        self.status = status
        if isinstance(executor, str):
            executor = Config.get_from_mappings(executor)
        self.executor = executor

        if taken_at and isinstance(taken_at, str):
            taken_at = datetime.strptime(taken_at, Config.TIMESTAMP)
        self.taken_at = taken_at
        if complete_until and isinstance(complete_until, str):
            complete_until = datetime.strptime(complete_until, Config.TIMESTAMP)
        self.complete_until = complete_until
        if completed_at and isinstance(completed_at, str):
            completed_at = datetime.strptime(completed_at, Config.TIMESTAMP)
        self.completed_at = completed_at

        self.comments = self._parse_comments_from_str(comments)
        self.is_blocked = is_blocked
        self.changed = dict()

    @staticmethod
    def _parse_comments_from_str(comments: str) -> list[tuple[datetime, str]]:
        result = []
        if comments:
            comments = comments.split('\n')
            for comment in comments:
                time, comment = [item.strip() for item in comment.split(']')]
                time = datetime.strptime(time[1:], Config.TIMESTAMP)
                result.append((time, comment))
        return result

    @staticmethod
    def _parse_comments_to_str(comments: list[tuple[datetime, str]]) -> str:
        if not comments:
            return ''
        result = []
        for time, comment in comments:
            result.append(f'[{time.strftime(Config.TIMESTAMP)}] {comment}')
        return '\n'.join(result)

    def write_to_table(self, row: int | None = None):
        logger.info(f'Pushing {self} with {self.changed} to the table')
        if not row:
            row = self.row

        dict_to_write = self.__dict__.copy()
        dict_to_write.pop('changed')
        dict_to_write['task_id'] = f'=СТРОКА($A${self.task_id})'  # Фиксируем id задачи на случай сортировок
        dict_to_write['comments'] = self._parse_comments_to_str(self.comments)

        # Преобразование дат
        for key in ('created_at', 'taken_at', 'complete_until', 'completed_at'):
            if dict_to_write[key]:
                dict_to_write[key] = self.__dict__[key].strftime(Config.TIMESTAMP)
        if dict_to_write['status'] in Config.mappings:
            dict_to_write['status'] = Config.mappings[dict_to_write['status']]
        if dict_to_write['executor'] and isinstance(dict_to_write['executor'], int):
            dict_to_write['executor'] = Config.mappings[dict_to_write['executor']]

        logger.info(f'Values to be inserted: {dict_to_write}')
        database.task_sheet.update_row(row, list(dict_to_write.values()))
        logger.info(f'{self} is successfully pushed to the table')
        result = self.changed
        self.changed.clear()
        return result

    @property
    def row(self) -> int:
        task_ids = database.get_ids()
        return task_ids.index(self.task_id) + 2

    def take(self, executor_id: int | str, taken_at: datetime | None = None):
        logger.info(f'ID {executor_id} is trying to take {self} ')
        if self.executor:
            logger.info(f'{self} is already taken by {self.executor}')
            return {'already-taken-by': self.executor}
        if not taken_at:
            taken_at = datetime.now()

        self._edit_batch(
            executor=executor_id,
            status=Config.STATUS_TAKEN,
            taken_at=taken_at
        )
        logger.info(f'{self} is taken by {self.executor}')
        return self.write_to_table()

    def _edit_batch(self, **kwargs):
        """
        Use this method to edit multiple attributes of :class:`Task`
        """

        logger.info(f'Starting batch update of {self}')
        for key, value in kwargs.items():
            self._edit_one(key, value)
        return {'ok': True}

    def _edit_one(self, attr, value):
        if attr not in self.__dict__:
            message = f'Task has no attribute called {attr}'
            logger.error(message, exc_info=True)
            raise AttributeError(message)
        setattr(self, attr, value)
        self.changed[attr] = value
        logger.info(f'Updated attribute {attr} with {value}')
        return {'ok': True}

    def edit_priority(self, priority: int):
        """
        Edit priority of the Task and save it to the table
        """
        self._edit_priority(priority)
        return self.write_to_table()

    def _edit_priority(self, priority: int):
        return self._edit_one('priority', priority)

    def edit_comment(self, new_comment: str, given_at: datetime | None = None):
        """
        Edit a comment and save it to the table
        """
        if not given_at:
            given_at = datetime.now()
        self._edit_one('comment', [(given_at, new_comment)])
        return self.write_to_table()

    def add_comment(self, new_comment: str, given_at: datetime | None = None):
        """
        Add a comment and save it to the table
        """
        self._add_comment(new_comment, given_at)
        return self.write_to_table()

    def _add_comment(self, new_comment: str, given_at: datetime | None = None):
        """
        Add a comment without deleting the existing one
        """
        if not given_at:
            given_at = datetime.now()
        self.comments.append((given_at, new_comment))
        self.changed['comments'] = self._parse_comments_to_str([(given_at, new_comment)])
        logger.info(f'Updated attribute comment with {self.changed['comments']}')
        return {'ok': True}

    def change_executor(self, new_executor: int, taken_at: datetime | None = None):
        """
        Change executor and save it to the table
        """
        if new_executor == self.executor:
            logger.warning(f'Cannot change executor: {Config.mappings[new_executor]} is already assigned to {self}')
            return {'same-executor': self.executor}
        self._change_executor(new_executor, taken_at)
        return self.write_to_table()

    def _change_executor(self, new_executor: int, taken_at: datetime | None = None):
        """
        Change executor of :class:`<Task>`.

        The last values of attributes :attr:`executor` and :attr:`taken_at` are stored to the :attr:`comment` attribute
        """
        last_executor = self.executor
        last_taken_at = self.taken_at.strftime(Config.TIMESTAMP)
        if not taken_at:
            taken_at = datetime.now()
        logger.info(
            f'Changing executor of {self} from {Config.mappings[last_executor]} to {Config.mappings[new_executor]}'
        )
        self._add_comment(
            f'Предыдущий исполнитель {Config.mappings[last_executor]} работал над задачей с {last_taken_at}'
        )
        return self._edit_batch(
            executor=new_executor,
            taken_at=taken_at
        )

    def complete(self, completed_at: datetime | None = None, comment: str | None = None):
        """
        Complete the Task and write it to the table.

        Changing:
            :attr:`status` attribute to value 2
        """
        self._end(completed_at=completed_at, comment=comment)
        return self.write_to_table()

    def cancel(self, completed_at: datetime | None = None, comment: str | None = None):
        """
        Cancel the Task and write it to the table.

        Changing:
            :attr:`status` attribute to value 3
        """
        self._end(new_status=Config.STATUS_CANCELED, completed_at=completed_at, comment=comment)
        return self.write_to_table()

    def _end(self,
             new_status: int = Config.STATUS_COMPLETED,
             completed_at: datetime | None = None,
             comment: str | None = None):
        """
        End the Task by completing or canceling.

        Changing:
            :attr:`completed_at` attribute to datetime object
            :attr:`status` attribute to value 2 (complete) or 3 (cancel)

        Optionally can add a comment
        """
        if comment:
            self._add_comment(comment)
        if not completed_at:
            completed_at = datetime.now()
        return self._edit_batch(
            status=new_status,
            completed_at=completed_at
        )

    def return_to_work(self, comment: str):
        """
        Return the Task back to work. A comment is mandatory!

        Changing:
            :attr:`completed_at` attribute to None
            :attr:`status` attribute to value 1
        """
        if not comment:
            logger.warning(f"You can't return {self} to work without a comment")
            return
        self._add_comment(comment)
        self._edit_batch(
            status=Config.STATUS_TAKEN,
            completed_at=None
        )
        logger.info(f'{self} returned to work with comment: {comment}')
        return self.write_to_table()

    @classmethod
    def get_last_id(cls) -> int:
        logger.info('Finding last used task_id')
        last_id = sorted(database.get_ids())[-1]
        logger.info(f'Last task_id found: {last_id}')
        return int(last_id)

    @classmethod
    def create(cls,
               room: int,
               text: str,
               author: str,
               created_at: datetime | None = None,
               priority: int = 2):
        new_id = cls.get_last_id() + 1
        database.task_sheet.update_value((new_id + 1, Config.task_columns['task_id']), new_id)
        logger.info(f'{new_id=} is reserved on the table')
        if not created_at:
            created_at = datetime.now()
        new_task = Task(new_id, room, text, created_at, author, priority)
        logger.info(f'Task created: {new_task}')
        new_task.write_to_table(row=new_id + 1)
        return new_task

    @classmethod
    def get_one_or_none(cls, task_id: int):
        logger.info(f'Finding {task_id=}')
        ids = database.get_ids()

        try:
            row = ids.index(task_id) + 2  # rows begin from 1, 1st row - title
        except ValueError:
            logger.error(f'{task_id} is not found in the table')
            return None
        logger.info(f'Found {task_id=} on {row=}. Pulling the task from the table')
        task = Task(*database.task_sheet.get_row(row=row, include_tailing_empty=False))
        logger.info(f'{task} is pulled from the table')
        return task

    @classmethod
    def get_all_tasks(cls, **filter_by) -> list:
        rows = database.get_rows_amount()
        logger.info(f'Applying {filter_by=}')
        keys = list(filter_by.keys())
        for key in keys:
            if key not in Config.task_columns:
                logger.warning(f'Task has not an attribute called {key}, skipping')
                filter_by.pop(key)

        result = []
        for row in rows:
            # print(row)
            for key, value in filter_by.items():
                if row[Config.task_columns[key] - 1] != value:
                    break
            else:
                result.append(Task(*row))
        logger.info(f'{len(result)} tasks found with query {filter_by}')
        return result


if __name__ == '__main__':
    # TODO оформить в виде тестов
    # task1 = Task.create(408, 'тест', 'Акимов', datetime(2024, 11, 1))
    # task2 = Task.create(308, 'тест2', 'Акимов', datetime(2024, 11, 3))
    # task3 = Task.create(409, 'тест3', 'Акимов', datetime(2024, 11, 4), 1)
    # task4 = Task.create(409, 'тест4', 'Акимов', datetime(2024, 11, 4))
    # task1.take(262388958)
    # task2.take(262388958)
    # task3.take(1983129117)
    # task1.add_comment('Тестовый комментарий')
    # task1.change_executor(1983129117)
    # task1.complete()
    # task2.cancel()
    # task1 = Task(111, 408, 'тест',
    #              datetime(2024, 11, 1), 'Акимов', priority=3,
    #              comments='[13.11.2024 0:00:00] Подключил кабель HDMI, доску можно пока использовать как монитор\n'
    #                       '[14.11.2024 0:00:00] Выключил кабель HDMI, доску можно пока использовать как монитор')
    # print(task1.comments)
    # print(task1._parse_comments_to_str(task1.comments))
    # print(Task.get_one_or_none(5).__dict__)
    # print(Task.get_one_or_none(10).__dict__)
    tasks = Task.get_all_tasks(executor='Акимов Дмитрий', status='Взято')
    print(tasks)
