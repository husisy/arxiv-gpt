import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
import sqlite3
import json

from ._init import login, db

#the tables of sql and related caculations are wirtten here

# User table
class User(UserMixin,db.Model):
    uid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    Is_adm = db.Column(db.Integer)
    message = db.relationship('message', backref='User', lazy='dynamic')
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def get_id(self):
        return self.uid

    def get_user_name(self):
        return self.username

    def if_adm(self):
        return self.Is_adm

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# paper table
class paper(db.Model):
    pid = db.Column(db.Integer, primary_key=True)
    arxivID = db.Column(db.String(50), unique=True)
    meta_info_json_path = db.Column(db.String(100), unique=True)
    pdf_path = db.Column(db.String(100), unique=True, default='')
    tex_path = db.Column(db.String(100), unique=True, default='')
    chunk_text_json_path = db.Column(db.String(100), default='')
    num_chunk = db.Column(db.Integer, default=0)
    message = db.relationship('message', backref='paper', lazy='dynamic')
    def __repr__(self):
        return '<paper {}>'.format(self.arxivID)

    def get_id(self):
        return self.pid
    def get_arxivID(self):
        return self.arxivID
    # get title from meta-info.json
    def get_title(self):
        with open(os.path.join(os.environ['ARXIV_DIRECTORY'], self.meta_info_json_path), 'r') as fid:
            meta_info = json.load(fid)
        return meta_info['title']
    def get_pdf_url(self):
        with open(os.path.join(os.environ['ARXIV_DIRECTORY'], self.meta_info_json_path), 'r') as fid:
            meta_info = json.load(fid)
        return meta_info['pdf_url']


# message table
class message(db.Model):
    mid = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer, db.ForeignKey('paper.pid'))
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'))
    content = db.Column(db.String(500))
    time = db.Column(db.DateTime)
    def __repr__(self):
        return '<"message": {},'.format(self.content)+'"time": {}'.format(self.time)+">"

# init_db() is used to initialize the database, it should be called only once
def init_db():
    # create the database and the db table
    db.drop_all()
    db.create_all()
    db.session.commit()
    # insert some test data
    conn = sqlite3.connect('app.db')
    print('opened database successfully')
    c = conn.cursor()
    sql_query = "UPDATE paper SET  meta_info_json_path = 'arxiv//test_paper1//meta-info.json' where pid = 1;"
    c.execute(sql_query)
    conn.commit()
    sql_query = "UPDATE paper SET  meta_info_json_path = 'arxiv//test_paper2//meta-info.json' where pid = 2;"
    c.execute(sql_query)
    conn.commit()
    # show the table
    contents = c.execute("SELECT * FROM paper")
    for row in contents:
        print(row)

# with app.app_context():
#     init_db()
