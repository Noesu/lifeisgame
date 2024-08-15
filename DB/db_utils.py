from DB.models import Question, Config, Task, Session
# from Config import lc
from Bot import dp
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (KeyboardButton,
                           ReplyKeyboardRemove,
                           Message,
                           InlineKeyboardMarkup,
                           InlineKeyboardButton,
                           ReplyKeyboardMarkup)
from stacks import *
import time
from sqlalchemy.exc import OperationalError
import sqlite3
from sqlalchemy import text, literal_column
from Utils.date_time import *


async def load_number_of_questions(usage_attr):
    with Session() as session:
        try:
            match usage_attr:
                case 'total':
                    number_of_questions = session.query(Question).count()
                case 'new':
                    number_of_questions = (
                        session.query(Question)
                        .filter(Question.date_used.is_(None))
                        .count()
                    )
                case 'used':
                    number_of_questions = (
                        session.query(Question)
                        .filter(Question.date_used.is_not(None))
                        .count()
                    )
                case _:
                    number_of_questions = 0
        except Exception as e:
            print(f'Error getting number of questions from DB: {e}')
            number_of_questions = 0
        finally:
            session.close()
        return number_of_questions


async def load_questions(usage_attr):
    with Session() as session:
        try:
            match usage_attr:
                case "all":
                    lc.questions = (
                        session.query(Question.q_text, Question.a_text, literal_column("_rowid_").label("rowid"))
                        .order_by(literal_column("_rowid_").asc())
                        .all()
                    )
                    lc.questions = [(index + 1, question.q_text, question.rowid) for index, question in
                                    enumerate(lc.questions)]
                    return
                case "new":
                    questions = (
                        session.query(Question.q_text, Question.a_text, literal_column("_rowid_").label("rowid"))
                        .filter(Question.date_used.is_(None))
                        .order_by(literal_column("_rowid_").asc())
                        .all()
                    )
                    return [(question.q_text, question.a_text, question.rowid) for question in questions]
                case "used":
                    lc.questions = (
                        session.query(Question.q_text, Question.a_text, literal_column("_rowid_").label("rowid"))
                        .filter(Question.date_used.is_not(None))
                        .order_by(literal_column("_rowid_").asc())
                        .all()
                    )
        except Exception as e:
            print(f"Error loading questions: {e}")


async def load_question(rowid):
    with Session() as session:
        question = []
        try:
            question = (session.query(Question)
                        .filter(literal_column("_rowid_") == rowid)
                        .first()
                        )
        except Exception as e:
            print(f"Error loading selected question: {e}")
        finally:
            session.close()
            return question


async def question_duplicates_found(q_text):
    with Session() as session:
        try:
            duplicates_found = session.query(Question).filter(Question.q_text == q_text).first()
            return duplicates_found
        except Exception as e:
            print(f"Error loading duplicated question: {e}")
        finally:
            session.close()


async def save_question(rowid, q_text, a_text):
    with Session() as session:
        try:
            if rowid:
                # Обновление существующей записи
                session.query(Question).filter(literal_column("_rowid_") == rowid).update({
                    Question.q_text: q_text,
                    Question.a_text: a_text,
                    Question.date_used: None
                })
            else:
                # Добавление новой записи
                new_question = Question(q_text=q_text, a_text=a_text)
                session.add(new_question)
                session.commit()  # Сохраняем изменения в базе данных

                # Получаем _rowid_ новой записи
                rowid = session.execute(
                    text("SELECT _rowid_ FROM Question WHERE q_text = :q_text AND a_text = :a_text"),
                    {"q_text": q_text, "a_text": a_text}
                ).scalar()
            return rowid
        except Exception as e:
            print(f"Error updating or inserting selected question: {e}")
            session.rollback()  # Откат транзакции в случае ошибки
        finally:
            session.close()


async def delete_question(rowid):
    with Session() as session:
        try:
            session.query(Question).filter(literal_column("_rowid_") == rowid).delete()
            session.commit()
        except Exception as e:
            print(f"Error deleting question: {e}")
        finally:
            session.close()


async def set_q_flag(rowid, switch):
    """Переключатель признака публикации вопроса
    Принимаемые параметры:
    rowid  - rowid вопроса, содержащегося в БД,
    switch - параметр, определяющий выполняемое действие:
     "on"   - присваивает признаку date_used значение, соответствующее текущей дате и локальному времени,
            - возвращает текущую дату и локальное время
     "off"  - устанавливает значение признака date_used как None
     "auto" - проверяет наличие признака date_used.
             - при его наличии устанавливает его значение как None.
             - при его отсутствии присваивает признаку date_used значение, соответствующее текущей дате
               и локальному времени

    Возвращает значение признака date_used"""
    with Session() as session:
        try:
            if switch == "on":
                date_used = datetime.now()
                session.query(Question).filter(literal_column("_rowid_") == rowid).update(
                    {Question.date_used: date_used})
                session.commit()
                return date_used
            if switch == "off":
                session.query(Question).filter(literal_column("_rowid_") == rowid).update({Question.date_used: None})
                session.commit()
                return None
            if switch == "auto":
                question = session.query(Question).filter(literal_column("_rowid_") == rowid).first()
                date_used = None if question.date_used else datetime.now()
                session.query(Question).filter(literal_column("_rowid_") == rowid).update(
                    {Question.date_used: date_used})
                session.commit()
                return date_used
        except Exception as e:
            print(f"Error accessing question post flag: {e}")
            session.rollback()
        finally:
            session.close()


