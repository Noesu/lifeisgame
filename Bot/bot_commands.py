from aiogram.filters import CommandStart
from Bot import bot, dp
from aiogram import Bot, Dispatcher, types, F
import DB.db_utils as db_utils
import Bot.bot_utils as bot_utils
from Config import lc
from .keyboards import *
from stacks import *
from Bot.bot_utils import get_chat_name
from datetime import datetime
from Utils.date_time import user_friendly_datetime


@dp.message(CommandStart())
# async def command_start(callback: types.CallbackQuery, message: types.Message):
async def command_start(message: types.Message):
    """Стартовое меню"""
    await clean_stacks(*all_stacks)  # удаление всех сообщений текущей сессии
    await db_utils.clean_up_past_tasks()  # удаление всех пропущенных заданий из БД
    lc.chat_name = await get_chat_name(lc.chat_id)  # запрос актуального названия подключенного канала

    # загрузка предстоящих ОДИНОЧНЫХ заданий и формирование блока отчета в стартовом сообщении
    next_active_single_tasks = await db_utils.load_next_active_tasks("single")
    single_task_info = 'Одиночные:'
    if next_active_single_tasks:
        for task in next_active_single_tasks:
            await bot_utils.run_single_task(callback, task)
            single_task_info += (f'\nВопрос опубликован {await user_friendly_datetime(task[0])}'
                                 f'\nПубликация ответа запланирована {await user_friendly_datetime(task[1])}')
        single_task_info += f'\n'
    else:
        single_task_info += ' не запланированы\n'

    # загрузка предстоящих ЗАПЛАНИРОВАННЫХ заданий и формирование блока отчета в стартовом сообщении
    next_active_multi_tasks = await db_utils.load_next_active_tasks("multi")
    multi_task_info = 'По расписанию:'
    if next_active_multi_tasks:
        multi_task_info += f' запланировано публикаций: {len(next_active_multi_tasks)}\n'
        if next_active_multi_tasks[0][0] < datetime.now() < next_active_multi_tasks[0][1]:
            multi_task_info += (f'Очередной вопрос был опубликован '
                                f'{await user_friendly_datetime(next_active_multi_tasks[0][0])}\n'
                                f'Публикация ответа запланирована на {next_active_multi_tasks[0][1]}')
        else:
            multi_task_info += (f'Очередной вопрос будет опубликован '
                                f'{await user_friendly_datetime(next_active_multi_tasks[0][0])}\n'
                                f'Публикация ответа запланирована на {next_active_multi_tasks[0][1]}')
    else:
        multi_task_info += ' не запланированы'

    menu_message = (f'<b>Life is game for <i>George Bars</i></b>\n'
                    f'Система управления квизами v 0.3\n\n'
                    f'Ближайшие публикации:\n{single_task_info}{multi_task_info}')

    keyboard = command_start_keyboard(lc)
    bot_message = await message.answer(menu_message, reply_markup=keyboard)
    top_menu_stack.append(bot_message)
