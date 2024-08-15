# import asyncio
# from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
# from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
# from aiogram.types import (KeyboardButton,
#                            ReplyKeyboardRemove,
#                            Message,
#                            InlineKeyboardMarkup,
#                            InlineKeyboardButton,
#                            ReplyKeyboardMarkup)
from stacks import *
from .keyboards import *
from DB.models import Question, Config, Task, Session
from Config import lc
from Bot import dp
import DB.db_utils as db_utils
from States.states import QuestionState, ConfigState
# from Utils.date_time import user_friendly_datetime, calculate_answer_delay
from Utils.utils import *
from .bot_commands import *
from .bot_utils import *


@dp.callback_query(lambda callback_query: callback_query.data.startswith('database_'))
async def read_database(callback: types.CallbackQuery, state: FSMContext) -> None:

    await clean_all_stacks_except(top_menu_stack)  # очистка всех стеков сообщений кроме верхнего
    await state.clear()  # очистка значений конечных автоматов Finite State Machine (FSM)
    await db_utils.load_questions(usage_attr="all")  # загрузка всех вопросов из БД
    lc.q_offset = int(callback.data.split('_')[1])  # получение смещения для пагинации

    # Формирование страницы вопросов для отображения при пагинации
    menu_message = f"Всего сохранено вопросов: {await db_utils.load_number_of_questions(usage_attr='total')}\n\n"
    for q_id, q_text, rowid in lc.questions[lc.q_offset:lc.q_offset + lc.q_range]:
        if len(q_text) > 40:  # максимальная длина вопроса для отображения установлена в 40 символов
            menu_message += f'{q_id}. {q_text[:37]}...\n'
        else:
            menu_message += f'{q_id}. {q_text}\n'

    bot_message = await callback.message.answer(menu_message, reply_markup=read_database_keyboard(lc))
    database_stack.append(bot_message)
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('question_'))
async def read_question(callback: types.CallbackQuery, state: FSMContext, question_id=None) -> None:
    await callback.answer()
    await clean_stacks(database_stack, question_stack)

    # получение id загружаемого вопроса: при вызове функции по имени / при вызове функции callback-запросом
    rowid = question_id or int(callback.data.split('_')[1])

    # запись в FSM данных отображаемого вопроса (id, вопрос и ответ)
    await state.update_data(rowid=rowid)
    question = await db_utils.load_question(rowid)
    await state.update_data(q_text=question.q_text, a_text=question.a_text)

    # формирование блока сообщения о дате и времени последней публикации вопроса
    published_attr = "нет" if not question.date_used else await user_friendly_datetime(question.date_used)

    menu_message = (f'Вопрос: <code>{question.q_text}</code>\n'
                    f'Ответ: <code>{question.a_text}</code>\n'
                    f'Опубликован: {published_attr}')

    bot_message = await callback.message.answer(menu_message, reply_markup=read_question_keyboard(lc))
    question_stack.append(bot_message)


@dp.callback_query(F.data == 'edit_q')
async def edit_question(callback: types.CallbackQuery, state: FSMContext) -> None:
    bot_message = await callback.message.answer("Введите вопрос:", reply_markup=cancel_state_keyboard(lc))
    question_stack.append(bot_message)
    await callback.answer()
    await state.set_state(QuestionState.q_text_new)  # Установка FSM на пользовательский ввод текста вопроса


@dp.message(QuestionState.q_text_new)
async def question_set(message: Message, state: FSMContext) -> None:
    question_stack.append(message)

    # Вызов проверки дублирования текста вопроса в БД
    duplicate_found = await db_utils.question_duplicates_found(message.text)

    # Формирование сообщения о наличии дубликата вопроса в БД
    if duplicate_found:
        published_attr = "нет" if not duplicate_found.date_used else user_friendly_datetime(duplicate_found.date_used)
        message_text = (f'Вопрос уже присутствует в базе данных!\n\n'
                        f'<i>Текст вопроса: {duplicate_found.q_text}\n'
                        f'Текст ответа: {duplicate_found.a_text}\n'
                        f'Опубликован: {published_attr}</i>\n\n'
                        f'<b>Введите другой вопрос...</b>')
    # Формирование сообщения о необходимости ввода ответа на вопрос
    else:
        await state.update_data(q_text_new=message.text)  # Сохранение текста вопроса в FSM
        message_text = "Введите ответ:"
        await state.set_state(QuestionState.a_text_new)  # Установка FSM на пользовательский ввод текста ответа

    bot_message = await message.answer(message_text, reply_markup=cancel_state_keyboard(lc))
    question_stack.append(bot_message)


