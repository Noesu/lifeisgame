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
import config
import sqlite3 as sq

logging.basicConfig(level=logging.ERROR)

bot = Bot(token=config.TOKEN, parse_mode="HTML")
dp = Dispatcher()

Q_RANGE = 10


class Question(StatesGroup):
    rowid = State()
    q_used = State()
    q_text = State()
    a_text = State()
    old_q = State()
    old_a = State()


@dp.message(CommandStart())
async def command_start(message: types.Message):
    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("SELECT COUNT (*) FROM questions")
        count = cur.fetchone()[0]
    menu_message = (f'<b>Life is game by <i>George Bars</i></b>\n'
                    f'Система управления квизами v 0.1\n\n'
                    f'Всего сохранено вопросов: {count}\n'
                    f'Ближайший квиз запланирован на DD.Month HH:MM')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="База данных",
        callback_data="database_"))
    builder.add(types.InlineKeyboardButton(
        text="Управление",
        callback_data="settings"))
    await message.answer(menu_message, reply_markup=builder.as_markup())
    # await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('database_'))
async def read_database(callback: types.CallbackQuery, q_offset: int = 0):
    builder = InlineKeyboardBuilder()

    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("SELECT COUNT (*) FROM questions")
        count = cur.fetchone()[0]

    match callback.data.split('_')[1]:
        case 'prev':
            q_offset = max(0, q_offset-Q_RANGE)
        case 'next':
            q_offset = min(q_offset+Q_RANGE, count-Q_RANGE)
        case _:
            q_offset = 0

    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("SELECT Question, rowid FROM questions ORDER BY rowid ASC LIMIT ? OFFSET ?", (Q_RANGE, q_offset))
        questions = cur.fetchall()

    menu_message = ""
    for index, (q_text, rowid) in enumerate(questions, q_offset):
        menu_message += f'{index + 1}. {q_text[:40]}\n'
        builder.add(types.InlineKeyboardButton(text=str(index + 1), callback_data=f"question_{rowid}"))
    builder.adjust(5)

    prev_btn = types.InlineKeyboardButton(text=f"<<< {Q_RANGE}", callback_data="database_prev")
    next_btn = types.InlineKeyboardButton(text=f"{Q_RANGE} >>>", callback_data="database_next")
    builder.row(prev_btn, next_btn)

    add_q = types.InlineKeyboardButton(text=f"Добавить вопрос", callback_data="add_question")
    builder.row(add_q)

    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('question_'))
async def read_question(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    rowid = int(callback.data.split('_')[1])
    print(rowid)
    await state.update_data(rowid=rowid)
    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("SELECT Question, Answer, Used FROM Questions WHERE rowid = ?", (rowid,))
        row = cur.fetchone()
    await state.update_data(old_q=row[0])
    await state.update_data(old_a=row[1])
    menu_message = f'Вопрос: <code>{row[0]}</code>\n' \
                   f'Ответ: <code>{row[1]}</code>\n' \
                   f'Опубликован: {row[2]}'
    edit_q = types.InlineKeyboardButton(text="Редактировать вопрос", callback_data=f"edit_q")
    del_q = types.InlineKeyboardButton(text="Удалить вопрос", callback_data=f"del_q")
    clear_q_flag = types.InlineKeyboardButton(text="Сбросить признак", callback_data=f"clear_q_flag")
    send_q = types.InlineKeyboardButton(text="Опубликовать", callback_data=f"send_q{rowid}")
    builder.add(edit_q, del_q, clear_q_flag).adjust(2)
    builder.row(send_q)
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('edit_q'))
async def edit_question(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Введите вопрос:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Question.q_text)


@dp.message(Question.q_text)
async def question_set(message: Message, state: FSMContext):
    q_text = message.text
    await state.update_data(q_text=q_text)
    await message.answer("Введите ответ:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Question.a_text)


@dp.message(Question.a_text)
async def question_check(message: Message, state: FSMContext):
    a_text = message.text
    await state.update_data(a_text=a_text)
    data = await state.get_data()
    menu_message = f'Старый вопрос: <code>{data.get("old_q")}</code>\n' \
                   f'Новый вопрос: <code>{data.get("q_text")}</code>\n\n' \
                   f'Старый ответ: <code>{data.get("old_a")}</code>\n' \
                   f'Новый ответ: <code>{a_text}</code>'
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Отмена", callback_data=f'question_{data.get("rowid")}'))
    builder.add(types.InlineKeyboardButton(text="Сохранить", callback_data=f'save_question'))
    await message.answer(text=menu_message, reply_markup=builder.as_markup())
    await state.set_state()


@dp.callback_query(F.data == "save_question")
async def save_question(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("UPDATE questions SET Question = ?, Answer = ?, Used = ? WHERE rowid = ?",
                    (data.get('q_text'), data.get('a_text'), 0, data.get('rowid')))
        db.commit()
    builder = InlineKeyboardBuilder()
    menu_message = "Вопрос сохранён в базу данных"
    builder.add(types.InlineKeyboardButton(text="Назад", callback_data=f"question_{data.get('rowid')}"))
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "add_question")
async def add_question(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("INSERT INTO questions DEFAULT VALUES")
        cur.execute("SELECT last_insert_rowid()")
        rowid = cur.fetchone()[0]
    await state.update_data(rowid=rowid)
    await edit_question()


@dp.callback_query(F.data == "del_q")
async def delete_question(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("DELETE FROM questions WHERE rowid = ?", (data.get('rowid'),))
        db.commit()
    menu_message = "Вопрос удалён"
    builder.add(types.InlineKeyboardButton(text="Назад", callback_data=f'database_'))
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "clear_q_flag")
async def delete_used(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    with sq.connect("questions.db") as db:
        cur = db.cursor()
        cur.execute("UPDATE questions SET Used = ? WHERE rowid = ?", ('нет', data.get('rowid')))
        db.commit()
    menu_message = "Признак сброшен"
    builder.add(types.InlineKeyboardButton(text="Назад", callback_data=f"question_{data.get('rowid')}"))
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
