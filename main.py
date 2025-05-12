import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, \
    CallbackQueryHandler
from database import add_birthday, get_birthdays_by_user, delete_birthday, get_all_birthdays_today, get_all_user_ids
from utils import create_keyboard
from config import BOT_TOKEN
import schedule
import time
import threading
import asyncio

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Определяет порядок запуска функций для ConversationHandler
ADD_NAME, ADD_GROUP, ADD_DETAILS, ADD_DATE, DELETE_NAME = range(5)


# помощь
async def help_command(update, context):
    await update.message.reply_text("Используйте /start для отображения меню.")


# Отправляет приветственное сообщение и предлагает команды
async def start(update, context):
    # Проверяем, является ли обновление сообщением или CallbackQuery
    keyboard = [
        [InlineKeyboardButton("Получить информацию", callback_data="get_info")],
        [InlineKeyboardButton("Редактировать данные", callback_data="change")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "Привет! Я - бот, который поможет тебе помнить о днях рождениях, праздниках и других важных событиях.\n"
            "Выбери опцию: ", reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Выберите опцию: ", reply_markup=reply_markup
        )


# стартовое меню дней рождений
async def get_info(update, context):
    keyboard = [
        [InlineKeyboardButton("Посмотреть список", callback_data="list_birthdays")],
        [InlineKeyboardButton("День рождения сегодня", callback_data="today_birthdays")],
        [InlineKeyboardButton("Вернуться в главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Отлично. Что делаем дальше?", reply_markup=reply_markup)


async def change(update, context):
    await update.callback_query.edit_message_text(
        "Используй /add, чтобы добавить день рождения, /delete чтобы удалить.\n"
        "А также /start, чтобы вернуться в главное меню"
    )


# --- Обработчики добавления дня рождения ---

# Начинает процесс добавления дня рождения
async def add_birthday_start(update, context):
    await update.message.reply_text("Введите фамилию и имя человека через пробел:")
    return ADD_NAME


# Сохраняет имя и запрашивает дату
async def add_birthday_surname_name(update, context):
    context.user_data['surname_name'] = update.message.text
    await update.message.reply_text("Введите информацию о группе. Например: 'семья', 'коллеги', 'друзья'.\n"
                                    "Если добавление группы не требуется, отправьте слово 'НЕТ' в любом регистре.")
    return ADD_GROUP


# Запрашивает группу
async def add_group(update, context):
    text = update.message.text
    if text.lower() == "нет":
        context.user_data['group'] = None
    else:
        context.user_data['group'] = update.message.text
    await update.message.reply_text("Здесь вы можете ввести какую-либо дополнительную информацию о человеке,"
                                    "если нужно.\nЛибо отправьте слово 'НЕТ' в любом регистре.")
    return ADD_DETAILS


async def add_details(update, context):
    text = update.message.text
    if text.lower() == "нет":
        context.user_data['details'] = None
    else:
        context.user_data['details'] = update.message.text
    await update.message.reply_text("Введите дату рождения в формате YYYY-MM-DD:")
    return ADD_DATE


# Сохраняет дату
async def add_birthday_date(update, context):
    try:
        date = update.message.text
        add_birthday(update.message.from_user.id, context.user_data['surname_name'], date,
                     group=context.user_data['group'], details=context.user_data['details'])
        await update.message.reply_text("День рождения успешно добавлен!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Пожалуйста, используйте YYYY-MM-DD.")
        return ADD_DATE  # Остаемся на этом шаге


# Отменяет процесс добавления
async def add_birthday_cancel(update, context):
    await update.message.reply_text("Добавление дня рождения отменено.")
    return ConversationHandler.END


# --- Обработчик списка дней рождений ---

async def list_birthdays(update, context):
    birthdays = get_birthdays_by_user(update.callback_query.from_user.id)
    if birthdays:
        message = "Ваши дни рождения:\n"
        for birthday in birthdays:
            message += f"- {birthday.surname_name}: {birthday.date.strftime('%Y-%m-%d')}"
            if birthday.group:
                message += f', группа: {birthday.group}'
            if birthday.details:
                message += f', {birthday.details}'
            message += "\n"
        await update.callback_query.edit_message_text(message)
    else:
        await update.callback_query.edit_message_text("У вас пока нет сохраненных дней рождений.")


# --- Обработчики удаления дня рождения ---

# Начинает процесс удаления дня рождения
async def delete_birthday_start(update, context):
    birthdays = get_birthdays_by_user(update.message.from_user.id)
    if not birthdays:
        await update.message.reply_text("У вас нет сохраненных дней рождений для удаления.")
        return ConversationHandler.END

    context.user_data['birthdays'] = birthdays  # Сохраняем список дней рождений
    keyboard = create_keyboard([birthday.surname_name for birthday in birthdays])
    await update.message.reply_text("Выберите имя человека, чей день рождения хотите удалить, в выпадающем меню:"
                                    , reply_markup=keyboard)
    return DELETE_NAME


# Удаляет выбранный день рождения
async def delete_birthday_name(update, context):
    name = update.message.text
    user_id = update.message.from_user.id
    deleted = delete_birthday(user_id, name)
    if deleted:
        await update.message.reply_text(f"День рождения {name} успешно удален!", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text(f"Не удалось удалить день рождения {name}.")
    return ConversationHandler.END


# Отменяет процесс удаления.
async def delete_birthday_cancel(update, context):
    await update.message.reply_text("Удаление дня рождения отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# --- Обработчик получения дней рождений сегодня ---

# Выводит список дней рождений на сегодня
async def today_birthdays(update, context):
    birthdays = get_all_birthdays_today(update.callback_query.from_user.id)
    if birthdays:
        message = "Сегодня дни рождения отмечают:\n"
        for birthday in birthdays:
            message += f"- {birthday.surname_name})"
            if birthday.group:
                message += f', группа: {birthday.group}'
            if birthday.details:
                message += f', {birthday.details}'
            message += "\n"
        await update.callback_query.edit_message_text(message)
    else:
        await update.callback_query.edit_message_text("Сегодня ни у кого нет дня рождения.")


# словарь для привязки кнопок к функциям
button_actions = {"back_to_main": start,
                  "get_info": get_info,
                  "change": change,
                  "list_birthdays": list_birthdays,
                  "today_birthdays": today_birthdays
                  }


# Обрабатывает нажатия на кнопки меню.
async def button(update, context):
    query = update.callback_query
    await query.answer()  # Необходимо всегда вызывать answer() для CallbackQuery
    action = button_actions.get(query.data)  # Получаем функцию из словаря
    if action:
        await action(update, context)  # Вызываем функцию, если она найдена
    else:
        await query.edit_message_text("Неизвестная опция.")


# --- Отправка ежедневных уведомлений ---
def send_daily_reminders(context, user_id):
    birthdays = get_all_birthdays_today(user_id)
    if birthdays:
        for birthday in birthdays:
            try:
                context.bot.send_message(chat_id=birthday.user_id,
                                         text=f"Сегодня день рождения у {birthday.surname_name}! Не забудьте поздравить!")
                print(f"Отправлено уведомление пользователю {birthday.user_id} о дне рождении {birthday.surname_name}")
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {birthday.user_id}: {e}")


# Задача для планировщика.
def job(application, user_id):
    send_daily_reminders(application, user_id)


# Запускает планировщик задач.
def run_scheduler(application):
    async def scheduled_job():
        # Получаем всех пользователей, для которых нужно выполнить рассылку.
        user_ids = get_all_user_ids()
        for user_id in user_ids:
            birthdays = get_all_birthdays_today(user_id)
            if birthdays:
                for birthday in birthdays:
                    try:
                        await application.bot.send_message(chat_id=birthday.user_id,
                                                           text=f"Сегодня день рождения у {birthday.surname_name}!"
                                                                f" Не забудьте поздравить!")
                        print(
                            f"Отправлено уведомление пользователю {birthday.user_id}"
                            f" о дне рождении {birthday.surname_name}")
                    except Exception as e:
                        print(f"Не удалось отправить уведомление пользователю {birthday.user_id}: {e}")

    def run_async_job():
        asyncio.run(scheduled_job())

    schedule.every().day.at("9:00").do(run_async_job)

    def scheduler_loop():
        while True:
            schedule.run_pending()
            time.sleep(1)

    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()


# Запускает бота
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get_info", get_info))
    application.add_handler(CommandHandler("change", change))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("list", list_birthdays))
    application.add_handler(CommandHandler("today", today_birthdays))

    # ConversationHandler для добавления дня рождения
    add_birthday_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_birthday_start)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_birthday_surname_name)],
            ADD_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_group)],
            ADD_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_details)],
            ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_birthday_date)],
        },
        fallbacks=[CommandHandler("cancel", add_birthday_cancel)],
    )
    application.add_handler(add_birthday_handler)

    # ConversationHandler для удаления дня рождения
    delete_birthday_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_birthday_start)],
        states={
            DELETE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_birthday_name)],
        },
        fallbacks=[CommandHandler("cancel", delete_birthday_cancel)],
    )
    application.add_handler(delete_birthday_handler)

    # Запуск планировщика в отдельном потоке
    run_scheduler(application)

    # Запуск бота
    application.run_polling()


if __name__ == '__main__':
    main()