@dp.message(QuestionState.a_text_new)
async def question_check(message: Message, state: FSMContext) -> None:
    question_stack.append(message)
    await state.update_data(a_text_new=message.text)  # Сохранение текста ответа в FSM
    data = await state.get_data()  # Запрос всех данных текущего состояния из FSM

    # Формирование сообщения в зависимости от того, редактируется ли имеющийся вопрос или вносится новый вопрос
    if not data.get("rowid"):  # если это новый вопрос
        menu_message = (f'Вопрос: <code>{data.get("q_text_new")}</code>\n\n'
                        f'Ответ: <code>{message.text}</code>\n')
    else:  # если это редактирование имеющегося вопроса
        menu_message = (f'Старый вопрос: <code>{data.get("q_text")}</code>\n'
                        f'Новый вопрос: <code>{data.get("q_text_new")}</code>\n\n'
                        f'Старый ответ: <code>{data.get("a_text")}</code>\n'
                        f'Новый ответ: <code>{message.text}</code>')

    bot_message = await message.answer(text=menu_message, reply_markup=confirm_question_keyboard(lc))
    question_stack.append(bot_message)


@dp.callback_query(F.data == 'cancel_state')
async def cancel_question_edit(callback: types.CallbackQuery, state: FSMContext):
    await clean_stacks(question_stack)
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "confirm_question")
async def confirm_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    # При отсутствии в FSM соответствующего значения, rowid передается как None, что означает новый вопрос
    rowid, q_text, a_text = data.get("rowid"), data.get("q_text_new"), data.get("a_text_new")

    # Получаем значение rowid нового или редактируемого вопроса
    rowid = await db_utils.save_question(rowid, q_text, a_text)
    await read_question(callback, state, rowid)


@dp.callback_query(F.data == "del_q")
async def delete_question(callback: types.CallbackQuery, state: FSMContext):
    rowid = (await state.get_data()).get('rowid')
    await db_utils.delete_question(rowid)
    menu_message = "Вопрос удалён"
    message_page = await callback.message.answer(menu_message, reply_markup=delete_question_keyboard(lc))
    question_stack.append(message_page)
    await callback.answer()


@dp.callback_query(F.data == "reverse_q_flag")
async def reverse_q_flag(callback: types.CallbackQuery, state: FSMContext):
    rowid = (await state.get_data()).get('rowid')
    await db_utils.set_q_flag(rowid, "auto")

    # Обновление данных вопроса после изменения признака публикации
    question = await db_utils.load_question(rowid)
    published_attr = "нет" if not question.date_used else await user_friendly_datetime(question.date_used)

    # Обновление текста сообщения с новыми данными
    menu_message = (f'Вопрос: <code>{question.q_text}</code>\n'
                    f'Ответ: <code>{question.a_text}</code>\n'
                    f'Опубликован: {published_attr}')

    await callback.message.edit_text(menu_message, reply_markup=read_question_keyboard(lc))
    await callback.answer()


