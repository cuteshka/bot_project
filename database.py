import sqlalchemy.orm as orm
from sqlalchemy import create_engine, Column, Integer, String, Date
from config import DATABASE_URL
from datetime import datetime, date

engine = create_engine(DATABASE_URL, echo=False)
SqlAlchemyBase = orm.declarative_base()
__factory = None


class Birthday(SqlAlchemyBase):
    __tablename__ = 'birthdays'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    surname_name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    group = Column(String, nullable=True)
    details = Column(String, nullable=True)

    def __repr__(self):
        return f"<Birthday(surname_name='{self.surname_name}', date='{self.date}')>"


if not __factory:
    __factory = orm.sessionmaker(bind=engine)
    SqlAlchemyBase.metadata.create_all(engine)


# добавляет день рождения в базу данных
def add_birthday(user_id, surname_name, date, group=None, details=None):
    session = __factory()
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        birthday = Birthday(user_id=user_id, surname_name=surname_name, date=date_obj, group=group, details=details)
        session.add(birthday)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Ошибка добавления дня рождения: {e}")
    finally:
        session.close()


# возвращает список дней рождений для конкретного пользователя
def get_birthdays_by_user(user_id):
    session = __factory()
    try:
        birthdays = session.query(Birthday).filter_by(user_id=user_id).all()
        return birthdays
    finally:
        session.close()


# Возвращает список дней рождений на сегодня
def get_all_birthdays_today(user_id):
    today = date.today()
    session = __factory()
    try:
        birthdays = (session.query(Birthday).filter(Birthday.date.like(f"%-{today.month:02d}-{today.day:02d}"))
                     .filter_by(user_id=user_id).all())
        return birthdays
    finally:
        session.close()


# удаляет день рождения из базы данных
def delete_birthday(user_id, surname_name):
    session = __factory()
    try:
        birthday = session.query(Birthday).filter_by(user_id=user_id, surname_name=surname_name).first()
        if birthday:
            session.delete(birthday)
            session.commit()
            return True
        else:
            return False
    except Exception as e:
        session.rollback()
        print(f"Ошибка удаления дня рождения: {e}")
        return False
    finally:
        session.close()


