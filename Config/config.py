from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from DB.models import Config



DEFAULT = {
    "q_range": 10,
    "answer_delay": 60
}


class LocalConfig:
    def __init__(self):
        with Session() as db_session:
            config = db_session.query(Config).first()
            if config:
                self.chat_id = config.chat_id or None
                self.q_range = config.q_range or DEFAULT.get("q_range")
                self.answer_delay = config.answer_delay or DEFAULT.get("answer_delay")
                self.schedule_day = config.schedule_day or None
                self.schedule_time = config.schedule_time or None
                self.preface_question = config.q_text_preface or None
                self.preface_answer = config.a_text_preface or None
                self.q_offset = 0
                self.chat_name = None
                self.questions = []
            else:
                raise ValueError


engine = create_engine('sqlite:///lifeisgame2.db')
Session = sessionmaker(bind=engine)
lc = LocalConfig()