@dp.callback_query(F.data == "single_q")
async def create_single_task(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    task_data = await state.get_data()
    task = await db_utils.create_single_task_db(task_data)
    await run_single_task(callback, task)


@dp.callback_query(F.data == "settings")
async def settings(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await clean_all_stacks_except(top_menu_stack)
    autopost_message = "не установлена"
    if lc.schedule_day and lc.schedule_time:
        if len(lc.schedule_day) == 7:
            week_message = "Ежедневно "
        elif len(lc.schedule_day) == 1:
            week = {
                "0": "понедельникам ",
                "1": "вторникам ",
                "2": "средам ",
                "3": "четвергам ",
                "4": "пятницам ",
                "5": "субботам ",
                "6": "воскресеньям "
            }
            week_message = "По "
            for weekday_index in str(lc.schedule_day):
                week_message += week.get(weekday_index)
        else:
            week = {
                "0": "ПН ",
                "1": "ВТ ",
                "2": "СР ",
                "3": "ЧТ ",
                "4": "ПТ ",
                "5": "СБ ",
                "6": "ВС "
            }
            week_message = "По "
            for weekday_index in str(lc.schedule_day):
                week_message += week.get(weekday_index)
        time_message = f'в {lc.schedule_time}'
        autopost_message = week_message + time_message
    menu_message = (f"<b>Панель настроек</b>\n\n"
                    f"Подключенная группа: <i>{lc.chat_name}</i> (<code>{lc.chat_id}</code>)\n"
                    f"Периодичность автопостинга (<code>{autopost_message}</code>)\n"
                    f"Задержка публикации ответов (минут): <code>{lc.answer_delay}</code>\n"
                    f"Количество вопросов на странице: <code>{lc.q_range}</code>\n"
                    f"Предисловие вопроса: <code>{"установлено" if lc.preface_question else 'не установлено'}</code>\n"
                    f"Предисловие ответа: <code>{"установлено" if lc.preface_answer else 'не установлено'}</code>"
                    )
    bot_message = await callback.message.answer(menu_message, reply_markup=settings_keyboard(lc))
    settings_stack.append(bot_message)
    await callback.answer()


@dp.callback_query(F.data == 'config_chat_id')
async def config_change_chat_id(callback: types.CallbackQuery, state: FSMContext) -> None:
    message = 'Введите новый номер chat_id! <i>(например: -1234567890)</i>'
    settings_page = await callback.message.answer(message, reply_markup=back_to_settings_keyboard(lc))
    settings_stack.append(settings_page)
    await callback.answer()
    await state.set_state(ConfigState.chat_id)


@dp.message(ConfigState.chat_id)
async def chat_id_set(message: Message, state: FSMContext):
    settings_stack.append(message)
    if not valid_number(message.text):
        message_text = ('<b>Номер chat_id должен иметь числовой формат!</b>\n'
                        'Введите номер chat_id! <i>(например: -1234567890)</i>')
        settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
        settings_stack.append(settings_page)
    else:
        chat_id = int(message.text)
        try:
            chat_info = await bot.get_chat(chat_id)
            chat_name = chat_info.full_name
            await state.update_data(chat_id=chat_id, chat_name=chat_name)
            message_text = f'<b>Сохранить чат: <i>{chat_name}</i> с номером chat_id: <code>{chat_id}</code></b>?'
            settings_page = await message.answer(message_text, reply_markup=save_config_keyboard(lc))
            settings_stack.append(settings_page)
        except TelegramAPIError:
            message_text = (f'<b>Чат с номером chat_id <code>{message.text}</code> не найден!</b>\n'
                            f'Введите новый номер chat_id! <i>(например: -1234567890)</i>')
            settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
            settings_stack.append(settings_page)


@dp.callback_query(lambda callback_query: callback_query.data.startswith('config_schedule_day_'))
async def config_schedule_day(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    schedule_day = data.get('schedule_day') or lc.schedule_day
    schedule_day_set = set(map(int, schedule_day)) if schedule_day else set()
    if callback.data.rsplit('_')[-1]:
        day_switch = int(callback.data.rsplit('_')[-1])
        if day_switch in schedule_day_set:
            schedule_day_set.discard(day_switch)
        else:
            schedule_day_set.add(day_switch)
        await state.update_data(schedule_day=''.join(map(str, schedule_day_set)))

    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    menu_message = "Шаг 1 из 2\n\n"
    for i, day in enumerate(days_of_week):
        status = f"<b>ДА</b>" if i in schedule_day_set else "НЕТ"
        menu_message += f'{day}: {status}\n'
    menu_message += "\n<i><b>Установите дни для автопостинга вопросов...</b></i>"
    if not date_set_stack:  # отслеживание первичного запуска метода. если запуск первичный, то отправляется новое
        date_set_page = await callback.message.answer(menu_message, reply_markup=config_schedule_day_keyboard(lc))
        date_set_stack.append(date_set_page)
    else:  # если запуск не первичный, то редактируется старое сообщение
        await callback.message.edit_text(menu_message, reply_markup=config_schedule_day_keyboard(lc))


@dp.callback_query(F.data == 'config_schedule_time')
async def config_schedule_time(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    if data.get("schedule_day"):
        menu_message = (
            f'Шаг 2 из 2\n\n'
            f'<b><i>Введите время для автопостинга вопросов в формате HH:MM...</i></b>'
        )
        await state.set_state(ConfigState.schedule_time)
    else:
        menu_message = "Не выбран ни один день недели. Автопостинг отключен!"
    settings_page = await callback.message.answer(menu_message, reply_markup=back_to_settings_keyboard(lc))
    settings_stack.append(settings_page)


@dp.message(ConfigState.schedule_time)
async def config_schedule_time_set(message: Message, state: FSMContext):
    settings_stack.append(message)
    if not await valid_time(message.text):
        message_text = '<b>Время для автопостинга вопросов должно быть указано в формате HH:MM!</b>\n\n'
        settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
        settings_stack.append(settings_page)
    else:
        await state.update_data(schedule_time=message.text)
        message_text = f'<b>Сохранить время для автопостинга вопросов:<i> {message.text}</i></b>?'
        settings_page = await message.answer(message_text, reply_markup=save_config_keyboard(lc))
        settings_stack.append(settings_page)


@dp.callback_query(F.data == "save_config")
async def save_config(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lc.chat_id = data.get("chat_id", lc.chat_id)
    lc.answer_delay = data.get("answer_delay", lc.answer_delay)
    lc.q_range = data.get("q_range", lc.q_range)
    lc.chat_name = data.get("chat_name", lc.chat_name)
    lc.schedule_time = data.get("schedule_time", lc.schedule_time)
    lc.schedule_day = data.get("schedule_day", lc.schedule_day)
    lc.preface_question = data["preface_question"] if "preface_question" in data else lc.preface_question
    lc.preface_answer = data["preface_answer"] if "preface_answer" in data else lc.preface_answer
    await db_utils.update_config(
        lc.chat_id,
        lc.answer_delay,
        lc.q_range,
        lc.schedule_time,
        lc.schedule_day,
        lc.preface_question,
        lc.preface_answer
    )
    await callback.answer()
    await settings(callback, state)


@dp.callback_query(F.data == 'config_answer_delay')
async def config_change_answer_delay(callback: types.CallbackQuery, state: FSMContext) -> None:
    message = '<b>Введите интервал задержки публикации ответа в минутах</b>'
    settings_page = await callback.message.answer(message, reply_markup=back_to_settings_keyboard(lc))
    settings_stack.append(settings_page)
    await callback.answer()
    await state.set_state(ConfigState.answer_delay)


@dp.message(ConfigState.answer_delay)
async def answer_delay_set(message: Message, state: FSMContext):
    settings_stack.append(message)
    if not valid_number(message.text):
        message_text = ('<b>Время задержки публикации ответа должно иметь числовой формат!</b>\n'
                        'Введите время задержки публикации ответа в минутах!')
        settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
        settings_stack.append(settings_page)
    elif int(message.text) == 0:
        message_text = ('<b>Задержка публикации ответа не может быть равной 0</b>\n'
                        'Введите время задержки публикации ответа в минутах!')
        settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
        settings_stack.append(settings_page)
    else:
        answer_delay = abs(round(int(message.text)))
        await state.update_data(answer_delay=answer_delay)
        message_text = f'<b>Сохранить время задержки публикации ответа (минут):<i> {answer_delay}</i></b>?'
        settings_page = await message.answer(message_text, reply_markup=save_config_keyboard(lc))
        settings_stack.append(settings_page)


@dp.callback_query(F.data == 'config_q_range')
async def config_change_q_range(callback: types.CallbackQuery, state: FSMContext) -> None:
    message = '<b>Введите количество вопросов на одну страницу</b>'
    settings_page = await callback.message.answer(message, reply_markup=back_to_settings_keyboard(lc))
    settings_stack.append(settings_page)
    await callback.answer()
    await state.set_state(ConfigState.q_range)


@dp.message(ConfigState.q_range)
async def q_range_set(message: Message, state: FSMContext):
    settings_stack.append(message)
    if not valid_number(message.text):
        message_text = ('<b>Количество вопросов на одну страницу должно иметь числовой формат!</b>\n'
                        'Введите количество вопросов на одну страницу!')
        settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
        settings_stack.append(settings_page)
    elif int(message.text) == 0:
        message_text = ('<b>Количество вопросов на одну страницу не может быть равным 0</b>\n'
                        'Введите количество вопросов на одну страницу!')
        settings_page = await message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
        settings_stack.append(settings_page)
    else:
        q_range = abs(round(int(message.text)))
        await state.update_data(q_range=q_range)
        message_text = f'<b>Сохранить отображение вопросов на одну страницу:<i> {q_range}</i></b>?'
        settings_page = await message.answer(message_text, reply_markup=save_config_keyboard(lc))
        settings_stack.append(settings_page)


@dp.callback_query(lambda callback_query: callback_query.data.startswith('config_preface_'))
async def config_set_preface(callback: types.CallbackQuery, state: FSMContext) -> None:
    preface_type = callback.data.split('_')[2]
    if preface_type == "question":
        preface_question_indicator = lc.preface_question if lc.preface_question else "не установлено"
        message_text = (f'Предисловие для публикуемого вопроса: <code>{preface_question_indicator}</code>\n'
                        f'<b>Введите предисловие для публикуемого вопроса</b>')
        await state.set_state(ConfigState.preface_question)
    elif preface_type == "answer":
        preface_answer_indicator = lc.preface_answer if lc.preface_answer else "не установлено"
        message_text = (f'Предисловие для публикуемого ответа: <code>{preface_answer_indicator}</code>\n'
                        f'<b>Введите предисловие для публикуемого ответа</b>')
        await state.set_state(ConfigState.preface_answer)
    else:
        message_text = f"Error! preface_type = {preface_type}"
    settings_page = await callback.message.answer(message_text,
                                                  reply_markup=preface_keyboard(preface_type, lc))
    settings_stack.append(settings_page)
    await callback.answer()


@dp.message(ConfigState.preface_question)
async def config_confirm_preface_question(message: Message, state: FSMContext):
    settings_stack.append(message)
    message_text = (f'Предисловие к публикуемым вопросам:<i> {message.text}</i>\n'
                    '<b>Для изменения предисловия повторите ввод</b>')
    await state.update_data(preface_question=message.text)
    settings_page = await message.answer(message_text, reply_markup=save_config_keyboard(lc))
    settings_stack.append(settings_page)


@dp.message(ConfigState.preface_answer)
async def config_confirm_preface_answer(message: Message, state: FSMContext):
    settings_stack.append(message)
    message_text = (f'Предисловие к публикуемым ответам:<i> {message.text}</i>\n'
                    '<b>Для изменения предисловия повторите ввод</b>')
    await state.update_data(preface_answer=message.text)
    settings_page = await message.answer(message_text, reply_markup=save_config_keyboard(lc))
    settings_stack.append(settings_page)


@dp.callback_query(lambda callback_query: callback_query.data.startswith('delete_preface_'))
async def config_delete_preface(callback: types.CallbackQuery, state: FSMContext) -> None:
    preface_type = callback.data.split('_')[2]
    match preface_type:
        case "question":
            await state.update_data(preface_question="")
        case "answer":
            await state.update_data(preface_answer="")
    await save_config(callback, state)
    await settings(callback, state)


@dp.callback_query(F.data == "scheduler")
async def scheduler(callback: types.CallbackQuery):
    await clean_all_stacks_except(top_menu_stack)
    scheduled_autopost_task = await db_utils.check_active_tasks_count("multi")
    if scheduled_autopost_task:
        next_autopost_task_q_time = await db_utils.load_next_multi_task_q_time()
        menu_message = (f'<b>Планировщик</b>\n\n'
                        f'Автопубликация включена\n'
                        f'Запланировано {scheduled_autopost_task} вопросов\n'
                        f'Следующий вопрос будет опубликован {await user_friendly_datetime(next_autopost_task_q_time)} ')
    else:
        menu_message = (f"<b>Планировщик</b>\n\n"
                        f"Автопубликация выключена\n")
    scheduler_page = await callback.message.answer(menu_message,
                                                   reply_markup=switch_autopost_keyboard(lc, scheduled_autopost_task))
    scheduler_stack.append(scheduler_page)
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('autopost_'))
async def switch_autopost(callback: types.CallbackQuery, state: FSMContext) -> None:

    if callback.data == "autopost_on":
        await db_utils.create_multi_tasks_db()
        tasks = await db_utils.load_next_active_tasks('multi')
        message_text = (f"Вопросов в очереди на публикацию: {len(tasks)}.\n"
                        f"Ближайшая публикация запланирована на "
                        f"{await user_friendly_datetime(tasks[0][0])}")
        pass  # await Запустить исполнение первой задачи multitask!
    else:
        await db_utils.delete_multi_tasks_db()
        message_text = "Автопубликация отключена"
        pass  # await Остановить выполнение очередной задачи multitask, если запущена

    scheduler_page = await callback.message.answer(message_text, reply_markup=back_to_settings_keyboard(lc))
    scheduler_stack.append(scheduler_page)
    await callback.answer()


# @dp.callback_query(F.data == 'back_to_command_start')
# async def back_to_command_start(callback: types.CallbackQuery):
#     await clean_stacks(scheduler_stack)
#     await command_start(callback.message)
#     await callback.answer()

