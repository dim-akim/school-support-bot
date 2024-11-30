from bot.telegram_bot_calendar import DetailedTelegramCalendar, DAY


ru_months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
ru_days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
RU_STEP = {'y': 'год', 'm': 'месяц', 'd': 'день'}


class MyCalendar(DetailedTelegramCalendar):
    first_step = DAY
    # previous and next buttons style. they are emoji now!
    prev_button = "⬅️"
    next_button = "➡️"
    # you do not want empty cells when month and year are being selected
    # empty_day_button = ""
    empty_month_button = ""
    empty_year_button = ""
    empty_nav_button = "×"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days_of_week['Ru'] = ru_days_of_week
        self.months['Ru'] = ru_months
