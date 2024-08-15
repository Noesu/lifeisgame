from aiogram.fsm.state import State, StatesGroup


class QuestionState(StatesGroup):
    rowid = State()
    q_used = State()
    q_text = State()
    a_text = State()
    q_text_new = State()
    a_text_new = State()


class ConfigState(StatesGroup):
    chat_id = State()
    chat_name = State()
    answer_delay = State()
    q_range = State()
    schedule_day = State()
    schedule_time = State()
    preface_question = State()
    preface_answer = State()


