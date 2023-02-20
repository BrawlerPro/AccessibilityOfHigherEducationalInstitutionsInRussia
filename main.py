import json
import re
import sqlite3
import os
from flask import Flask, render_template, request, g, flash, abort, redirect, url_for, make_response
from FDataBase import FDataBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from UserLogin import UserLogin
import requests as res
import datetime

# конфигурация
DATABASE = '/tmp/flsite.db'
DEBUG = True
SECRET_KEY = 'fdgfh78@#5?>gfhf89dx,v06k'
MAX_CONTENT_LENGTH = 1024 * 1024

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'flsite.db')))

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
login_manager.login_message_category = "success"


@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id, dbase)


def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    """Вспомогательная функция для создания таблиц БД"""
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


def get_db():
    """Соединение с БД, если оно еще не установлено"""
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


dbase = None


@app.before_request
def before_request():
    """Установление соединения с БД перед выполнением запроса"""
    global dbase
    db = get_db()
    dbase = FDataBase(db)


@app.teardown_appcontext
def close_db(error):
    """ Закрываем соединение с БД, если оно было установлено """
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == 'POST':
        s = request.form['scr'].lower()
        with open('parse/result.json', encoding='utf-8') as f:
            file = list(
                filter(lambda x: (True if s in (a := x[1])['title'].lower() or s in a['title1'].lower() else False),
                       json.load(f).items()))
            return render_template('index.html', posts=file, title='Home')
    else:
        with open('parse/result.json', encoding='utf-8') as f:
            file = json.load(f)
            return render_template('index.html', posts=file.items(), title='Home')


@app.route("/about/<alias>", methods=["POST", "GET"])
@login_required
def showPost(alias):
    if request.method == "POST":
        pass
    else:
        with open('parse/result.json', encoding='utf-8') as f:
            file = json.load(f)
            uni = file[alias]
            # состояния: True - Сайт работает, False - DDoS, None - ошибка.
            response = res.get(uni['link'])
            if response:
                # True
                state = (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Сайт в порядке!')
            else:
                # False
                if str(response.status_code)[0] == '5':
                    state = (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Сайт в порядке!')
                else:
                    # None
                    state = (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             '{0} {1}'.format(response.status_code, response.reason))
            return render_template('about.html', title=uni['title'], comments=uni['coments'], first_name=uni['title1'],
                                   img=uni['img'], state=state)


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    if request.method == "POST":
        user = dbase.getUserByEmail(request.form['email'])
        if user and check_password_hash(user['psw'], request.form['psw']):
            userlogin = UserLogin().create(user)
            rm = True if request.form.get('remainme') else False
            login_user(userlogin, remember=rm)
            return redirect(request.args.get("next") or url_for("profile"))

        flash("Неверная пара логин/пароль", "error")

    return render_template("login.html", menu=dbase.getMenu(), title="Авторизация")


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        if len(request.form['name']) > 4 and len(request.form['email']) > 4 \
                and len(request.form['psw']) > 4 and request.form['psw'] == request.form['psw2']:
            if re.fullmatch(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', request.form['email']):
                hash = generate_password_hash(request.form['psw'])
                res = dbase.addUser(request.form['name'], request.form['email'], hash)
                if res and 'Пользователь' not in str(res):
                    flash("Вы успешно зарегистрированы", "success")
                    return redirect(url_for('login'))
                else:
                    flash(res, "error")
            else:
                flash('Некорректная почта')
        else:
            flash("Неверно заполнены поля", "error")

    return render_template("register.html", menu=dbase.getMenu(), title="Регистрация")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "success")
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html", menu=dbase.getMenu(), title="Профиль")


@app.route('/userava')
@login_required
def userava():
    img = current_user.getAvatar(app)
    if not img:
        return ""

    h = make_response(img)
    h.headers['Content-Type'] = 'image/png'
    return h


@app.route('/upload', methods=["POST", "GET"])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and current_user.verifyExt(file.filename):
            try:
                img = file.read()
                resa = dbase.updateUserAvatar(img, current_user.get_id())
                if not resa:
                    flash("Ошибка обновления аватара", "error")
                flash("Аватар обновлен", "success")
            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "error")
        else:
            flash("Ошибка обновления аватара", "error")

    return redirect(url_for('profile'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
