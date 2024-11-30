import datetime

import pygsheets

from bot.settings import Config
from bot.database import client


class Printers:
    table: pygsheets.spreadsheet
    sheets_list: list[pygsheets.worksheet]
    cartridge_sheet: pygsheets.worksheet
    summary_sheet: pygsheets.worksheet

    CHANGE_COLUMN = 5  # Столбец с датами замен - Е (5)
    EVENT_COLUMN = 7  # Столбец с событиями - G (6)
    START_ROW = 5  # Первый ряд с данными (ряды 1-4 - заголовки)

    AUDITORY_CELL = 'A2'  # Кабинет
    MODEL_CELL = 'B2'  # Модель принтера
    CARTRIDGE_CELL = 'B4'  # Модель картриджа
    STATUS_CELL = 'B5'  # Состояние (Работает, Кончился картридж, Есть проблемы, В ремонте, Готов к выдаче
    NAME_CELL = 'B7'  # Сетевое имя принтера
    IP_ADDRESS_CELL = 'B8'  # IP-адрес принтера
    SERIAL_NUM_CELL = 'B10'  # Серийный № принтера
    INVENT_NUM_CELL = 'B11'  # Инвентарный № принтера
    NUM_CELL = 'B12'  # Внутренний № принтера

    def __init__(self):
        self.table = client.open_by_key(Config.PRINTERS_GSHEET_KEY)
        self.sheets_list = self.table.worksheets()
        self.cartridge_sheet = self.sheets_list[0]  # Картриджи - лист 0
        self.summary_sheet = self.sheets_list[1]  # Summary - лист 1
        self.sheets_list = self.sheets_list[2:]

        self.registry = self.get_registry()

    def get_registry(self) -> dict[str, dict[str, pygsheets.worksheet]]:
        registry = {}
        for sheet in self.sheets_list:
            title = sheet.title
            room = title[:3]
            if room not in registry:
                registry[room] = {}
            printer = title[4:]
            registry[room][printer] = sheet
        return registry

    def change_cartridge(self, room: str, device: str, date: str) -> tuple[str, str]:
        """
        Проставляет дату замены картриджа <date> на страницу принтера <room device>
        в первую пустую строчку колонки <CHANGE_COLUMN>

        :param room: str, номер кабинета - ключ для соваря <registry>
        :param device: str, название принтера - ключ для словаря <registry[room]>
        :param date: str, дата замены в формате ДД.ММ.ГГГГ
        :return: tuple, предыдущая дата замены и количество месяцев, прошедших с этой даты
        """
        printer_sheet = self.registry[room][device]
        dates = [day for day in printer_sheet.get_col(self.CHANGE_COLUMN) if day]
        last_row = len(dates)
        if isinstance(date, datetime.date):
            date = date.strftime('%d.%m.%Y')

        printer_sheet.update_value((last_row + 1, self.CHANGE_COLUMN), date)

        last_date = printer_sheet.cell((last_row, self.CHANGE_COLUMN)).value
        elapsed = printer_sheet.cell((last_row, self.CHANGE_COLUMN + 1)).value
        return last_date, elapsed


if __name__ == '__main__':

    printers = Printers()
    for item in printers.registry:
        print(item, printers.registry[item])
    buttons = [printer for printer in printers.registry['102']]
    printer_name, = printers.registry['102']
    print(buttons)

    sheet = printers.sheets_list[4]
