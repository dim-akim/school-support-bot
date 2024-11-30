import datetime
import functools
import logging

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler,
                          MessageHandler,
                          ConversationHandler,
                          CallbackQueryHandler,
                          ContextTypes,
                          Application,
                          filters)
from telegram.constants import ChatAction, ParseMode

from bot.utils.keyboards import make_inline_keyboard
from bot.utils.inline_calendar import MyCalendar, RU_STEP
from bot.utils.users import is_admin, user_is_teacher
from bot.settings import Config, ConversationStates
from bot.handlers.cancel import exit_command_handler, exit_callback_handler
from bot.models.task import Task

logger = logging.getLogger(f'admin.{__name__}')

WAIT_ACTION, WAIT_PROBLEM, WAIT_DESCRIPTION, WAIT_ROOM, WAIT_PRIORITY, WAIT_SHOW = range(6)


def admin_only(command):
    """
    Декоратор, который ограничивает доступ к команде только для chat_id, которые перечислены в ADMIN_IDS
    TODO вынести в отдельный модуль
    """

    @functools.wraps(command)
    async def wrapper(*args, **kwargs):
        update: Update = args[0]
        context: ContextTypes.DEFAULT_TYPE = args[1]

        chat_id = update.effective_user.id
        current_user = context.bot_data['users'].get(chat_id, None)

        if current_user and is_admin(current_user):
            if not context.user_data.get('table_fullname'):
                context.user_data['table_fullname'] = current_user.fullname
                context.user_data['role'] = current_user.role
            if not context.user_data.get('tasks', None):
                context.user_data['tasks'] = {}
            return await command(*args, **kwargs)
        else:
            logger.warning(f'Доступ к {command.__name__} запрещен для {current_user=}')
            return await access_denied(*args, **kwargs)

    return wrapper


async def access_denied(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f'access_denied is triggered by user: {update.effective_user.id} {update.effective_user.username}')
    text = ['Вам запрещено использовать эту команду',
            '',
            f'Обратитесь к @{Config.SUPERUSER_USERNAME} для получения доступа.']
    text = '\n'.join(text)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text)
    return ConversationHandler.END
