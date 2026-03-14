import datetime
import calendar
import json
from messages import CALENDAR_MONTH_NAMES, CALENDAR_WEEKDAY_NAMES


def create_callback_data(action, year, month, day):
    """ Create the callback data associated to each button"""
    return ";".join([action, str(year), str(month), str(day)])


def separate_callback_data(data):
    """ Separate the callback data"""
    return data.split(";")


def create_calendar(year=None, month=None, prefix="", language="en"):
    """
    Create an inline markup with the provided year and month.
    Adds a prefix to callback data for distinction.
    :param int year: Year to use in the calendar, if None, the current year is used.
    :param int month: Month to use in the calendar, if None, the current month is used.
    :param str prefix: A string to prefix all callback data (to differentiate calendars).
    :param str language: Language for calendar text ('en' for English, 'pt' for Portuguese).
    :return: Returns the InlineKeyboardMarkup object with the calendar.
    """
    now = datetime.datetime.now()
    year = now.year if year is None else year
    month = now.month if month is None else month
    
    # Get month and weekday names for the selected language
    month_names = CALENDAR_MONTH_NAMES.get(language, CALENDAR_MONTH_NAMES["en"])
    weekday_names = CALENDAR_WEEKDAY_NAMES.get(language, CALENDAR_WEEKDAY_NAMES["en"])
    
    data_ignore = create_callback_data(f"{prefix}IGNORE", year, month, 0)
    markup = {"inline_keyboard": []}
    # First row - Month and Year
    row = [{"text": month_names[month - 1] + " " + str(year), "callback_data": data_ignore}]
    markup["inline_keyboard"].append(row)
    # Second row - Week Days
    row = []
    for day in weekday_names:
        row.append({"text": day, "callback_data": data_ignore})
    markup["inline_keyboard"].append(row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append({"text": " ", "callback_data": data_ignore})
            else:
                row.append(
                    {"text": "{}".format(day), "callback_data": create_callback_data(f"{prefix}DAY", year, month, day)}
                )
        markup["inline_keyboard"].append(row)
    # Last row - Buttons
    row = [
        {"text": "<", "callback_data": create_callback_data(f"{prefix}PREV-MONTH", year, month, 0)},
        {"text": " ", "callback_data": data_ignore},
        {"text": ">", "callback_data": create_callback_data(f"{prefix}NEXT-MONTH", year, month, 0)},
    ]
    markup["inline_keyboard"].append(row)

    return json.dumps(markup)


def process_calendar_selection(bot, update):
    """
    Process the callback_query. This method generates a new calendar if forward or
    backward is pressed. This method should be called inside a CallbackQueryHandler.
    :param telegram.Bot bot: The bot, as provided by the CallbackQueryHandler
    :param telegram.Update update: The update, as provided by the CallbackQueryHandler
    :return: Returns a tuple (Boolean,datetime.datetime), indicating if a date is selected
                and returning the date if so.
    """
    ret_data = (False, None)
    query = update.callback_query
    (action, year, month, day) = separate_callback_data(query.data)
    curr = datetime.datetime(int(year), int(month), 1)
    if action == "IGNORE":
        bot.answer_callback_query(callback_query_id=query.id)
    elif action == "DAY":
        bot.edit_message_text(text=query.message.text,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id
                              )
        ret_data = True, datetime.datetime(int(year), int(month), int(day))
    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        bot.edit_message_text(text=query.message.text,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              reply_markup=create_calendar(int(pre.year), int(pre.month)))
    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        bot.edit_message_text(text=query.message.text,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id,
                              reply_markup=create_calendar(int(ne.year), int(ne.month)))
    else:
        bot.answer_callback_query(callback_query_id=query.id, text="Something went wrong!")
        # UNKNOWN
    return ret_data