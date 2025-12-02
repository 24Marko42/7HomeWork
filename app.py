import os
import json
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, TextAreaField, BooleanField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.utils import secure_filename
import logging
import sys
import datetime

DISABLE_EMAIL = False 

if not DISABLE_EMAIL:
    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '0')) if os.environ.get('SMTP_PORT') else None
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASS = os.environ.get('SMTP_PASS')
    DEST_EMAIL = os.environ.get('DEST_EMAIL')

    missing = []
    if not SMTP_HOST:
        missing.append('SMTP_HOST')
    if not SMTP_PORT:
        missing.append('SMTP_PORT')
    if not SMTP_USER:
        missing.append('SMTP_USER')
    if not SMTP_PASS:
        missing.append('SMTP_PASS')
    if not DEST_EMAIL:
        missing.append('DEST_EMAIL')

    if missing:
        print("\n" + "="*60, file=sys.stderr)
        print("SMTP не настроен! Отправка заявок будет сохраняться в файл", file=sys.stderr)
        print(f"Отсутствуют параметры: {', '.join(missing)}", file=sys.stderr)
        print("Чтобы включить отправку email, задайте переменные окружения:", file=sys.stderr)
        print('  export SMTP_HOST="smtp.gmail.com"', file=sys.stderr)
        print('  export SMTP_PORT="587"', file=sys.stderr)
        print('  export SMTP_USER="you@gmail.com"', file=sys.stderr)
        print('  export SMTP_PASS="app_password_here"', file=sys.stderr)
        print('  export DEST_EMAIL="destination@example.com"', file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        DISABLE_EMAIL = True  # Автоматически отключаем email при отсутствии настроек

BASE = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'mars-mission-secret-2025'),
    UPLOAD_FOLDER=os.path.join(BASE, 'static', 'uploads'),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024
)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

def load_members():
    path = os.path.join(BASE, 'members', 'members.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        app.logger.warning(f"Файл {path} не найден. Создаю тестовые данные.")
        return [
            {
                "name": "Иван Петров",
                "photo": "default.jpg",
                "speciality": "Капитан корабля",
                "description": "Опытный пилот с 10-летним стажем"
            },
            {
                "name": "Мария Сидорова",
                "photo": "default.jpg",
                "speciality": "Главный инженер",
                "description": "Специалист по жизнеобеспечению"
            }
        ]

def save_application(data, photo_path=None, photo_name=None):
    """Сохраняет заявку в лог-файл вместо отправки email"""
    log_path = os.path.join(BASE, 'applications.log')
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Фамилия: {data['surname']}\n")
        f.write(f"Имя: {data['name']}\n")
        f.write(f"Email: {data['email']}\n")
        f.write(f"Образование: {data['education']}\n")
        f.write(f"Профессия: {data['profession']}\n")
        f.write(f"Пол: {data['sex']}\n")
        f.write(f"Готов остаться: {'Да' if data['ready'] else 'Нет'}\n\n")
        f.write(f"Мотивация:\n{data['motivation']}\n")
        if photo_name:
            f.write(f"\nФото сохранено: {photo_name}\n")
            f.write(f"Путь: {photo_path}\n")
        f.write(f"{'='*60}\n")

def send_email_with_attachment(subject: str, body: str, attachment_path: str = None, attachment_name: str = None):
    if DISABLE_EMAIL:
        raise Exception("Отправка email отключена в конфигурации")
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = DEST_EMAIL
    msg.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as fh:
            data = fh.read()
            subtype = (attachment_name or os.path.basename(attachment_path)).rsplit('.', 1)[-1].lower()
            msg.add_attachment(data, maintype='image', subtype=subtype, filename=(attachment_name or os.path.basename(attachment_path)))

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)

class ApplicantForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired(), Length(max=64)])
    name = StringField('Имя', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    education = StringField('Образование', validators=[DataRequired(), Length(max=128)])
    profession = SelectField('Профессия', choices=[
        ('инженер-исследователь','инженер-исследователь'),('пилот','пилот'),('строитель','строитель'),
        ('экзобиолог','экзобиолог'),('врач','врач'),('инженер по терраформированию','инженер по терраформированию'),
        ('климатолог','климатолог'),('специалист по радиационной защите','специалист по радиационной защите'),
        ('астрогеолог','астрогеолог'),('гляциолог','гляциолог'),('инженер жизнеобеспечения','инженер жизнеобеспечения'),
        ('метеоролог','метеоролог'),('оператор марсохода','оператор марсохода'),('киберинженер','киберинженер'),
        ('штурман','штурман'),('пилот дронов','пилот дронов')
    ], validators=[DataRequired()])
    sex = RadioField('Пол', choices=[('male','Мужской'),('female','Женский')], validators=[DataRequired()])
    motivation = TextAreaField('Мотивация', validators=[DataRequired(), Length(min=10)])
    ready = BooleanField('Готовы ли остаться на Марсе?')
    photo = FileField('Фото (макс. 5 МБ)')
    submit = SubmitField('Отправить заявку')

@app.route('/')
@app.route('/index')
def index():
    routes = [
        ('/list_prof/ol','Список профессий (ol)'),
        ('/list_prof/ul','Список профессий (ul)'),
        ('/distribution','Размещение'),
        ('/member/1','Член экипажа (1)'),
        ('/member/random','Член экипажа (random)'),
        ('/room/male/25','Оформление каюты (пример)'),
        ('/astronaut_selection','Запись добровольцем'),
        ('/galery','Галерея')
    ]
    return render_template('index.html', title='🚀 Марсианская миссия', routes=routes, username='Исследователь')

@app.route('/list_prof/<list_type>')
def list_prof(list_type):
    professions = [
        "Пилот космического корабля", "Инженер-исследователь", "Врач-космонавт", 
        "Экзобиолог", "Инженер систем жизнеобеспечения", "Климатолог", 
        "Астрогеолог", "Специалист по радиационной защите", "Оператор марсохода",
        "Метеоролог", "Киберинженер", "Строитель инфраструктуры"
    ]
    if list_type not in ('ol', 'ul'):
        return render_template('list_prof.html', title='Список профессий', bad=True, param=list_type)
    return render_template('list_prof.html', title='Требуются специалисты для Марса', professions=professions, list_type=list_type)

@app.route('/distribution')
def distribution():
    members = load_members()
    return render_template('distribution.html', title='Размещение экипажа', members=members)

@app.route('/member/<arg>')
def member(arg):
    members = load_members()
    if arg == 'random':
        import random
        member = random.choice(members)
        return render_template('member.html', title='Случайный член экипажа', member=member)
    
    try:
        idx = int(arg) - 1
        if 0 <= idx < len(members):
            return render_template('member.html', title='Член экипажа', member=members[idx])
        else:
            return render_template('member.html', title='Член экипажа', error='Неверный номер члена экипажа')
    except (ValueError, IndexError):
        return render_template('member.html', title='Член экипажа', error='Неверный параметр')

@app.route('/room/<sex>/<int:age>')
def room(sex, age):
    sex = sex.lower()
    if sex not in ('male', 'female'):
        return render_template('room.html', title='Оформление каюты', error='Неверный пол. Используйте "male" или "female"')
    
    theme = "blue" if sex == "male" else "purple"
    return render_template('room.html', title='Ваша каюта на Марсе', sex=sex, age=age, theme=theme)

@app.route('/astronaut_selection', methods=['GET', 'POST'])
def astronaut_selection():
    form = ApplicantForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        photo_filename = None
        photo_path = None
        
        if form.photo.data:
            f = form.photo.data
            if f.filename:
                photo_filename = secure_filename(f.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                f.save(photo_path)
                app.logger.info(f"Фото сохранено: {photo_path}")

        application_data = {
            'surname': form.surname.data,
            'name': form.name.data,
            'email': form.email.data,
            'education': form.education.data,
            'profession': form.profession.data,
            'sex': 'Мужской' if form.sex.data == 'male' else 'Женский',
            'ready': form.ready.data,
            'motivation': form.motivation.data
        }

        try:
            if DISABLE_EMAIL:
                save_application(application_data, photo_path, photo_filename)
                flash('Заявка успешно сохранена в файл applications.log!', 'success')
            else:
                body = (
                    f"Фамилия: {application_data['surname']}\n"
                    f"Имя: {application_data['name']}\n"
                    f"Email: {application_data['email']}\n"
                    f"Образование: {application_data['education']}\n"
                    f"Профессия: {application_data['profession']}\n"
                    f"Пол: {application_data['sex']}\n"
                    f"Готов остаться: {'Да' if application_data['ready'] else 'Нет'}\n\n"
                    f"Мотивация:\n{application_data['motivation']}\n"
                )
                send_email_with_attachment(
                    "Новая заявка на марсианскую миссию", 
                    body, 
                    photo_path, 
                    photo_filename
                )
                flash('✅ Заявка успешно отправлена по почте!', 'success')
        except Exception as e:
            app.logger.exception("Ошибка при обработке заявки")
            flash(f'Ошибка: {str(e)}', 'danger')
            # Всегда сохраняем в файл при ошибке отправки
            save_application(application_data, photo_path, photo_filename)
            flash('Заявка сохранена локально в applications.log', 'warning')

        return redirect(url_for('astronaut_selection', ok=1))

    ok = request.args.get('ok')
    return render_template(
        'astronaut_selection.html', 
        title='📝 Запись в добровольцы на Марс',
        form=form, 
        ok=ok,
        email_disabled=DISABLE_EMAIL
    )

@app.route('/galery', methods=['GET', 'POST'])
def galery():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('❌ Файл не выбран', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('⚠️ Пустое имя файла', 'warning')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash(f'Фото "{filename}" добавлено в галерею!', 'success')
            return redirect(url_for('galery'))

    images = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            images.append(url_for('static', filename=f'uploads/{filename}'))
    
    return render_template('galery.html', title='📸 Галерея марсианской миссии', images=images)

@app.route('/status')
def status():
    return render_template(
        'status.html',
        title='🔧 Статус системы',
        email_disabled=DISABLE_EMAIL,
        upload_folder=app.config['UPLOAD_FOLDER'],
        has_applications=os.path.exists(os.path.join(BASE, 'applications.log'))
    )

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Запуск марсианского приложения")
    print(f"Рабочая директория: {BASE}")
    print(f"Папка для загрузок: {app.config['UPLOAD_FOLDER']}")
    print(f"Отправка email: {'Отключена' if DISABLE_EMAIL else 'Включена'}")
    if not DISABLE_EMAIL:
        print(f"   Адрес получателя: {DEST_EMAIL}")
    print(f"Доступ по адресу: http://127.0.0.1:8080")
    print("="*70 + "\n")
    
    app.run(host='127.0.0.1', port=8080, debug=True)