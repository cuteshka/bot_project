from telegram import ReplyKeyboardMarkup


# Создает клавиатуру с заданными вариантами
def create_keyboard(options):
    keyboard = ReplyKeyboardMarkup([[option] for option in options], one_time_keyboard=True)
    return keyboard
