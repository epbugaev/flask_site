from flask import Flask, request, g, render_template, abort, redirect, url_for, session, escape, flash 
import sqlite3
import typing
import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import pdfkit

DATABASE = '/flaskr.db' 
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin' 
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    DEBUG=True,
    SECRET_KEY='development key',
    UPLOAD_FOLDER='static',
    DOWNLOAD_FOLDER='downloads',
    USERNAME='admin',
    PASSWORD='default'))

def connect_db():
    """Соединяет с указанной базой данных."""
    rv = sqlite3.connect(app.config['DATABASE']) # внутри конфигураций надо будет указать БД, в которую мы будем все хранить
    rv.row_factory = sqlite3.Row #инстанс для итерации по строчкам (может брать по строке и выдавать)
    return rv


def get_db():
    """Если ещё нет соединения с базой данных, открыть новое - для текущего контекста приложения"""
    if not hasattr(g, 'sqlite_db'): #g - это наша глобальная переменная, являющася объектом отрисовки
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext #декоратор при разрыве connection
def close_db(error): #закрытие может проходить как нормально, так и с ошибкой, которую можно обрабатывать
    """Закрываем БД при разрыве"""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def init_db():
    """Инициализируем наше БД"""
    print('initializing db')
    with app.app_context(): # внутри app_context app и g связаны
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f: 
            db.cursor().executescript(f.read())
        db.commit()

if __name__ == '__main__':
    print('in main')
    init_db()
    #app.run(debug=True)

@app.route("/")
def start_site():
    session.clear()
    db = get_db()
    name = ""
    if session.get('user_id'):
        name = db.execute('select login from users where id = (?)', [session.get('user_id')]).fetchone()[0]        
    else:
        session['logged_in'] = False
    return render_template('layout.html', username=name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        db = get_db()
        lg = request.form['login']
        pw = request.form['password']

        username_cnt = len(db.execute('select login from users where login = (?)', [lg]).fetchall())

        required_password = db.execute('select password from users where login = (?)', [lg]).fetchone()[0]
        
        if len(lg) == 0 or username_cnt == 0:
            error_message = 'Invalid username'
        elif request.form['password'] != required_password:
            #print(request.form['password'] )
            error_message = 'Invalid password'
        else:
            session['user_id'] = db.execute('select id from users where login = (?)', [lg]).fetchone()[0]
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('profile'))

    return render_template('login.html', error_message=error_message)

def password_validation(ps: str) -> bool:
    if len(ps) <= 5:
        return False
    num = False
    letter = False
    for c in ps:
        if c.isalpha():
            letter = True
        if c.isdigit():
            num = True
    return (num and letter)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('logged_in'):
        return redirect(url_for('start_site'))
        
    error_message = None
    if request.method == 'POST':
        db = get_db()
        lg = request.form['login']
        pw = request.form['password']
        username_cnt = len(db.execute('select login from users where login = (?)', [lg]).fetchall())

        if len(lg) == 0 or username_cnt != 0:
            error_message = 'This login is already used, please choose another'
        elif password_validation(pw) == False:
            error_message = 'Your password is weak, please choose another.'
        else:
            db.execute('insert into users (login, password) values (?, ?)', [lg, pw])
            # Name sessionID
            session['user_id'] = db.execute('select id from users where login = (?)', [lg]).fetchone()[0]
            session['logged_in'] = True
            flash('You were registered')

            db.commit()
            return redirect(url_for('profile'))

    return render_template('register.html', error_message=error_message)

