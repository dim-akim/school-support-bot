import html
import json
import traceback
import logging

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, ConversationHandler, CallbackQueryHandler

from bot.settings import Config

logger = logging.getLogger(__name__)


async def exit_dialogue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Прерывает любой из диалогов на любом этапе."""
    logger.info(f'Canceled the dialog: {update.effective_user}')
    context.user_data.clear()
    cancel_text = 'Выход из диалога. Отмена'
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_reply_markup()
    else:
        await update.message.reply_text(text=cancel_text)

    return ConversationHandler.END

exit_command_handler = CommandHandler('exit', exit_dialogue)
exit_callback_handler = CallbackQueryHandler(exit_dialogue, pattern='^' '_exit' '$')
