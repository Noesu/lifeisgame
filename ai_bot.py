import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (KeyboardButton,
                           ReplyKeyboardRemove,
                           Message,
                           InlineKeyboardMarkup,
                           InlineKeyboardButton,
                           ReplyKeyboardMarkup)
import sqlite3 as sq
from dotenv import load_dotenv
import os
from os.path import join, dirname
import config
import time


def get_from_env(key):
    """Load bot token from env"""
    dotenv_path = join(dirname(__file__), 'token.env')
    load_dotenv(dotenv_path)
    return os.environ.get(key)


logging.basicConfig(level=logging.ERROR)
token = get_from_env('TOKEN')
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher()
DATABASE_PAGES = []


class Settings:
    def __init__(self):
        config_db_exists = os.path.exists("config.db")
        if config_db_exists:
            print('Загрузка настроек из файла config.db')
        else:
            print('Файл config.db не найден')
            with sq.connect("config.db") as db:
                cur = db.cursor()
                print('Создание таблицы настроек...')
                cur.execute('''
                        CREATE TABLE IF NOT EXISTS settings (
                            id INTEGER PRIMARY KEY,
                            variable_name TEXT,
                            value TEXT
                        )
                    ''')
                print('Применение настроек по умолчанию...')
                cur.executemany('INSERT INTO settings (variable_name, value) VALUES (?, ?)',
                                config.default_values)

        with sq.connect("config.db") as db:
            cur = db.cursor()
            cur.execute('''
                    SELECT value FROM settings WHERE variable_name IN (?, ?, ?, ?, ?)
                ''', ('Q_RANGE', 'Q_DATABASE', 'T_DATABASE', 'CHAT_ID', 'A_DELAY'))
            values = cur.fetchall()
        print(values)
        self.Q_RANGE = int(values[0][0])
        self.Q_DATABASE = values[1][0]
        self.T_DATABASE = values[2][0]
        self.CHAT_ID = int(values[3][0])
        self.A_DELAY = int(values[4][0])
        self.CHAT_NAME = ""

    async def get_chat_name(self):
        chat_info = await bot.get_chat(configuration.CHAT_ID)
        self.CHAT_NAME = chat_info.title


configuration = Settings()


