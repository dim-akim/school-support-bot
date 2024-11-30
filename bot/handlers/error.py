import html
import json
import traceback
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.settings import Config

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message_with_update = (
        'An exception was raised while handling an update\n\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>'
    )
    message_with_context = (
        f'<pre language="python">context.bot_data = {html.escape(str(context.bot_data))}</pre>\n\n'
        f'<pre language="python">context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre language="python">context.user_data = {html.escape(str(context.user_data))}</pre>'
    )
    message_with_traceback = f'<pre language="python">{html.escape(tb_string)}</pre>'

    # Finally, send the message
    await context.bot.send_message(
        chat_id=Config.SUPERUSER_ID, text=message_with_update, parse_mode=ParseMode.HTML
    )
    await context.bot.send_message(
        chat_id=Config.SUPERUSER_ID, text=message_with_context, parse_mode=ParseMode.HTML
    )
    await context.bot.send_message(
        chat_id=Config.SUPERUSER_ID, text=message_with_traceback, parse_mode=ParseMode.HTML
    )
