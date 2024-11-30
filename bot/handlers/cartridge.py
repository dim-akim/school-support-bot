import datetime
import logging

from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from bot.gsheets_connector import Printers
from bot.utils.keyboards import make_inline_keyboard
from bot.utils.inline_calendar import MyCalendar, RU_STEP
from bot.handlers.cancel import exit_command_handler, exit_callback_handler

logger = logging.getLogger(__name__)
# TODO refactor - класс Printer, в котором будет информация о конкретном принтере
printers = Printers()  # Экземпляр класса Printers, в котором держатся страницы Реестра принтеров
FLOOR, ROOM, DEVICE, DATE, DONE = range(5)  # Состояния для диалога по картриджам


async def cartridge_choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Стартует диалог по картриджам. Есть две опции:
        Замена - зарегистрировать замену картриджа в конкретном принтере
        Привоз - записать количество привезенных картриджей

    :return: :obj:`int`: Состояние FLOOR - выбор этажа
    """
    buttons = ['Замена', 'Привоз']
    await update.message.reply_text(
        'Что делаем с картриджами?',
        reply_markup=make_inline_keyboard(buttons)
    )

    return FLOOR


async def cartridge_choose_floor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Первый этап из диалога по замене картриджей: **Этаж**-Кабинет-Принтер-Дата-Готово.

    Дает пользователю выбрать этаж, на котором стоит принтер.
    Заменяет кнопки, которые были на полученном сообщении

    :return: Состояние ROOM - выбор кабинета
    """
    query = update.callback_query
    await query.answer()

    buttons = {
        '1': 'change_1_floor',
        '2': 'change_2_floor',
        '3': 'change_3_floor',
        '4': 'change_4_floor',
        '5': 'change_5_floor'
    }
    text = [
        'Замена картриджа\n',
        f'Этаж: выберите'
    ]
    text = '\n'.join(text)
    await query.edit_message_text(
        text,
        reply_markup=make_inline_keyboard(buttons)  # TODO добавить кнопки "Назад"
    )

    return ROOM


async def cartridge_choose_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Второй этап из диалога по замене картриджей: Этаж-**Кабинет**-Принтер-Дата-Готово.

    Дает пользователю выбрать кабинет, в котором стоит принтер.

    :return: Состояние DEVICE - выбор принтера
    """
    query = update.callback_query
    floor_number = query.data[7]
    buttons = [room for room in printers.registry if room[0] == floor_number]
    if not buttons:
        await query.answer(f'На {floor_number} этаже не зарегистрировано работающих принтеров')
        return ROOM

    await query.answer()
    text = [
        'Замена картриджа\n',
        f'Кабинет: выберите'
    ]
    text = '\n'.join(text)
    await query.edit_message_text(
        text,
        reply_markup=make_inline_keyboard(buttons)
    )

    return DEVICE


async def cartridge_choose_device(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Третий этап из диалога по замене картриджей: Этаж-Кабинет-**Принтер**-Дата-Готово.

    Дает пользователю выбрать принтер, если в кабинете их стоит больше одного.
    Если принтер в кабинете единственный, сразу переходит к следующему этапу диалога.

    :return: Состояние DATE - выбор даты замены
    """
    query = update.callback_query
    await query.answer()
    room_number = query.data
    context.user_data['room'] = room_number
    buttons = [printer for printer in printers.registry[room_number]]
    if len(buttons) == 1:
        # Пропускаем диалог выбора принтера, если на этаже он только один
        context.user_data['printer'] = buttons[0]
        return await cartridge_choose_date(update, context)

    else:
        text = [
            'Замена картриджа\n',
            f'Кабинет: {room_number}',
            f'Принтер: выберите'
        ]
        text = '\n'.join(text)
        await query.edit_message_text(
            text,
            reply_markup=make_inline_keyboard(buttons)
        )

    return DATE


