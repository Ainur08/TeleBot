import os
import random
import string
import datetime
from threading import Thread
from time import sleep
import schedule
import sqlalchemy as sqlalchemy
from sqlalchemy import MetaData, UniqueConstraint
from sqlalchemy import Table
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import telebot
import matplotlib.pyplot as plt
import numpy as np

TOKEN = "1567721230:AAGK2QhaQWPfIfE1BtkgJQcuUYj0F2jGS4o"
ADMIN_ID = 460688017
bot = telebot.TeleBot(TOKEN)
engine = sqlalchemy.create_engine("sqlite:///athletic.db")
Base = declarative_base()
Base.metadata.create_all(engine, checkfirst=True)
session_factory = sessionmaker()
session_factory.configure(bind=engine)
Session = scoped_session(session_factory)
metadata = MetaData(engine)

agreement_words = ["да", "пойду", "приду", "буду"]
disagreement_words = ["нет", "не"]


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    name = Column(String)
    telegram_id = Column(Integer, unique=True)


class Schedule(Base):
    __tablename__ = 'schedule'
    id = Column(Integer, primary_key=True)
    day = Column(String)
    lesson = Column(String)
    lesson_num = Column(Integer)


class Attendance(Base):
    __tablename__ = 'attendance'
    id = Column(Integer, primary_key=True)
    date = Column(String)
    user_id = Column(Integer, nullable=False)


def autolabel(rects, ax):
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')


def unregister_agreement(message):
    _date = datetime.datetime.today().strftime('%Y-%m-%d')
    session = Session()
    a = session.query(Attendance.id).filter(Attendance.date == _date).filter(
        Attendance.user_id == int(message.from_user.id))
    a = session.query(Attendance).get(a[0][0])
    try:
        session.delete(a)
        session.commit()
        bot.send_message(message.chat.id, text=u"Вы не придете.")
    except:
        return None


def register_agreement(message):
    _date = datetime.datetime.today().strftime('%Y-%m-%d')
    session = Session()
    _attendance = Attendance()
    _attendance.date = _date
    _attendance.user_id = message.from_user.id
    try:
        session.add(_attendance)
        session.commit()
        bot.send_message(message.chat.id, text=u"Вы придете.")
    except:
        return None


@bot.message_handler(commands=['stat'])
def admin_stat(message):
    if message.from_user.id == ADMIN_ID:
        _today = datetime.date.today()
        labels = list(reversed([(_today - datetime.timedelta(days=i)) for i in range(7)]))
        session = Session()
        _users = session.query(User).count()
        _attendances = [
            session.query(Attendance.user_id).filter(Attendance.date == l.strftime('%Y-%m-%d')).count()
            for l in labels
        ]
        _not_attendances = [_users - a for a in _attendances]
        x = np.arange(len(labels))
        width = 0.35
        fig, ax = plt.subplots()
        rects1 = ax.bar(x - width / 2, _attendances, width, label='Посетили')
        rects2 = ax.bar(x + width / 2, _not_attendances, width, label='Отсутствовали')
        ax.set_ylabel('Количество')
        ax.set_xticks(x)
        ax.set_xticklabels(list([l.strftime('%A') for l in labels]))
        ax.legend()
        autolabel(rects1, ax)
        autolabel(rects2, ax)
        fig.tight_layout()
        plt.savefig('graph.png')
        img = open('graph.png', 'rb')
        bot.send_photo(ADMIN_ID, img)
        img.close()

def schedule_distribution():
    session = Session()
    chats = [c[0] for c in session.query().with_entities(User.chat_id).all()]
    _today = datetime.datetime.today().strftime('%A')
    lessons = [l for l in session.query(Schedule.lesson, Schedule.lesson_num).filter(Schedule.day == _today)]
    lessons.sort(key=lambda l: l[1])
    response = "Today schedule" + '\n'.join(f"{l[1]}) {l[0]}" for l in lessons)
    for c in chats:
        bot.send_message(c, text=response)


@bot.message_handler(commands=['today'])
def today(message):
    session = Session()
    _today = datetime.datetime.today().strftime('%A')
    lessons = [l for l in session.query(Schedule.lesson, Schedule.lesson_num).filter(Schedule.day == _today)]
    lessons.sort(key=lambda l: l[1])
    response = '\n'.join(f"{l[1]}) {l[0]}" for l in lessons)
    bot.send_message(message.chat.id, text=response)


@bot.message_handler(commands=['start'])
def start(message):
    session = Session()
    _user = User()
    _user.chat_id = message.chat.id
    _user.telegram_id = message.from_user.id
    _user.name = ' '.join([message.from_user.first_name, message.from_user.last_name])
    try:
        session.add(_user)
        session.commit()
    except:
        return None


@bot.message_handler(func=lambda message: True, content_types=['text'])
def agreement(message):
    if any([w in message.text.lower() for w in disagreement_words]):
        return unregister_agreement(message)
    elif any([w in message.text.lower() for w in agreement_words]):
        return register_agreement(message)
    return None


def bot_polling():
    bot.polling()


def schedule_checker():
    while True:
        schedule.run_pending()
        sleep(1)


if __name__ == "__main__":
    schedule.every().day.at("01:35").do(schedule_distribution)
    Thread(target=schedule_checker).start()
    Thread(target=bot_polling).start()

    # schedule_table = Table('schedule', metadata,
    #                        Column('id', Integer, primary_key=True),
    #                        Column('day', String),
    #                        Column('lesson', String),
    #                        Column('lesson_num', Integer))
    # attendance_table = Table('attendance', metadata,
    #                          Column('id', Integer, primary_key=True),
    #                          Column('user_id', Integer, nullable=False),
    #                          Column('date', String, nullable=False),
    #                          UniqueConstraint('date', 'user_id', name='uix_1'))
    # user_table = Table('user', metadata,
    #                    Column('id', Integer, primary_key=True),
    #                    Column('chat_id', Integer, unique=True),
    #                    Column('name', String),
    #                    Column('telegram_id', Integer, unique=True))
    # metadata.create_all()
    # week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    # session = Session()
    # for w in week_days:
    #     for i in range(1, random.randint(6, 8)):
    #         s = Schedule()
    #         s.day = w
    #         s.lesson = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    #         s.lesson_num = i
    #         session.add(s)
    #         session.commit()
    # session.flush()
    # session.close()
