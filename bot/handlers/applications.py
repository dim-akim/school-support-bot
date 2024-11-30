import logging


from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)


async def approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    userid = update.message.from_user.id
    text = [
        'Вас приветствует бот Технической поддержки',
        'Вальдорфской школы имени А. А. Пинского',
        '',
        'Использование бота допускается только сотрудниками школы,',
        'но вас я пока не вижу в этом списке',
        'Нажми и увидишь, что будет.',
        f'На всякий случай, твой {userid=}'
    ]
    text = '\n'.join(text)
    await update.message.reply_html(
        text=text,
        reply_markup=ReplyKeyboardRemove()
    )