class Task:
    def __init__(self, question: str, answer: str, delay: int, chat_id: int, chat_name: str, post_time: str):
        self.question = question
        self.question_post_time = post_time
        self.answer = answer
        self.answer_post_time = ""
        self.delay = delay
        self.chat_id = chat_id
        self.chat_name = chat_name

    async def start_quiz(self):
        await bot.send_message(self.chat_id, self.question)
        await self.finish_quiz()

    async def finish_quiz(self):
        await asyncio.sleep(self.delay)
        await bot.send_message(self.chat_id, self.answer)
        self.answer_post_time = time.strftime("%H:%M %d.%m.%Y", time.localtime())
        await self.update_database()

    async def update_database(self):
        with sq.connect(configuration.T_DATABASE) as db:
            cur = db.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    question TEXT,
                    start_time TEXT,
                    answer TEXT,
                    end_time TEXT,
                    chat_name TEXT
                )
            ''')
            cur.execute('''
                    INSERT INTO tasks (question, start_time, answer, end_time, chat_name)
                    VALUES (?, ?, ?, ?, ?)''',
                        [self.question, self.question_post_time, self.answer, self.answer_post_time, self.chat_name])
            db.commit()


class Question(StatesGroup):
    rowid = State()
    q_used = State()
    q_text = State()
    a_text = State()
    q_text_new = State()
    a_text_new = State()


@dp.message(CommandStart())
async def command_start(message: types.Message):
    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute("SELECT COUNT (*) FROM library")
        count = cur.fetchone()[0]
    menu_message = (f'<b>Life is game by <i>George Bars</i></b>\n'
                    f'Система управления квизами v 0.1\n\n'
                    f'Всего сохранено вопросов: {count}\n'
                    f'Ближайший квиз запланирован на DD.Month HH:MM\n'
                    f'Подключенная группа: {configuration.CHAT_NAME}')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="База данных",
        callback_data="database_0"))
    builder.add(types.InlineKeyboardButton(
        text="Управление",
        callback_data="settings"))
    await message.answer(menu_message, reply_markup=builder.as_markup())
    # await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('database_'))
async def read_database(callback: types.CallbackQuery):
    if DATABASE_PAGES:
        database_page = DATABASE_PAGES.pop()
        await bot.delete_message(database_page.chat.id, database_page.message_id)

    q_offset = int(callback.data.split('_')[1])
    builder = InlineKeyboardBuilder()

    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute('SELECT COUNT (*) FROM library')
        count = cur.fetchone()[0]
        cur.execute('SELECT Question, rowid FROM library ORDER BY rowid ASC LIMIT ? OFFSET ?',
                    (configuration.Q_RANGE, q_offset))
        questions = cur.fetchall()

    menu_message = ""
    for index, (q_text, rowid) in enumerate(questions, q_offset):
        menu_message += f'{index + 1}. {q_text[:40] if q_text else "-"}\n'
        builder.add(types.InlineKeyboardButton(text=str(index + 1),
                                               callback_data=f"question_{rowid}"))
    builder.adjust(5)

    if q_offset == 0:
        prev_btn = types.InlineKeyboardButton(text=f"Назад",
                                              callback_data='database_0')
    else:
        prev_btn = types.InlineKeyboardButton(text=f"<<< {configuration.Q_RANGE}",
                                              callback_data=f"database_{q_offset - configuration.Q_RANGE}")

    if q_offset + configuration.Q_RANGE > count:
        next_btn = types.InlineKeyboardButton(text=f"Назад",
                                              callback_data='database_0')
    else:
        next_btn = types.InlineKeyboardButton(text=f"{configuration.Q_RANGE} >>>",
                                              callback_data=f"database_{q_offset + configuration.Q_RANGE}")

    builder.row(prev_btn, next_btn)

    add_q = types.InlineKeyboardButton(text=f"Добавить вопрос",
                                       callback_data="edit_q")
    builder.row(add_q)

    database_page = await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    DATABASE_PAGES.append(database_page)
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('question_'))
async def read_question(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    rowid = int(callback.data.split('_')[1])
    await state.update_data(rowid=rowid)
    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute("SELECT Question, Answer, Used, Post_date FROM library WHERE rowid = ?",
                    (rowid,))
        row = cur.fetchone()
    await state.update_data(q_text=row[0], a_text=row[1])
    menu_message = f'Вопрос: <code>{row[0]}</code>\n' \
                   f'Ответ: <code>{row[1]}</code>\n' \
                   f'Опубликован: {"нет" if not row[2] else row[3]}'
    edit_q = types.InlineKeyboardButton(text="Редактировать вопрос",
                                        callback_data=f"edit_q")
    del_q = types.InlineKeyboardButton(text="Удалить вопрос",
                                       callback_data=f"del_q")
    clear_q_flag = types.InlineKeyboardButton(text="Сбросить признак",
                                              callback_data=f"clear_q_flag")
    send_q = types.InlineKeyboardButton(text="Опубликовать",
                                        callback_data=f"send_q")
    builder.add(edit_q, del_q, clear_q_flag).adjust(2)
    builder.row(send_q)
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('edit_q'))
async def edit_question(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Введите вопрос:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Question.q_text_new)


@dp.message(Question.q_text_new)
async def question_set(message: Message, state: FSMContext):
    q_text_new = message.text
    await state.update_data(q_text_new=q_text_new)
    await message.answer("Введите ответ:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Question.a_text_new)


@dp.message(Question.a_text_new)
async def question_check(message: Message, state: FSMContext):
    a_text_new = message.text
    await state.update_data(a_text_new=a_text_new)
    data = await state.get_data()
    builder = InlineKeyboardBuilder()
    if not data.get("rowid"):
        menu_message = f'Вопрос: <code>{data.get("q_text_new")}</code>\n\n' \
                       f'Ответ: <code>{a_text_new}</code>\n'
        builder.add(types.InlineKeyboardButton(text="Отмена",
                                               callback_data=f'database_0'))
    else:
        menu_message = f'Старый вопрос: <code>{data.get("q_text")}</code>\n' \
                       f'Новый вопрос: <code>{data.get("q_text_new")}</code>\n\n' \
                       f'Старый ответ: <code>{data.get("a_text")}</code>\n' \
                       f'Новый ответ: <code>{a_text_new}</code>'
        builder.add(types.InlineKeyboardButton(text="Отмена",
                                               callback_data=f'question_{data.get("rowid")}'))
    builder.add(types.InlineKeyboardButton(text="Сохранить",
                                           callback_data=f'save_question'))
    await message.answer(text=menu_message, reply_markup=builder.as_markup())
    await state.set_state()


@dp.callback_query(F.data == "save_question")
async def save_question(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    builder = InlineKeyboardBuilder()
    with (sq.connect(configuration.Q_DATABASE) as db):
        cur = db.cursor()
        if data.get("rowid"):
            cur.execute("UPDATE library SET Question = ?, Answer = ?, Used = ? WHERE rowid = ?",
                        (data.get('q_text_new'), data.get('a_text_new'), 0, data.get('rowid')))
            builder.add(types.InlineKeyboardButton(text="Назад",
                                                   callback_data=f"question_{data.get('rowid')}"))
        else:
            cur.execute("INSERT INTO library (Question, Answer, Used) VALUES (?, ? ,?)",
                        (data.get('q_text_new'), data.get('a_text_new'), 0))
            builder.add(types.InlineKeyboardButton(text="Назад",
                                                   callback_data=f"database_0"))
        db.commit()
    menu_message = "Вопрос сохранён в базу данных"
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "add_question")
async def add_question(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute("INSERT INTO library DEFAULT VALUES")
        cur.execute("SELECT last_insert_rowid()")
        rowid = cur.fetchone()[0]
    await state.update_data(rowid=rowid)
    # await state.update_data(rowid=rowid, q_text=0, a_text=0)
    await edit_question(callback, state)


@dp.callback_query(F.data == "del_q")
async def delete_question(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute("DELETE FROM library WHERE rowid = ?", (data.get('rowid'),))
        db.commit()
    menu_message = "Вопрос удалён"
    builder.add(types.InlineKeyboardButton(text="Назад",
                                           callback_data=f'database_0'))
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "clear_q_flag")
async def delete_used(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute("UPDATE library SET Used = ?, Post_date = ? WHERE rowid = ?",
                    (0, 0, data.get('rowid')))
        db.commit()
    menu_message = "Признак сброшен"
    builder.add(types.InlineKeyboardButton(text="Назад",
                                           callback_data=f"question_{data.get('rowid')}"))
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "send_q")
async def send_question(callback: types.CallbackQuery, state: FSMContext):
    time_and_date = time.strftime("%H:%M %d.%m.%Y", time.localtime())
    data = await state.get_data()
    task = Task(data.get('q_text'),
                data.get('a_text'),
                configuration.A_DELAY,
                configuration.CHAT_ID,
                configuration.CHAT_NAME,
                time_and_date)
    asyncio.create_task(task.start_quiz())
    with sq.connect(configuration.Q_DATABASE) as db:
        cur = db.cursor()
        cur.execute("UPDATE library SET Used = ?, Post_date = ? WHERE rowid = ?",
                    (1, time_and_date, data.get('rowid')))
        db.commit()
    builder = InlineKeyboardBuilder()
    menu_message = (f"Вопрос опубликован {time_and_date} в группе {configuration.CHAT_NAME}\n"
                    f"Задержка публикации ответа {configuration.A_DELAY} секунд")
    builder.add(types.InlineKeyboardButton(text="Назад",
                                           callback_data=f"question_{data.get('rowid')}"))
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "settings")
async def settings(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    menu_message = (f"<b>Панель настроек</b>\n\n"
                    f"Подключенная группа: {configuration.CHAT_NAME} (<code>{configuration.CHAT_ID}</code>)\n"
                    f"База данных вопросов: <code>{configuration.Q_DATABASE}</code>\n"
                    f"База данных задач: <code>{configuration.T_DATABASE}</code>\n"
                    f"Задержка публикации ответов: <code>{configuration.A_DELAY}</code> секунд\n"
                    f"Количество вопросов на странице: <code>{configuration.Q_RANGE}</code>")
    buttons = (
        ("Изменить группу", "conf_chat_id"),
        ("Изменить БД вопросов", "conf_q_db"),
        ("Изменить БД задач", "conf_t_db"),
        ("Задержка ответа", "conf_a_delay"),
        ("Вопросов на странице", "conf_q_range")
    )
    inline_keyboard = []
    for button_text, button_callback in buttons:
        inline_keyboard.append([types.InlineKeyboardButton(text=button_text, callback_data=button_callback)])
    builder = types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.answer(menu_message, reply_markup=builder)
    await callback.answer()


async def main():
    await configuration.get_chat_name()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