@app.route('/update_data', methods=['POST'])
def update_data():
    if session.get('logged_in') == False:
        return redirect(url_for('start_site'))

    print('my_id update', session['user_id'])
    
    db = get_db()
    print('decided to set', request.form['first_name'], 'new first name', db.execute('select first_name from users where id = (?)', [session['user_id']]).fetchone())

    db.execute('UPDATE users SET first_name=(?) WHERE id = (?);', [request.form['first_name'], session['user_id']])
    db.execute('UPDATE users SET last_name=(?) WHERE id = (?);', [request.form['last_name'], session['user_id']])
    db.execute('UPDATE users SET experience=(?) WHERE id = (?);', [request.form['experience'], session['user_id']])
    db.execute('UPDATE users SET achievments=(?) WHERE id = (?);', [request.form['achievments'], session['user_id']])
    f = request.files['img']
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']) + f.filename))
    url = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']) + f.filename)
    db.execute('UPDATE users SET img=(?) WHERE id = (?);', [url, session['user_id']])
    db.commit()

    print('decided to set', request.form['first_name'], 'new first name', db.execute('select first_name from users where id = (?)', [session['user_id']]).fetchone())
    return redirect(url_for('profile'))

@app.route('/profile', methods=['GET'])
def profile():
    if session.get('logged_in') == False:
        return redirect(url_for('start_site'))
        
    db = get_db()
    fn = db.execute('select first_name from users where id = (?)', [session['user_id']]).fetchone()[0]
    ln = db.execute('select last_name from users where id = (?)', [session['user_id']]).fetchone()[0]
    experience = db.execute('select experience from users where id = (?)', [session['user_id']]).fetchone()[0]
    achievments = db.execute('select achievments from users where id = (?)', [session['user_id']]).fetchone()[0]
    img = db.execute('select img from users where id = (?)', [session['user_id']]).fetchone()[0]
    error_message = None

    if request.method == 'GET':
        return render_template('profile.html', first_name=fn, last_name=ln, experience=experience, achievments=achievments, error_message=error_message, file=img)

@app.route('/resume', methods=['GET'])
def resume():
    if session.get('logged_in') == False:
        return redirect(url_for('start_site'))
    
    db = get_db()
    fn = db.execute('select first_name from users where id = (?)', [session['user_id']]).fetchone()[0]
    ln = db.execute('select last_name from users where id = (?)', [session['user_id']]).fetchone()[0]
    experience = db.execute('select experience from users where id = (?)', [session['user_id']]).fetchone()[0]
    achievments = db.execute('select achievments from users where id = (?)', [session['user_id']]).fetchone()[0]
    img = db.execute('select img from users where id = (?)', [session['user_id']]).fetchone()[0]
    error_message = None

    if request.method == 'GET':
        return render_template('resume.html', first_name=fn, last_name=ln, experience=experience, achievments=achievments, error_message=error_message, file=img)

@app.route('/download_resume', methods=['POST'])
def download_resume():
    if session.get('logged_in') == False:
        return redirect(url_for('start_site'))

    db = get_db()
    fn = db.execute('select first_name from users where id = (?)', [session['user_id']]).fetchone()[0]
    ln = db.execute('select last_name from users where id = (?)', [session['user_id']]).fetchone()[0]
    experience = db.execute('select experience from users where id = (?)', [session['user_id']]).fetchone()[0]
    achievments = db.execute('select achievments from users where id = (?)', [session['user_id']]).fetchone()[0]
    img = db.execute('select img from users where id = (?)', [session['user_id']]).fetchone()[0]
    img_abs = img
    if img != None:
        img_abs = os.path.abspath(img)
    error_message = None

    print('HELLO!!!!')
    print(os.path.join(app.config['DOWNLOAD_FOLDER'], fn + ln + '.pdf'))
    pdf_template = render_template('resume_no_buttons.html', first_name=fn, last_name=ln, experience=experience, achievments=achievments, error_message=error_message, file=img_abs)

    print(os.path.abspath(os.path.join(app.config['DOWNLOAD_FOLDER'], fn + ln + '.pdf')))
    pdfkit.from_string(pdf_template, os.path.abspath(os.path.join(app.config['DOWNLOAD_FOLDER'], fn + ln + '.pdf')), options={"enable-local-file-access": ""})
    
    return render_template('resume.html', first_name=fn, last_name=ln, experience=experience, achievments=achievments, error_message=error_message, file=img)

@app.route('/logout')
def logout():
    session.clear()
    session['logged_in'] = False
    return redirect(url_for('start_site'))