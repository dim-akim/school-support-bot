import logging

from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup
from telegram.ext import (CommandHandler,
                          MessageHandler,
                          ConversationHandler,
                          CallbackQueryHandler,
                          ContextTypes,
                          filters)
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest

from bot.utils.keyboards import make_inline_keyboard
from bot.utils.users import is_admin, user_is_teacher
from bot.settings import Config
from bot.handlers.cancel import exit_command_handler, exit_callback_handler
from bot.handlers.restrictions import admin_only
from bot.handlers.start import authorize
from bot.models.task import Task

logger = logging.getLogger(f'{__name__}')

WAIT_ACTION, WAIT_PROBLEM, WAIT_DESCRIPTION, WAIT_ROOM, WAIT_PRIORITY, WAIT_SHOW = range(6)
CLOSE_TASK = 'close'
CANCEL_TASK = 'cancel'


@authorize
async def tasks_choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f'tasks_choose_action is triggered by: {update.effective_user}')
    """
    Стартует диалог по задачам. Есть две опции:
        Создать заявку
        Задачи (доступно только админам)

    :return: :obj:`int`: Состояние FLOOR - выбор этажа
    """
    if user_is_teacher(context.user_data):
        return await tasks_choose_problem(update, context)

    buttons = {
        'Создать заявку': 'application',
        'Задачи': 'get'
    }
    text = [
        'Вам запрещено использовать эту команду',
        '',
        f'Обратитесь к @{Config.SUPERUSER_USERNAME} для получения доступа.'
    ]
    text = '\n'.join(text)
    await update.message.reply_html(
        'Работаем с задачами. Выберите опцию на кнопке',
        reply_markup=make_inline_keyboard(buttons, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
    )

    return WAIT_ACTION


async def tasks_get_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_get_action is triggered by: {update.effective_user}')
    # TODO если здесь не будет дополнительной логики, можно убрать этот шаг и сразу перейти к choose_problem
    query = update.callback_query
    await query.answer()
    return await tasks_choose_problem(update, context)


async def tasks_choose_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_choose_problem is triggered by: {update.effective_user}')
    query = update.callback_query
    if query:
        await query.answer()
    # TODO учесть вариант с неоконченной заявкой
    context.user_data['task_application'] = {}
    text = [
        '<b>Создание заявки</b>\n',
        'К какой категории вы относите вашу проблему?',
        f'Если подходящей категории не нашлось, напишите текстом'
    ]
    text = '\n'.join(text)
    buttons = [
        'Принтер',
        'Доска',
        'Ноутбук',
        'Компьютер'
    ]
    if query:
        await query.edit_message_text(
            text,
            reply_markup=make_inline_keyboard(buttons, max_columns=2, callback_prefix=Config.TASKS_CALLBACK_PREFIX),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_html(
            text,
            reply_markup=make_inline_keyboard(buttons, max_columns=2, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
        )
    return WAIT_PROBLEM


async def tasks_get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_get_problem is triggered by: {update.effective_user}')
    if update.message:
        category = update.message.text.strip()
    else:
        query = update.callback_query
        await query.answer()
        category = query.data.split('_')[1]  # TODO привести к виду prefix_action_smth
    context.user_data['task_application']['category'] = category

    return await tasks_choose_description(update, context)


async def tasks_choose_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_choose_description is triggered by: {update.effective_user}')
    category = context.user_data['task_application']['category']

    text = [
        '<b>Создание заявки</b>\n',
        f'<b>Категория</b>: {context.user_data['task_application']['category']}',
        '',
        'Выберите проблему или опишите ее текстом'
    ]
    text = '\n'.join(text)
    problems = {
        'Принтер': ['Заменить картридж', 'Не печатает'],
        'Доска': ['Не включается'],
        'Ноутбук': [],
        'Компьютер': []
    }
    keyboard = None
    if category in problems and problems[category]:
        buttons = {problem: f'desc_{problem}' for problem in problems[category]}
        keyboard = make_inline_keyboard(buttons, callback_prefix=Config.TASKS_CALLBACK_PREFIX)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_html(
            text,
            reply_markup=keyboard
        )
    return WAIT_DESCRIPTION


async def tasks_get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_get_description is triggered by: {update.effective_user}')
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data['task_application']['description'] = query.data.split('_')[2]
    else:
        context.user_data['task_application']['description'] = update.message.text
    return await tasks_choose_room(update, context)


async def tasks_choose_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_choose_room is triggered by: {update.effective_user}')
    text = [
        '<b>Создание заявки</b>\n',
        f'Категория: {context.user_data['task_application']['category']}',
        f'<b>Описание</b>: {context.user_data['task_application']['description']}',
        '',
        'Выберите кабинет или напишите его номер',
        '<i>или номер этажа, если это коридор</i>'
    ]
    text = '\n'.join(text)
    buttons = {
        'Учительская': 'room_300',
        'Директор': 'room_104',
        'Секретариат': 'room_105',
        'Бухгалтерия': 'room_107'
    }
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=make_inline_keyboard(buttons, max_columns=2, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
        )
    else:
        msg = await update.message.reply_html(
            text,
            reply_markup=make_inline_keyboard(buttons, max_columns=2, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
        )
        context.user_data['task_application']['message'] = msg
    return WAIT_ROOM


async def tasks_wrong_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_wrong_room is triggered by: {update.effective_user}')
    # wrong_number = update.message.text
    await update.message.delete()
    return WAIT_ROOM


async def tasks_get_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_get_room is triggered by: {update.effective_user}')
    query = update.callback_query
    if query:
        await query.answer()
        room = query.data.split('_')[2]
    else:
        room = update.message.text
    context.user_data['task_application']['room'] = int(room)
    if context.user_data['role'] in ('Админ', 'Суперадмин'):  # TODO вынести в константы / конфиг
        return await tasks_choose_priority(update, context)
    return await create_task(update, context)


async def tasks_choose_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_choose_priority is triggered by: {update.effective_user}')
    text = [
        '<b>Создание заявки</b>\n',
        f'Категория: {context.user_data['task_application']['category']}',
        f'Описание: {context.user_data['task_application']['description']}',
        f'<b>Кабинет</b>: {context.user_data['task_application']['room']}',
        '',
        'Укажите приоритет задачи (по умолчанию 2)',
    ]
    text = '\n'.join(text)
    buttons = {
        '0': 'priority_0',
        '1': 'priority_1',
        '2': 'priority_2',
        '3': 'priority_3'
    }

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=make_inline_keyboard(buttons, max_columns=4, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
        )
    else:
        await update.message.reply_html(
            text,
            reply_markup=make_inline_keyboard(buttons, max_columns=4, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
        )
    return WAIT_PRIORITY


async def tasks_get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_get_priority is triggered by: {update.effective_user}')
    query = update.callback_query
    await query.answer()
    context.user_data['task_application']['priority'] = query.data.split('_')[2]
    return await create_task(update, context)


async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_create is triggered by: {update.effective_user}')
    category = context.user_data['task_application']['category']
    description = context.user_data['task_application']['description']
    room = context.user_data['task_application']['room']
    priority = context.user_data['task_application'].get('priority', 2)
    text = [
        '<b>Создание заявки</b>\n',
        f'Категория: {context.user_data['task_application']['category']}',
        f'Описание: {context.user_data['task_application']['description']}',
        f'Кабинет: {context.user_data['task_application']['room']}',
    ]
    text = '\n'.join(text)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_html(text)
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    task = Task.create(
        room,
        f'{category}: {description}',
        f'{context.user_data["table_fullname"]}',
        priority=priority
    )
    context.user_data['task_application'] = {}
    context.bot_data['new_tasks'][task.task_id] = task

    text = [
        '<b>Готово!</b>',
        f'Номер заявки: {task.task_id}',
        f'Дата заявки: {task.created_at.strftime(Config.TIMESTAMP)}\n',
        'Если хотите создать еще одну заявку, используйте команду /tasks'
    ]
    text = '\n'.join(text)
    await context.bot.send_message(update.effective_chat.id, text, parse_mode=ParseMode.HTML)
    return await send_new_task_to_admins(task.task_id, context)


async def send_new_task_to_admins(task_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_ids = [
        user.telegram_id for user in context.bot_data['users'].values() if user.role in ('Админ', 'Суперадмин')]
    task = context.bot_data['new_tasks'].get(task_id, None)
    if not task:
        logger.error(f'Task {task_id} not found in context.bot_data["new_tasks"]')
        return ConversationHandler.END
    text = [
        '<b>Новая заявка!</b>',
        '',
        f'<code>Номер:       </code>{task.task_id}',
        f'<code>Создана:     </code>{task.created_at.strftime(Config.TIMESTAMP)}',
        f'<code>Автор:       </code>{task.author}',
        f'<code>Кабинет:     </code>{task.room}',
        f'<code>Описание:    </code>{task.text}',
    ]
    text = '\n'.join(text)

    buttons = {
        'Принять': f'accept_{task.task_id}'
    }
    for admin in admin_ids:
        try:
            await context.bot.send_message(
                admin,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=make_inline_keyboard(buttons, exit_btn=False, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
            )
        except BadRequest as e:
            text = f'Exception: Bad Request for Telegram ID <code>{admin}</code>: {e.message}'
            logger.error(text)
            await context.bot.send_message(Config.SUPERUSER_ID, text, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


@admin_only
async def tasks_show_which(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f'tasks_show_which is triggered by: {update.effective_user}')
    query = update.callback_query
    await query.answer()
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    context.user_data['tasks'] = _get_open_tasks_by_executor(context.user_data['table_fullname'])
    buttons = {
        'Невзятые': 'show_nobodys',
        'Мои': 'show_0'
    }
    if update.effective_user.id == Config.SUPERUSER_ID:
        buttons.update({'Все': 'show_all'})
    await query.edit_message_text(
        'Просмотр задач. Выберите опцию на кнопке',
        reply_markup=make_inline_keyboard(buttons, callback_prefix=Config.TASKS_CALLBACK_PREFIX)
    )
    return WAIT_SHOW


@admin_only
async def show_one_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    query = update.callback_query
    await query.answer()
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    _, action, task_id = query.data.split('_')
    task_id = int(task_id)

    if not task_id:
        task_id = next(iter(context.user_data['tasks']))
    logger.debug(f'Pulling task {task_id} from context.user_data["tasks"]')
    task = context.user_data['tasks'].get(task_id, None)
    logger.info(f'Showing {task} to: {update.effective_user}')
    text = [
        f'<b>Заявка номер {task.task_id}</b>',
        '',
        f'<code>Создана:     </code>{task.created_at.strftime(Config.TIMESTAMP)}',
        f'<code>Автор:       </code>{task.author}',
        f'<code>Принята:     </code>{task.created_at.strftime(Config.TIMESTAMP)}',
        f'<code>Кабинет:     </code>{task.room}',
        f'<code>Описание:    </code>{task.text}',
        f'<code>Комментарий: </code>{task.comments}',
    ]
    if task.completed_at:
        text += [
            '',
            f'<code>Выполнено!   </code>😎',
            f'<code>Дата:        </code>{task.completed_at.strftime(Config.TIMESTAMP)}',
        ]
    text = '\n'.join(text)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=_make_task_scrolling_keyboard(task_id, context.user_data['tasks'])
    )
    return ConversationHandler.END


@admin_only
async def accept_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f'accept_task is triggered by: {update.effective_user}')
    query = update.callback_query
    await query.answer()
    _, action, task_id = query.data.split('_')
    task_id = int(task_id)
    task = context.bot_data['new_tasks'].pop(task_id, None)
    if not task:
        logger.warning(f'Task {task_id} is not found in context.bot_data["new_tasks"]'
                       f'It could be accepted by another admin')
        return
    task.take(context.user_data['table_fullname'])
    text = [
        f'{query.message.text}',
        '',
        f'<code>Автор:       </code>{task.author}',
        f'<code>Задачу принял </code>{update.effective_user.name}',
        f'<code>Дата:         </code>{task.taken_at.strftime(Config.TIMESTAMP)}',
        '',
        'Команда /tasks покажет все задачи',
    ]
    text = '\n'.join(text)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, entities=query.message.entities)


@admin_only
async def update_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


@admin_only
async def close_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f'finish_task is triggered by: {update.effective_user}')
    query = update.callback_query
    await query.answer()
    _, action, task_id = query.data.split('_')
    task_id = int(task_id)
    task = context.user_data['tasks'][task_id]
    if not task:
        logger.warning(f'Task {task_id} is not found in the table.'
                       f'It could be closed by another admin')
        return
    if action == CLOSE_TASK:
        task.complete()
    elif action == CANCEL_TASK:
        task.cancel()
    await show_one_task(update, context)


async def send_notification_to_author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


def _get_open_tasks_by_executor(executor: str) -> dict[int, Task]:
    tasks = Task.get_all_tasks(executor=executor,
                               status='Взято')
    return {task.task_id: task for task in tasks}


def _make_task_scrolling_keyboard(task_id: int, tasks: dict[int, Task]) -> InlineKeyboardMarkup:
    # TODO вынести в клавиатуры?
    task_ids = [key for key in tasks.keys()]
    current_index = task_ids.index(task_id)
    prev_task_id = task_ids[current_index - 1] if current_index else task_ids[-1]
    next_task_id = task_ids[current_index + 1] if current_index < len(task_ids) - 1 else task_ids[0]
    buttons = {
        '⬅️': f'show_{prev_task_id}',
        f'{current_index + 1} из {len(tasks)}': ' ',
        '➡️': f'show_{next_task_id}',
        'Выполнить': f'close_{task_id}',
        'Отклонить': f'cancel_{task_id}',  # TODO кнопка обновить список задач
    }
    return make_inline_keyboard(buttons, exit_btn=False, callback_prefix=Config.TASKS_CALLBACK_PREFIX)


# TODO вынести паттерны в конфиг
tasks_conversation = ConversationHandler(
    entry_points=[CommandHandler('tasks', tasks_choose_action)],
    states={
        WAIT_ACTION: [CallbackQueryHandler(tasks_show_which, pattern='^' 'tasks_get' '$'),
                      CallbackQueryHandler(tasks_get_action, pattern='^' 'tasks_application' '$')],
        WAIT_PROBLEM: [CallbackQueryHandler(tasks_get_problem, pattern='^' 'tasks_[А-Яа-я]+' '$'),
                       MessageHandler(filters.TEXT & ~filters.COMMAND, tasks_get_problem)],
        WAIT_DESCRIPTION: [CallbackQueryHandler(tasks_get_description, pattern='^' 'tasks_desc_[А-Яа-я ]+' '$'),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, tasks_get_description)],
        WAIT_ROOM: [CallbackQueryHandler(tasks_get_room, pattern='^' 'tasks_room_[0-9]+' '$'),
                    MessageHandler(filters.Regex('^' '[1-5][0-2][0-9]+' '$'), tasks_get_room),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, tasks_wrong_room)],
        WAIT_PRIORITY: [CallbackQueryHandler(tasks_get_priority, pattern='^' 'tasks_priority_[0-3]' '$')],
        WAIT_SHOW: [CallbackQueryHandler(show_one_task, pattern='^' 'tasks_show_[0-9]+' '$')]
    },
    fallbacks=[exit_callback_handler, exit_command_handler]
)
