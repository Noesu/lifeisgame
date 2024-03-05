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
import database

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=config.TOKEN, parse_mode="HTML")
dp = Dispatcher()


class Question(StatesGroup):
    q_number = State()
    set_q_text = State()
    set_a_text = State()


@dp.message(CommandStart())
async def command_start(message: types.Message):
    menu_message = (f'<b>Life is game by <i>George Bars</i></b>\n'
                    f'Система управления квизами v 0.1\n\n'
                    f'Всего сохранено вопросов: {len(database.questions)}\n'
                    f'Ближайший квиз запланирован на DD.Month HH:MM')
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="База данных",
        callback_data="database"))
    builder.add(types.InlineKeyboardButton(
        text="Управление",
        callback_data="settings"))
    await message.answer(menu_message, reply_markup=builder.as_markup())
    # await callback.answer()


# @dp.callback_query(F.data == "database")
# async def edit_database(callback: types.CallbackQuery):
#     menu_message = f'Всего сохранено вопросов: {len(database.questions)}'
#     builder = InlineKeyboardBuilder()
#     builder.add(types.InlineKeyboardButton(
#         text="Просмотр вопросов",
#         callback_data="read_database"))
#     builder.add(types.InlineKeyboardButton(
#         text="Добавление вопроса",
#         callback_data="add_question"))
#     await callback.message.answer(menu_message, reply_markup=builder.as_markup())
#     await callback.answer()


@dp.callback_query(F.data == "database")
async def read_database(callback: types.CallbackQuery):
    q_index = 0
    q_range = 10
    menu_message = "".join(
        f'{index + 1}. {q_text[:40]}\n' for index, (q_text, a_text, pub_times) in
        enumerate(database.questions[q_index:q_index + q_range]))
    builder = InlineKeyboardBuilder()
    for i in range(q_index, min(q_range, len(database.questions))):
        builder.add(types.InlineKeyboardButton(text=str(i + 1), callback_data=f"question_{i + 1}"))
    builder.adjust(5)
    if q_index > 0:
        prev_btn = types.InlineKeyboardButton(text="<<< 10", callback_data="prev_10")
    else:
        prev_btn = types.InlineKeyboardButton(text="<<< 10", callback_data="prev_10")
    edit_btn = types.InlineKeyboardButton(text="Edit", callback_data="edit_question")
    if len(database.questions) > q_index + q_range:
        next_btn = types.InlineKeyboardButton(text="10 >>>", callback_data="next_10")
    else:
        next_btn = types.InlineKeyboardButton(text="10 >>>", callback_data="next_10")
    builder.row(prev_btn, edit_btn, next_btn)
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('question_'))
async def read_question(callback: types.CallbackQuery, state: FSMContext):
    Question.q_number = int(callback.data.split('_')[1]) - 1
    await state.update_data(q_number=Question.q_number)
    menu_message = f'<b>Вопрос №{Question.q_number + 1}</b>\n\n' \
                   f'Вопрос: <code>{database.questions[Question.q_number][0]}</code>\n' \
                   f'Ответ: <code>{database.questions[Question.q_number][1]}</code>\n' \
                   f'Количество публикаций: {database.questions[Question.q_number][2]}'
    builder = InlineKeyboardBuilder()
    edit_q = types.InlineKeyboardButton(text="Редактировать вопрос", callback_data=f"editq_{Question.q_number}")
    edit_a = types.InlineKeyboardButton(text="Редактировать ответ", callback_data=f"edit_a{Question.q_number}")
    del_q = types.InlineKeyboardButton(text="Удалить вопрос", callback_data=f"del_q{Question.q_number}")
    clear_q_flag = types.InlineKeyboardButton(text="Сбросить признак", callback_data=f"clear_q_flag{Question.q_number}")
    send_q = types.InlineKeyboardButton(text="Опубликовать", callback_data=f"send_q{Question.q_number}")
    builder.add(edit_q, edit_a, del_q, clear_q_flag).adjust(2)
    builder.row(send_q)
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('editq_'))
async def edit_question(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Введите вопрос:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Question.set_q_text)


@dp.message(Question.set_q_text)
async def question_set(message: Message, state: FSMContext):
    new_q = message.text
    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    q_number = data.get('q_number')
    menu_message = f'<b>Вопрос №{q_number + 1}</b>\n\n' \
                   f'Старый вопрос: <code>{database.questions[Question.q_number][0]}</code>\n' \
                   f'Новый вопрос: <code>{new_q}</code>\n'
    builder.add(types.InlineKeyboardButton(text="Отмена", callback_data=f"question_{q_number+1}"))
    builder.add(types.InlineKeyboardButton(text="Сохранить", callback_data=f"save_question_{q_number+1}"))
    await state.update_data(new_q=new_q)
    await message.answer(text=menu_message, reply_markup=builder.as_markup())
    await state.set_state()


@dp.callback_query(lambda callback_query: callback_query.data.startswith('save_question_'))
async def save_question(callback: types.CallbackQuery, state: FSMContext):
    Question.q_number = int(callback.data.split('_')[1]) - 1
    database.questions[]
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()

# @dp.callback_query(F.data == "add_question")
# async def send_random_value(callback: types.CallbackQuery, state: FSMContext) -> None:
#     await state.set_state(Question.q_text)
#     await callback.answer("Введите вопрос:", reply_markup=ReplyKeyboardRemove())
#
#
# @dp.message(Question.q_text)
# async def process_name(message: Message, state: FSMContext) -> None:
#     await state.update_data(name=message.text)
#     await state.set_state(Question.a_text)
#     await message.answer(f"Введите ответ:", reply_markup=ReplyKeyboardRemove())
#
#
# @dp.message(Question.a_text)
# async def process_name(message: Message, state: FSMContext) -> None:
#     await state.update_data(name=message.text)
#     await state.set_state(Question.a_text)
#     await message.answer(f"Введите ответ:", reply_markup=ReplyKeyboardRemove())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
