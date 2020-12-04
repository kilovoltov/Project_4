import json
import os
from random import shuffle

from flask import Flask, render_template, abort
from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, SubmitField, HiddenField
from wtforms.validators import InputRequired
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func

app = Flask(__name__)
csrf = CSRFProtect(app)
# Настраиваем приложение
app.config.update(
    DEBUG=True,
    SECRET_KEY=b'_5#y2L"gpHF4Q8z\n\xec]/',
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# Создаем подключение к БД
db = SQLAlchemy(app)
# Создаем объект поддержки миграций
migrate = Migrate(app, db)

association_table = db.Table(
    'association',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id')),
    db.Column('goal_id', db.Integer, db.ForeignKey('goals.id'))
    )


# Модель для хранения визитов нашей страницы
class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    about = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    picture = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    free = db.Column(db.JSON, nullable=False)
    goals = db.relationship('Goal', secondary=association_table, back_populates='teachers')


class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    teachers = db.relationship('Teacher', secondary=association_table, back_populates='goals')


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    day = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    teacher = db.relationship('Teacher')


class Request(db.Model):
    __tablename__ = 'requests'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'))
    goal = db.relationship('Goal')


class RequestForm(FlaskForm):
    goals = db.session.query(Goal).all()
    name = StringField('Вас зовут', validators=[InputRequired(message='Нужно ввести свое имя')])
    phone = StringField('Ваш телефон', validators=[InputRequired(message='Введите номер телефона')])
    goal = RadioField('Какая цель занятий?',
                      choices=[(goal.key, goal.title) for goal in goals],
                      validators=[InputRequired(message='Нужно выбрать цель')])
    time = RadioField('Сколько времени есть?',
                      choices=[("1-2 часа в неделю", "1-2 часа в неделю"),
                               ("3-5 часов в неделю", "3-5 часов в неделю"),
                               ("5-7 часов в неделю", "5-7 часов в неделю"),
                               ("7-10 часов в неделю", "7-10 часов в неделю")],
                      validators=[InputRequired(message='Выберите количество свободного времени')])
    submit = SubmitField('Найдите мне преподавателя')


class BookingForm(FlaskForm):
    client_name = StringField('Вас зовут', validators=[InputRequired(message='Нужно ввести свое имя')])
    client_phone = StringField('Ваш телефон', validators=[InputRequired(message='Введите номер телефона')])
    client_teacher = HiddenField('clientTeacher', validators=[InputRequired()])
    client_time = HiddenField('clientTime', validators=[InputRequired()])
    client_weekday = HiddenField('clientWeekday', validators=[InputRequired()])
    submit = SubmitField('Записаться')


@app.route('/')
def render_main():
    teachers = db.session.query(Teacher).order_by(func.random()).limit(6)

    goals = db.session.query(Goal).all()
    return render_template('index.html',
                           teachers=teachers,
                           goals=goals)


@app.route('/goals/<goal>/')
def render_goal(goal):
    goal = db.session.query(Goal).filter(Goal.key == goal).first()
    if goal is None:
        abort(404)
    teachers = db.session.query(Teacher).filter(Teacher.goals.any(id=goal.id)).all()

    return render_template('goal.html',
                           teachers=teachers,
                           goal=goal)


@app.route('/profiles/all/')
def render_all_teachers():
    teachers = db.session.query(Teacher.id,
                                Teacher.name,
                                Teacher.about,
                                Teacher.picture,
                                Teacher.rating,
                                Teacher.price).all()

    return render_template('all.html',
                           teachers=teachers)


@app.route('/profiles/<int:id>/')
def render_profile(id):
    teacher = db.session.query(Teacher).get_or_404(id)
    teacher.free = json.loads(teacher.free)  # teachers.free turns into DICT from STRING

    goals = db.session.query(Goal).filter(Goal.teachers.any(id=teacher.id)).all()

    with open('days.json', 'r') as f:
        days = json.load(f)
    return render_template('profile.html',
                           teacher=teacher,
                           goals=goals,
                           days=days)


@app.route('/booking/<int:id>/<day>/<int:time>/', methods=['GET', 'POST'])
def render_booking(id, day, time):
    teacher = db.session.query(Teacher).get_or_404(id)
    with open('days.json', 'r') as f:
        days = json.load(f)
    if days.get(day) is None:
        abort(404)

    form = BookingForm(client_time=str(time) + ':00', client_weekday=day, client_teacher=id)

    if form.validate_on_submit():
        with open('days.json', 'r') as f:
            days = json.load(f)
        form = BookingForm()
        client_name = form.client_name.data
        client_phone = form.client_phone.data
        client_teacher = form.client_teacher.data
        client_time = form.client_time.data
        client_weekday = form.client_weekday.data

        booking = Booking(name=client_name,
                          phone=client_phone,
                          day=client_weekday,
                          time=client_time,
                          teacher_id=client_teacher)
        db.session.add(booking)
        db.session.commit()

        return render_template('booking_done.html',
                               name=client_name,
                               phone=client_phone,
                               days=days,
                               day=client_weekday,
                               time=client_time,
                               teacher=client_teacher)
    else:
        return render_template('booking.html',
                               teacher=teacher,
                               days=days,
                               day=day,
                               time=time,
                               form=form)


@app.route('/request/', methods=['GET', 'POST'])
def render_request():
    form = RequestForm()
    if form.validate_on_submit():
        form = RequestForm()
        name = form.name.data
        phone = form.phone.data
        goal = form.goal.data
        time = form.time.data

        goal = db.session.query(Goal).filter(Goal.key == goal).first()
        request = Request(name=name, phone=phone, time=time.split(' ')[0], goal=goal)
        db.session.add(request)
        db.session.commit()

        return render_template('request_done.html',
                               name=name,
                               phone=phone,
                               goal=goal,
                               time=time)
    else:
        goals = db.session.query(Goal).all()
        return render_template('request.html',
                               form=form,
                               goals=goals)


def to_db():
    """
    Используется для первоначального импорта данных из json-файла в таблицы БД
    """
    goals_rows = []
    with open('goals.json') as f:
        goals = json.load(f)
    for k, v in goals.items():
        goals_rows.append(Goal(key=k, title=v))
    db.session.add_all(goals_rows)
    db.session.commit()

    with open('teachers.json') as f:
        teachers = json.load(f)

    for teacher in teachers:
        teacher_goals = db.session.query(Goal).filter(Goal.key.in_(teacher['goals'])).all()
        row = Teacher(name=teacher['name'],
                      about=teacher['about'],
                      rating=teacher['rating'],
                      picture=teacher['picture'],
                      price=teacher['price'],
                      free=teacher['free'])
        db.session.add(row)
        row.goals = teacher_goals

    db.session.commit()


if __name__ == '__main__':
    app.run()
