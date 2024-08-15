from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def command_start_keyboard(lc):
    buttons = [
        ("База данных", f"database_{lc.q_offset}"),
        ("Настройки", "settings"),
        ("Планировщик", "scheduler")
    ]
    builder = InlineKeyboardBuilder()
    for text, callback_data in buttons:
        builder.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.as_markup()


def read_database_keyboard(lc):
    builder = InlineKeyboardBuilder()
    for q_id, q_text, rowid in lc.questions[lc.q_offset:lc.q_offset + lc.q_range]:
        builder.add(types.InlineKeyboardButton(text=str(q_id), callback_data=f"question_{rowid}"))
    builder.adjust(5)
    nav_buttons = []
    if lc.q_offset > 0:
        prev_btn = types.InlineKeyboardButton(text=f"<<< {lc.q_range}",
                                              callback_data=f"database_{lc.q_offset - lc.q_range}")
        nav_buttons.append(prev_btn)
    if lc.q_offset < len(lc.questions) - lc.q_range:
        next_btn = types.InlineKeyboardButton(text=f"{lc.q_range} >>>",
                                              callback_data=f"database_{lc.q_offset + lc.q_range}")
        nav_buttons.append(next_btn)
    if len(nav_buttons) == 2:
        builder.row(*nav_buttons)
    elif len(nav_buttons) == 1:
        builder.row(nav_buttons[0])
    add_q = types.InlineKeyboardButton(text=f"Добавить вопрос", callback_data="edit_q")
    # builder.row(prev_btn, next_btn)
    builder.row(add_q)
    return builder.as_markup()


def read_question_keyboard(lc):
    buttons = [
        ('Редактировать вопрос', 'edit_q'),
        ('Удалить вопрос', 'del_q'),
        ("Изменить признак", 'reverse_q_flag'),
        ('Опубликовать', 'single_q'),
        ('Закрыть', 'database_0')
    ]
    builder = InlineKeyboardBuilder()
    for text, callback_data in buttons:
        builder.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.adjust(2).as_markup()


def cancel_state_keyboard(lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Отмена",
                                           callback_data=f'cancel_state'))
    return builder.as_markup()


def confirm_question_keyboard(lc):
    buttons = [
        ('Сохранить', 'confirm_question'),
        ('Отмена', 'cancel_state')
    ]
    builder = InlineKeyboardBuilder()
    for text, callback_data in buttons:
        builder.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.as_markup()


def delete_question_keyboard(lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Назад",
                                           callback_data=f'database_0'))
    return builder.as_markup()


def back_to_question_kb(rowid, lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Назад",
                                           callback_data=f'database_0'))
    return builder.as_markup()


def settings_keyboard(lc):
    buttons = (
        ("Изменить группу", "config_chat_id"),
        ("Периодичность", "config_schedule_day_"),
        ("Задержка ответа", "config_answer_delay"),
        ("Вопросов на странице", "config_q_range"),
        ("Предисловие вопроса", "config_preface_question"),
        ("Предисловие ответа", "config_preface_answer")
    )
    builder = InlineKeyboardBuilder()
    for text, callback_data in buttons:
        builder.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))
    return builder.adjust(2).as_markup()


def config_schedule_day_keyboard(lc):
    buttons = (
        ("ПН", "config_schedule_day_0"),
        ("ВТ", "config_schedule_day_1"),
        ("СР", "config_schedule_day_2"),
        ("ЧТ", "config_schedule_day_3"),
        ("ПТ", "config_schedule_day_4"),
        ("СБ", "config_schedule_day_5"),
        ("ВС", "config_schedule_day_6")
    )  # формирование списка из семи inline-кнопок для отправки рекурсивного callback с выбранным днём недели
    builder = InlineKeyboardBuilder()
    for button_text, button_callback in buttons:
        builder.add(types.InlineKeyboardButton(text=button_text,
                                               callback_data=button_callback))
    builder.adjust(7)  # размещение семи кнопок в ряд
    cancel_btn = types.InlineKeyboardButton(text="Отмена", callback_data="settings")
    next_btn = types.InlineKeyboardButton(text="Далее", callback_data="config_schedule_time")
    builder.row(cancel_btn, next_btn)  # размещение строки с двумя кнопками
    return builder.as_markup()


def preface_keyboard(preface_type, lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Отмена", callback_data="settings"))
    if lc.preface_question and preface_type == "question":
        builder.add(types.InlineKeyboardButton(text="Удалить", callback_data="delete_preface_question"))
    elif lc.preface_answer and preface_type == "answer":
        builder.add(types.InlineKeyboardButton(text="Удалить", callback_data="delete_preface_answer"))
    return builder.as_markup()


def back_to_settings_keyboard(lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Отмена", callback_data="settings"))
    return builder.as_markup()


def save_config_keyboard(lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Отмена", callback_data="settings"))
    builder.add(types.InlineKeyboardButton(text="Сохранить", callback_data="save_config"))
    return builder.adjust(2).as_markup()


def switch_autopost_keyboard(lc, task_status):
    builder = InlineKeyboardBuilder()
    match task_status:
        case 0: builder.add(types.InlineKeyboardButton(text="Включить автопубликацию", callback_data="autopost_on"))
        case _: builder.add(types.InlineKeyboardButton(text="Выключить автопубликацию", callback_data="autopost_off"))
    return builder.as_markup()


def back_to_command_start_kb(lc):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Назад", callback_data="back_to_command_start"))
    return builder.as_markup()
