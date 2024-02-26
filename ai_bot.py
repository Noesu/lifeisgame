import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
import database

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=config.TOKEN)
dp = Dispatcher()


@dp.callback_query(F.data == "menu")
async def cmd_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="База данных",
        callback_data="database"))
    builder.add(types.InlineKeyboardButton(
        text="Настройки",
        callback_data="settings"))
    menu_message = (f'Life is game by George Bars\n'
                    f'Всего сохранено вопросов: {len(database.questions)}\n\n')
    print(database.questions)
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "database")
async def edit_database(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Добавить",
        callback_data="add_question"))
    builder.add(types.InlineKeyboardButton(
        text="Редактировать",
        callback_data="edit question"))
    menu_message = (f'Life is game by George Bars\n'
                    f'Всего сохранено вопросов: {len(database.questions)}')
    await callback.message.answer(menu_message, reply_markup=builder.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "add_question")
async def send_random_value(callback: types.CallbackQuery):
    question_text, answer_text = new_question()
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Меню",
        callback_data="menu"))
    if question_text and answer_text:
        database.add_question(question_text, answer_text)
        await callback.message.answer(
            f"Вопрос добавлен в базу данных: \n\n"
            f"Вопрос: {question_text}\nОтвет: {answer_text}",
            reply_markup=builder.as_markup())
        await callback.answer()
    else:
        await callback.message.answer("Ошибка при генерации вопроса и/или ответа.", reply_markup=builder.as_markup())
        await callback.answer()


@dp.callback_query(F.data == "edit_question")
async def send_random_value(callback: types.CallbackQuery):
    q_list = []
    builder = InlineKeyboardBuilder()

    for x in range(len(database.questions)):
        q_list.append(f"{str(x+1)}. {database.questions[x][1][0:20]}\n")
        builder.add(types.InlineKeyboardButton(text=str(x+1), callback_data=f"edit_{x}"))
    await callback.message.answer("".join(q_list), reply_markup=builder.as_markup())
    await callback.answer()


def new_question():
    return "Сколько будет 3+2", "5"


@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.reply("Введите номер вопроса:")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