async def cartridge_choose_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Четвертый этап из диалога по замене картриджей: Этаж-Кабинет-Принтер-**Дата**-Готово.

    Дает пользователю выбрать дату замены картриджа.

    :return: Состояние DONE - регистрация замены в таблице
    """
    query = update.callback_query
    await query.answer()
    if not context.user_data.get('printer'):
        context.user_data['printer'] = query.data

    calendar, step = MyCalendar(locale='Ru', max_date=datetime.date.today()).build()
    text = [
        'Замена картриджа\n',
        f'Кабинет: {context.user_data["room"]}',
        f'Принтер: {context.user_data["printer"]}',
        f'Дата: Выберите {RU_STEP[step]}'
    ]
    text = '\n'.join(text)
    dialog = await query.edit_message_text(text, reply_markup=calendar)
    context.user_data['dialog'] = dialog
    return DONE


async def calendar_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    result, key, step = MyCalendar(locale='Ru', max_date=datetime.date.today()).process(query.data)
    if not result and key:
        await query.answer()
        text = [
            'Замена картриджа\n',
            f'Кабинет: {context.user_data["room"]}',
            f'Принтер: {context.user_data["printer"]}',
            f'Дата: Выберите {RU_STEP[step]}'
        ]
        text = '\n'.join(text)
        await query.edit_message_text(text, reply_markup=key)
        return DONE
    elif result:
        context.user_data['date'] = result
        return await cartridge_change_done(update, context)


# async def cartridge_wrong_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """
#     Четвертый этап из диалога по замене картриджей: Этаж-Кабинет-Принтер-**Дата**-Готово.
#
#     Повторно запрашивает дату от пользователя в случае, если тот ее указал не по формату
#
#     :return: Состояние DONE - регистрация замены в таблице
#     """
#     chat_id = update.message.chat_id
#     dialog: telegram.Message = context.user_data['dialog']
#     text = dialog.text
#     reply_markup = dialog.reply_markup
#     await update.message.delete()
#     await update.callback_query.answer('Неверный формат даты!')
#     await update.message.reply_text(
#         'Неверный формат даты!'
#     )
#     # new_dialog = await update.message.reply_text(
#     #     text=text,
#     #     reply_markup=reply_markup
#     # )
#     # context.user_data['dialog'] = new_dialog
#     return DONE


async def cartridge_change_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Последний этап из диалога по замене картриджей: Этаж-Кабинет-Принтер-Дата-**Готово**.

    Регистрирует замену картриджа в Google-таблице и выдает сообщение о предыдущей замене.

    :return: Состояние ConversationHandler.END
    """
    # TODO реализовать занесение в таблицу и правильную запись в лог
    date = context.user_data['date']
    room = context.user_data['room']
    printer = context.user_data['printer']
    query = update.callback_query
    text = [
        'Замена картриджа\n',
        f'Кабинет: {room}',
        f'Принтер: {printer}',
        f'Дата: {date}'
    ]
    text = '\n'.join(text)
    await query.edit_message_text(text)

    await context.bot.send_chat_action(update.effective_message.chat_id, ChatAction.TYPING)
    # TODO сделать корутиной запись в таблицу
    last_date, elapsed = printers.change_cartridge(room, printer, date)
    username = update.effective_user.username
    logger.info(f'[ЗАМЕНА] {username=} {room=} {printer=} {date=}')

    await context.bot.send_message(
        update.effective_chat.id,
        f'Прошлая замена: {last_date}\n'
        f'Ресурс картриджа в месяцах: {elapsed}'
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cartridge_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Первый этап из диалога по привозу картриджей: Этаж-Кабинет-Принтер-Дата-**Готово**.

    Регистрирует замену картриджа в Google-таблице и выдает сообщение о предыдущей замене.

    :return: Состояние ConversationHandler.END
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        'Я пока не умею регистрировать привоз картриджей, увы...',
    )
    return ConversationHandler.END


cartridge_conversation = ConversationHandler(
    entry_points=[
        CommandHandler('cartridge', cartridge_choose_action)
    ],
    states={
        FLOOR: [
            exit_callback_handler,
            # ^ means "start of line/string"
            # $ means "end of line/string"
            # So ^ABC$ will only allow 'ABC'
            CallbackQueryHandler(cartridge_choose_floor, pattern='^' 'Замена' '$'),
            CallbackQueryHandler(cartridge_incoming, pattern='^' 'Привоз' '$'),
        ],
        ROOM: [
            exit_callback_handler,
            CallbackQueryHandler(cartridge_choose_room, pattern='^' 'change_[12345]_floor' '$'),
        ],
        DEVICE: [
            exit_callback_handler,
            CallbackQueryHandler(cartridge_choose_device),  # TODO нужен паттерн
        ],
        DATE: [
            exit_callback_handler,
            CallbackQueryHandler(cartridge_choose_date),  # TODO нужен паттерн
        ],
        DONE: [
            exit_callback_handler,
            CallbackQueryHandler(calendar_react, pattern=MyCalendar.func()),
        ],
    },
    fallbacks=[exit_command_handler,
               exit_callback_handler]
)
