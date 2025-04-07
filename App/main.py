import os, csv
from flask import Flask, redirect, render_template, jsonify, request, send_from_directory, flash, url_for
from sqlalchemy.exc import OperationalError, IntegrityError
from App.models import db, User, Student, Sticker, StudentSticker
from datetime import timedelta

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
    current_user,
    set_access_cookies,
    unset_jwt_cookies,
    current_user,
)


def create_app():
  app = Flask(__name__, static_url_path='/static')
  app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  app.config['TEMPLATES_AUTO_RELOAD'] = True
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
      app.root_path, 'data.db')
  app.config['DEBUG'] = True
  app.config['SECRET_KEY'] = 'MySecretKey'
  app.config['PREFERRED_URL_SCHEME'] = 'https'
  app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
  app.config['JWT_REFRESH_COOKIE_NAME'] = 'refresh_token'
  app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
  app.config["JWT_COOKIE_SECURE"] = True
  app.config["JWT_SECRET_KEY"] = "super-secret"
  app.config["JWT_COOKIE_CSRF_PROTECT"] = False
  app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

  app.app_context().push()
  return app


app = create_app()
db.init_app(app)

jwt = JWTManager(app)


@jwt.user_identity_loader
def user_identity_lookup(user):
  return user


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
  identity = jwt_data["sub"]
  return User.query.get(identity)


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
  flash("Your session has expired. Please log in again.")
  return redirect(url_for('login'))


def parse_students():
    with open('students.csv', mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            student = Student(
                id=row['ID'],
                first_name=row['FirstName'],
                image=row['Picture'],
                last_name=row['LastName'],
                programme=row['Programme'],
                start_year=row['YearStarted']
            )
            db.session.add(student)
    db.session.commit()

def create_users():
    users = [
        User(username="rob", password="robpass"),
        User(username="bob", password="bobpass"),
        User(username="sally", password="sallypass"),
        User(username="pam", password="pampass"),
        User(username="chris", password="chrispass")
    ]
    db.session.add_all(users)
    db.session.commit()

def create_stickers():
    stickers = [
        Sticker(name="Awesome", image="/static/stickers/awesome.png"),
        Sticker(name="Cool", image="/static/stickers/cool.png"),
        Sticker(name="Bravo", image="/static/stickers/bravo.png"),
        Sticker(name="Excellent", image="/static/stickers/excellent.png"),
        Sticker(name="Good Job", image="/static/stickers/good_job.png"),
        Sticker(name="Thumbs Up", image="/static/stickers/thumbs_up.png"),
        Sticker(name="Well Done", image="/static/stickers/well_done.png"),
        Sticker(name="Wonderful", image="/static/stickers/wonderful.png")
    ]
    db.session.add_all(stickers)
    db.session.commit()

def initialize_db():
    db.drop_all()
    db.create_all()
    create_users()
    parse_students()
    create_stickers()
    print('database initialized')


@app.route('/')
def login():
  return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_action():
  username = request.form.get('username')
  password = request.form.get('password')
  user = User.query.filter_by(username=username).first()
  if user and user.check_password(password):
    response = redirect(url_for('home'))
    access_token = create_access_token(identity=user.id)
    set_access_cookies(response, access_token)
    return response
  else:
    flash('Invalid username or password')
    return redirect(url_for('login'))


@app.route('/app')
@app.route('/app/<student_id>')
@jwt_required()
def home(student_id=None):
        students = Student.query.all()
        stickers = Sticker.query.all()
        selected_student = None

        if student_id:
            selected_student = Student.query.get(student_id)
            if selected_student:
                student_stickers = db.session.query(
                    StudentSticker, Sticker, User
                ).join(
                    Sticker, StudentSticker.sticker_id == Sticker.id
                ).join(
                    User, StudentSticker.awarded_by == User.id
                ).filter(
                    StudentSticker.student_id == student_id
                ).all()

                selected_student.stickers = [{
                    'id': ss.StudentSticker.id,
                    'name': s.name,
                    'image': s.image,
                    'date_awarded': ss.StudentSticker.date_awarded.strftime('%Y-%m-%d'),
                    'awarded_by': u.username,
                    'can_delete': u.id == current_user.id
                } for ss, s, u in student_stickers]

        if student_id:
            selected_student = Student.query.get(student_id)
            if selected_student:
                # Get stickers awarded to student with award info
                student_stickers = db.session.query(
                    StudentSticker, Sticker, User
                ).join(
                    Sticker, StudentSticker.sticker_id == Sticker.id
                ).join(
                    User, StudentSticker.awarded_by == User.id
                ).filter(
                    StudentSticker.student_id == student_id
                ).all()

                # Format sticker data for template
                selected_student.stickers = [{
                    'id': ss.StudentSticker.id,
                    'name': s.name,
                    'image': s.image,
                    'date_awarded': ss.StudentSticker.date_awarded,
                    'awarded_by': u.username,
                    'can_delete': u.id == current_user.id
                } for ss, s, u in student_stickers]

        return render_template('index.html', 
                             selected_student=selected_student, 
                             students=students,
                             stickers=stickers,
                             user=current_user)

@app.route('/give_sticker/<student_id>', methods=['POST'])
@jwt_required()
def give_sticker(student_id):
    sticker_id = request.form.get('sticker_id')
    
    # Check if sticker already awarded
    existing = StudentSticker.query.filter_by(
        student_id=student_id,
        sticker_id=sticker_id
    ).first()
    
    if existing:
        flash('This sticker has already been awarded to this student')
    else:
        new_sticker = StudentSticker(
            student_id=student_id,
            sticker_id=sticker_id,
            awarded_by=current_user.id
        )
        db.session.add(new_sticker)
        db.session.commit()
        flash('Sticker awarded successfully')
    
    return redirect(url_for('home', student_id=student_id))

@app.route('/delete_sticker/<sticker_award_id>')
@jwt_required()
def delete_sticker(sticker_award_id):
    sticker_award = StudentSticker.query.get(sticker_award_id)
    
    if sticker_award and sticker_award.awarded_by == current_user.id:
        student_id = sticker_award.student_id
        db.session.delete(sticker_award)
        db.session.commit()
        flash('Sticker removed successfully')
        return redirect(url_for('home', student_id=student_id))
    
    flash('You can only delete stickers that you awarded')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
  response = redirect(url_for('login'))
  unset_jwt_cookies(response)
  flash('logged out')
  return response


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)
