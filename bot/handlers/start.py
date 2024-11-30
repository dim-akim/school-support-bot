import logging
import functools

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.settings import Config
from bot.utils.users import user_is_teacher, is_admin
from bot.utils.keyboards import make_inline_keyboard
from bot.handlers.admin import send_new_user_to_admin

logger = logging.getLogger(__name__)


def authorize(command):
    """Декоратор, который заполняет поля user_data['table_fullname'] и user_data['role']
    при первом обращении к команде.
    Если пользователя нет в списке bot_data['users'], перенаправляет на регистрацию."""

    @functools.wraps(command)
    async def wrapper(*args, **kwargs):
        update: Update = args[0]
        context: ContextTypes.DEFAULT_TYPE = args[1]

        if not context.user_data.get('table_fullname'):
            current_user = context.bot_data['users'].get(update.effective_user.id, None)
            if not current_user:
                logger.info(f'Telegram ID {update.effective_user.id} not found. Redirecting to sign_up')
                return await sign_up(update, context)
            context.user_data['table_fullname'] = current_user.fullname
            context.user_data['role'] = current_user.role
        return await command(*args, **kwargs)

    return wrapper


@authorize
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers for /start and /help commands.
    """
    logger.info(
        f'start is triggered by user: {update.effective_user.id} {update.effective_user.username}')
    user_id = update.effective_user.id
    current_user = context.bot_data['users'].get(user_id, None)
    if user_id == Config.SUPERUSER_ID or is_admin(current_user):
        return await admin_help(update, context)
    if user_is_teacher(context.user_data):
        return await teacher_help(update, context)
    logger.error(f'Telegram ID {user_id} missed identification. Redirecting to sign_up')
    return await sign_up(update, context)


async def sign_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f'sign_up is triggered by user: {update.effective_user.id} {update.effective_user.username}')
    text = [
        'Вас приветствует бот Технической поддержки',
        'Вальдорфской школы имени А. А. Пинского.',
        '',
        'Использование бота допускается только сотрудниками школы,',
        'но Вас я пока не вижу в этом списке.',
        '',
        'Чтобы попасть в него, нажмите на кнопку',
    ]
    text = '\n'.join(text)
    await update.message.reply_html(
        text=text,
        reply_markup=make_inline_keyboard(['Зарегистрироваться'], exit_btn=False)
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f'register is triggered by user: {update.effective_user.id} {update.effective_user.username}')
    query = update.callback_query
    await query.answer('Заявка отправлена!')
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name
    text = [
        'Данные Вашей заявки:',
        '',
        f'Telegram ID: <code>{user_id}</code>',
        f'Имя в Telegram: <code>{full_name}</code>',
        '',
        'Как только ее подтвердит Администратор, вам придет оповещение.',
        f'Связь с Администратором: @{Config.SUPERUSER_USERNAME}',
    ]
    text = '\n'.join(text)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    await send_new_user_to_admin(update, context)


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f'admin_help is triggered by user: {update.effective_user.id} {update.effective_user.username}')
    userid = update.message.from_user.id
    text = [
        'Вас приветствует бот Технической поддержки',
        'Вальдорфской школы имени А. А. Пинского',
        '',
        '<b>Ваша роль</b>: <code>Админ</code>',
        'Доступные команды:',
        '/cartridge - начать диалог замены картриджа',
        '/tasks     - создать заявку или посмотреть задачи',
    ]
    text = '\n'.join(text)
    await update.message.reply_html(text)


async def teacher_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f'teacher_help is triggered by user: {update.effective_user.id} {update.effective_user.username}')
    text = [
        'Вас приветствует бот Технической поддержки',
        'Вальдорфской школы имени А. А. Пинского',
        '',
        '<b>Ваша роль</b>: <code>Учитель</code>',
        'Доступные команды:',
        '/tasks - создать новую заявку',
    ]
    text = '\n'.join(text)
    await update.message.reply_html(text)
