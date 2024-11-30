import logging

from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (MessageHandler,
                          ContextTypes,
                          ConversationHandler,
                          CallbackQueryHandler,
                          filters)

from bot.settings import Config
from bot.handlers.cancel import exit_command_handler, exit_callback_handler
from bot.utils.keyboards import make_inline_keyboard
from bot.utils.users import (User,
                             write_user_to_table)


logger = logging.getLogger(__name__)

WAIT_NEW_FULLNAME = 0
APPROVE = 'approve'
DECLINE = 'decline'
NOT_FOUND = 'not found'


async def send_new_user_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f'send_new_user_to_admin is triggered by user: {update.effective_user}')
    new_user = User(
        telegram_id=update.effective_user.id,
        fullname=update.effective_user.full_name,
        username=update.effective_user.name,
        role='Учитель')
    context.bot_data['new_users'][update.effective_user.id] = new_user
    text = [
        'Регистрация нового пользователя!',
        '',
        f'Telegram ID: <code>{new_user.telegram_id}</code>',
        f'Имя в Telegram: <code>{new_user.fullname}</code>',
        f'Username Telegram: {new_user.username}',
        f'Роль: <code>{new_user.role}</code>'
    ]
    text = '\n'.join(text)
    buttons = {
        'Подтвердить': f'approve_{new_user.telegram_id}',
        'Изменить имя': f'update-name_{new_user.telegram_id}',
        'Отказать': f'decline_{new_user.telegram_id}'
    }
    await context.bot.send_message(
        chat_id=Config.SUPERUSER_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=make_inline_keyboard(buttons, exit_btn=False, callback_prefix=Config.USERS_CALLBACK_PREFIX)
    )
    return ConversationHandler.END


async def approve_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f'approve_new_user is triggered by user: {update.effective_user}')
    query = update.callback_query
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    _, verdict, user_id = query.data.split('_')  # TODO вынести в отдельную функцию
    user_id = int(user_id)
    user = context.bot_data['new_users'].pop(user_id, None)
    if user:
        if verdict == APPROVE:
            write_user_to_table(user, context.user_data['table_fullname'])
            # write_user_to_table(user, 'testing')
            context.bot_data['users'][user_id] = user
        await send_verdict(user, verdict, context)
    else:
        logger.warning(
            f'User with {user_id=} not found in bot_data["new_users"]. Probably already approved or declined')
        verdict = NOT_FOUND

    answers = {
        APPROVE: 'Заявка подтверждена!',
        DECLINE: 'Заявка отклонена!',
        NOT_FOUND: 'Пользователь не найден в списке заявок'
    }
    text = answers[verdict]
    await query.answer(text)

    text = f'{query.message.text} \n\n <b>{text}</b>'

    await query.edit_message_text(text, parse_mode=ParseMode.HTML)


async def send_verdict(user: User, verdict: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f'{verdict=} is being sent to user: {user.telegram_id} {user.fullname}')
    if verdict == APPROVE:
        text = [
            '\U0001F44D Ваша регистрация подтверждена!',
            '',
            f'Нажмите /help',
            f'и Вы увидите, какие команды Вам доступны'
        ]
    else:
        text = [
            '\U0001F622 Ваша регистрация отклонена...',
            '',
            f'Если Вы считаете, что это произошло по ошибке',
            f'Напишите об этом Администратору: @{Config.SUPERUSER_USERNAME}'
        ]
    text = '\n'.join(text)
    await context.bot.send_message(user.telegram_id, text, parse_mode=ParseMode.HTML)


async def show_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def new_fullname_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f'new_fullname_for_user is triggered by user: {update.effective_user}')
    query = update.callback_query
    await query.answer()
    _, attr, user_id = query.data.split('_')
    user_id = int(user_id)
    context.user_data['new_fullname_for'] = user_id
    text = [
        f'{query.message.text}',
        '',
        'Напишите имя в формате Фамилия И.О.',
        'для отображения в таблице',
    ]
    text = '\n'.join(text)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    return WAIT_NEW_FULLNAME


async def get_new_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'get_new_fullname is triggered by user: {update.effective_user}')
    new_fullname = update.message.text
    user = context.bot_data['new_users'].get(context.user_data['new_fullname_for'])
    if not user:
        logger.warning(
            f'User with telegram_id={context.user_data['new_fullname_for']} not found in bot_data["new_users"]. '
            f'Probably already approved or declined')
        return ConversationHandler.END

    user.fullname = new_fullname
    # TODO refactor: выделить отдельные функции создания пользователя и высылки сообщения
    text = [
        '<b>Регистрация нового пользователя!</b>',
        '',
        f'<code>Telegram ID:       </code>{user.telegram_id}',
        f'<code>Имя в Telegram:    </code>{user.fullname}',
        f'<code>Username Telegram: </code>{user.username}',
        f'<code>Роль:              </code>{user.role}'
    ]
    text = '\n'.join(text)
    buttons = {
        'Подтвердить': f'approve_{user.telegram_id}',
        'Изменить имя': f'update-name_{user.telegram_id}',
        'Отказать': f'decline_{user.telegram_id}'
    }
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=make_inline_keyboard(buttons, exit_btn=False, callback_prefix=Config.USERS_CALLBACK_PREFIX)
    )
    return ConversationHandler.END


async def change_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def change_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


update_fullname_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(new_fullname_for_user,
                                       pattern='^' f'{Config.USERS_CALLBACK_PREFIX}update-[a-z]+_[0-9]+' '$')],
    states={
        WAIT_NEW_FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_fullname)]
    },
    fallbacks=[exit_command_handler, exit_callback_handler]
)
