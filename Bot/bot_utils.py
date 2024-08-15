from . import bot
from aiogram import Bot, Dispatcher, types, F
from Config import lc
import DB.db_utils as db_utils
from Utils.date_time import user_friendly_datetime, calculate_answer_delay
import asyncio


async def get_chat_name(chat_id):
    chat_info = await bot.get_chat(chat_id)
    return chat_info.full_name


async def run_single_task(callback, task):
    await send_question(callback, task)
    await send_answer(callback, task)


async def send_question(callback: types.CallbackQuery, task):
    try:
        await bot.send_message(task.chat_id, f'{lc.preface_question}\n\n{task.q_text}')
        await db_utils.set_q_flag(task.question_id, "on")
        menu_message = (f"Вопрос <code>{task.q_text}</code> опубликован {await user_friendly_datetime(task.q_time)} "
                        f"в группе {await get_chat_name(task.chat_id)}\n"
                        f"Ответ будет опубликован {await user_friendly_datetime(task.a_time)}.")
        await callback.message.answer(menu_message)
    except Exception as e:
        print(f"Error sending question: {e}")


async def send_answer(callback, task):
    try:
        delay = await calculate_answer_delay(task.a_time)
        if delay > 0:
            await asyncio.sleep(delay)
        await bot.send_message(task.chat_id, f'{lc.preface_answer}\n\n{task.a_text}')
        await db_utils.delete_single_task_db()
        menu_message = (f"Ответ <code>{task.a_text}</code> опубликован {await user_friendly_datetime(task.a_time)} "
                        f"в группе {await get_chat_name(task.chat_id)}\n")
        await callback.message.answer(menu_message)
    except Exception as e:
        print(f"Error sending answer: {e}")

