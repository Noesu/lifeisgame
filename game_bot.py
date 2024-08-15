import asyncio
import logging
# import re
# from aiogram import Bot, Dispatcher, types, F
# from aiogram import exceptions as ae
# from aiogram.filters import Command, CommandStart
# from aiogram.utils.keyboard import InlineKeyboardBuilder
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup
# from aiogram.exceptions import TelegramAPIError
# from aiogram.types import (KeyboardButton,
#                            ReplyKeyboardRemove,
#                            Message,
#                            InlineKeyboardMarkup,
#                            InlineKeyboardButton,
#                            ReplyKeyboardMarkup)
# import sqlite3 as sq
# from dotenv import load_dotenv
# import os
# from os.path import join, dirname
# from datetime import time, datetime, timedelta
# from sqlalchemy import Column, Integer, String, create_engine, exc, Boolean, DateTime, literal_column, ForeignKey
# from sqlalchemy.orm import declarative_base, sessionmaker, relationship
# from sqlalchemy.sql import func
# # import DB.db_utils as db_utils
# from DB.models import Question, Config, Task, Session
# from Config import lc
from Bot import bot, dp
from Bot import bot_handlers, bot_commands
import Config


logging.basicConfig(level=logging.DEBUG)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
