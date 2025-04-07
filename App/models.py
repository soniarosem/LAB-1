
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    awarded_stickers = db.relationship('StudentSticker', backref='awarder', lazy=True)

    def __init__(self, username, password):
        self.username = username
        self.set_password(password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Student(db.Model):
    id = db.Column(db.String(9), primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    image = db.Column(db.String(200))
    programme = db.Column(db.String(100))
    start_year = db.Column(db.Integer)
    stickers = db.relationship('StudentSticker', backref='student', lazy=True)

class Sticker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), nullable=False)

class StudentSticker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(9), db.ForeignKey('student.id'), nullable=False)
    sticker_id = db.Column(db.Integer, db.ForeignKey('sticker.id'), nullable=False)
    awarded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_awarded = db.Column(db.DateTime, default=db.func.current_timestamp())
