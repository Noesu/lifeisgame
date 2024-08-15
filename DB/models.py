from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, create_engine

engine = create_engine('sqlite:///lifeisgame2.db')
Base = declarative_base()


class Question(Base):
    __tablename__ = 'Question'

    # rowid = Column(Integer, primary_key=True)
    q_text = Column(String, primary_key=True)
    a_text = Column(String)
    date_used = Column(DateTime, default=None)

    # tasks = relationship("Task", back_populates="question")


class Config(Base):
    __tablename__ = 'Config'

    chat_id = Column(Integer, primary_key=True)
    q_range = Column(Integer)
    answer_delay = Column(Integer)
    schedule_time = Column(String, default=None)
    schedule_day = Column(String, default=None)
    q_text_preface = Column(String)
    a_text_preface = Column(String)


class Task(Base):
    __tablename__ = 'Task'

    q_text = Column(String, primary_key=True)
    q_time = Column(DateTime, primary_key=True)
    a_text = Column(String)
    a_time = Column(DateTime)
    chat_id = Column(Integer)
    single = Column(Boolean)
    question_id = Column(Integer)
    # question_id = Column(Integer, ForeignKey('Question.rowid'))

    # question = relationship("Question", back_populates="tasks")


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
