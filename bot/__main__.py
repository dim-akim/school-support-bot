"""
Бот Технической поддержки Вальдорфской школы имени А.А. Пинского
В боте реализовано ограничение на использование некоторых команд только для администраторов

Функционал:
    (СисАдмин) Фиксация даты замены очередного картриджа
    TODO (СисАдмин) Фиксация моделей и количества привезенных картриджей
    (СисАдмин) Создание индивидуальных таблиц с оценками для рассылки по классам
    TODO Создание и подтверждение заявки на урок или мероприятие в Актовом зале
    Создание заявки на техническое обслуживание
    Регистрация учителя и подтверждение заявки
    Просмотр заявок, взятых админом в исполнение, и их закрытие
    TODO Получение ссылки на таблицу Успеваемости за нужный триместр
    TODO Получение ссылки на таблицу Успеваемости для класса (без права редактирования)
"""

import html
import json
import traceback
import datetime
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (ApplicationBuilder,
                          CommandHandler,
                          MessageHandler,
                          CallbackQueryHandler,
                          ContextTypes,
                          filters)

from bot.settings import Config
from bot.utils.users import get_users_from_table
import bot.handlers as handlers


logger = logging.getLogger('bot')


COMMAND_HANDLERS = {
    ('start', 'help'): handlers.start
}

CALLBACK_QUERY_HANDLERS = {
    '^' 'Зарегистрироваться' '$': handlers.register,
    '^' f'{Config.USERS_CALLBACK_PREFIX}(approve|decline)_[0-9]+' '$': handlers.approve_new_user,
    '^' f'{Config.TASKS_CALLBACK_PREFIX}accept_[0-9]+' '$': handlers.accept_task,
    '^' f'{Config.TASKS_CALLBACK_PREFIX}update_[0-9]+' '$': handlers.update_task,
    '^' f'{Config.TASKS_CALLBACK_PREFIX}close_[0-9]+' '$': handlers.close_task,
    '^' f'{Config.TASKS_CALLBACK_PREFIX}show_[0-9]+' '$': handlers.show_one_task,
}

CONVERSATION_HANDLERS = [
    handlers.tasks_conversation,
    handlers.cartridge_conversation,
    handlers.update_fullname_conversation
]


def run_support_bot():
    """Запускает бота @help_admin_1060_bot
    """
    app = ApplicationBuilder().token(
        Config.ECHO_TOKEN if Config.APP_ENV == 'dev' else Config.BOT_TOKEN).build()

    for command_name, command_handler in COMMAND_HANDLERS.items():
        app.add_handler(CommandHandler(command_name, command_handler))

    for handler in CONVERSATION_HANDLERS:
        app.add_handler(handler)

    for pattern, handler in CALLBACK_QUERY_HANDLERS.items():
        app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    # app.add_handler(handlers.exit_command_handler)
    # app.add_handler(handlers.exit_callback_handler)

    if Config.APP_ENV == 'dev':
        app.add_handler(MessageHandler(filters.TEXT, echo))
        app.add_handler(CallbackQueryHandler(callback_query_echo))
    elif Config.APP_ENV == 'prod':
        app.add_handler(MessageHandler(filters.TEXT, log_missing))
        app.add_handler(CallbackQueryHandler(log_missing))

    app.add_error_handler(handlers.error_handler)

    get_users_from_table(app)
    # TODO сделать кастомный контекст с уже созданными словарями new_users и new_tasks
    app.bot_data['new_users'] = {}
    app.bot_data['new_tasks'] = {}

    app.run_polling()


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "Это сообщение означает, что бот что-то не отловил:\n\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.bot_data = {html.escape(str(context.bot_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
    )

    await context.bot.send_message(
        chat_id=Config.SUPERUSER_ID,
        text=message,
        parse_mode=ParseMode.HTML
    )


async def callback_query_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer('Эта кнопка не активна')
    text = [
        'Эт сообщение означает, что нажатая кнопка не прошла ни один установленный фильтр.',
        '',
        'Нажата кнопка с параметром',
        f'<code>{query.data}</code>'
    ]
    text = '\n'.join(text)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML
    )


async def log_missing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    text = [
        "Something happened and bot missed it:\n",
        " " * 76,
        f"update = {str(update_str)}\n",
        " " * 76,
        f"context.bot_data = {str(context.bot_data)}\n",
        " " * 76,
        f"context.user_data = {str(context.user_data)}",
    ]
    text = "".join(text)
    logger.warning(text)


if __name__ == '__main__':
    run_support_bot()
