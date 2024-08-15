import os
from os.path import join, dirname
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv


def get_from_env(key):
    """Load bot token from env"""
    dotenv_path = join(dirname(__file__), 'token.env')
    load_dotenv(dotenv_path)
    return os.environ.get(key)


# Инициализация бота и диспетчера
token = get_from_env('TOKEN')
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher()

__all__ = ["bot", "dp"]
