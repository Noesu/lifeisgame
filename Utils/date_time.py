from datetime import time, datetime, timedelta
from Config.config import lc


async def user_friendly_datetime(datetime_object):
    return datetime_object.strftime('%d.%m в %H:%M')


async def calculate_answer_delay(a_time):
    return (a_time - datetime.now()).total_seconds()


async def extract_time():
    datetime.strptime(lc.schedule_time, "%H:%M").time()


async def calculate_post_times(questions):
    # Преобразуем строку schedule_day обратно в множество целых чисел
    schedule_days = set(map(int, lc.schedule_day.split(','))) if lc.schedule_day else set()

    # Преобразуем строку schedule_time в объект time
    schedule_time = datetime.strptime(lc.schedule_time, "%H:%M").time()

    # Текущая дата
    current_date = datetime.now().date()

    # Получаем ближайшие даты для каждого из выбранных дней недели
    next_dates = []
    for day in schedule_days:
        next_dates.append(await get_next_weekday(current_date, day))

    # Сортируем даты по возрастанию
    next_dates.sort()

    # Количество вопросов
    num_questions = len(questions)

    # Генерируем список объектов datetime для каждого вопроса
    result_datetimes = []
    for i in range(num_questions):
        # Получаем дату из списка next_dates, с цикличностью
        date_for_question = next_dates[i % len(next_dates)]
        # Создаем объект datetime, комбинируя дату и время
        # print(f'date={date_for_question}\n'
        #       f'time={schedule_time}\n')
        datetime_for_question = datetime.combine(date_for_question, schedule_time)
        # print(f'combined={datetime_for_question}\n')
        result_datetimes.append(datetime_for_question)
        # Увеличиваем дату в списке next_dates для следующего использования
        next_dates[i % len(next_dates)] += timedelta(weeks=1)

    formatted_datetimes = [(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond) for dt in
                           result_datetimes]

    return formatted_datetimes


# Функция для получения следующей даты для заданного дня недели
async def get_next_weekday(start_date, weekday):
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return start_date + timedelta(days=days_ahead)