async def update_config(chat_id, answer_delay, q_range, schedule_time, schedule_day, preface_question,
                        preface_answer):
    with Session() as session:
        try:
            session.query(Config).update({
                Config.chat_id: chat_id,
                Config.answer_delay: answer_delay,
                Config.q_range: q_range,
                Config.schedule_time: schedule_time,
                Config.schedule_day: schedule_day,
                Config.q_text_preface: preface_question,
                Config.a_text_preface: preface_answer
            })
            session.commit()
        except Exception as e:
            print(f"Error updating config: {e}")
        finally:
            session.close()


async def create_single_task_db(data):
    a_time = (q_time := datetime.now()) + timedelta(minutes=lc.answer_delay)
    new_task = Task(q_text=(q_text := data.get('q_text')),
                    q_time=q_time,
                    a_text=(a_text := data.get('a_text')),
                    a_time=a_time,
                    chat_id=(chat_id := lc.chat_id),
                    question_id=data.get('rowid'),
                    single=True)
    with Session() as session:
        try:
            session.add(new_task)
            session.commit()
            task = session.query(Task).filter(Task.single.is_(True)).filter(
                Task.q_text == q_text, Task.q_time == q_time).first()
            return task
        except Exception as e:
            print(f"Error creating single task: {e}")
            session.rollback()
        finally:
            session.close()


async def delete_single_task_db():
    with Session() as session:
        try:
            session.query(Task).filter(Task.single.is_(True)).delete()
            session.commit()
        except Exception as e:
            print(f"Error deleting single task: {e}")
        finally:
            session.close()


async def create_multi_tasks_db():
    questions = await load_questions('new')
    qa_post_times = await calculate_post_times(questions)
    for question in questions:
        q_time = datetime(*qa_post_times.pop(0))
        a_time = q_time + timedelta(minutes=lc.answer_delay)
        new_task = Task(q_text=question[0],
                        q_time=q_time,
                        a_text=question[1],
                        a_time=a_time,
                        chat_id=lc.chat_id,
                        question_id=question[2],
                        single=False)
        with Session() as session:
            try:
                session.add(new_task)
                session.commit()
                # return q_text, q_time, a_text, a_time, chat_id
            except Exception as e:
                print(f"Error creating multi tasks: {e}")
                session.rollback()
            finally:
                session.close()


async def delete_multi_tasks_db():
    with Session() as session:
        try:
            session.query(Task).filter(Task.single.is_(False)).delete()
            session.commit()
        except Exception as e:
            print(f"Error deleting multi tasks: {e}")
        finally:
            session.close()


async def check_active_tasks_count(task_type):
    with Session() as session:
        try:
            match task_type:
                case "single":
                    task_count = session.query(Task).filter(Task.single.is_(True)).count()
                case "multi":
                    task_count = session.query(Task).filter(Task.single.is_(False)).count()
            return task_count
        except Exception as e:
            print(f"Error loading active tasks count: {e}")


async def load_next_active_tasks(task_type):
    with Session() as session:
        try:
            match task_type:
                case "single":
                    tasks = session.query(Task).filter(Task.single.is_(True)).filter(
                        Task.a_time > datetime.now()).order_by(
                        Task.q_time.asc()).all()
                    session.expunge_all()  # Удаляем объекты из сессии, чтобы их можно было использовать после закрытия
                    return tasks
                case "multi":
                    tasks = session.query(Task).filter(Task.single.is_(False)).filter(
                        Task.a_time > datetime.now()).order_by(
                        Task.q_time.asc()).all()
                    return [(task.q_time, task.a_time) for task in tasks]
        except Exception as e:
            print(f"Error loading next active {task_type} task info: {e}")
# async def load_next_active_tasks_times(task_type):
#     with Session() as session:
#         try:
#             match task_type:
#                 case "single":
#                     tasks = session.query(Task).filter(Task.single.is_(True)).filter(
#                         Task.a_time > datetime.now()).order_by(
#                         Task.q_time.asc()).all()
#                     return [(task.q_time, task.a_time) for task in tasks]
#                 case "multi":
#                     tasks = session.query(Task).filter(Task.single.is_(False)).filter(
#                         Task.a_time > datetime.now()).order_by(
#                         Task.q_time.asc()).all()
#                     return [(task.q_time, task.a_time) for task in tasks]
#         except Exception as e:
#             print(f"Error loading next active {task_type} task info: {e}")


async def load_next_multi_task_q_time():
    with Session() as session:
        try:
            next_multi_task = session.query(Task).filter(Task.single.is_(False)).order_by(Task.q_time.asc()).first()
            return next_multi_task.q_time
        except Exception as e:
            print(f"Error loading next active multi task time: {e}")


async def clean_up_past_tasks():
    with Session() as session:
        try:
            result = session.query(Task).filter(Task.a_time < datetime.now()).delete()
            session.commit()
            print(f"Deleted {result} past tasks.")
        except Exception as e:
            print(f"Error cleaning up past tasks: {e}")
            session.rollback()


# def load_config():
#     with Session() as session:
#         try:
#             config = session.query(Config).first()
#             return config
#         except Exception as e:
#             print(f"Error loading configuration from database: {e}")
