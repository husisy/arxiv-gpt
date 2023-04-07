import os

import dotenv

dotenv.load_dotenv()

class Config:
    SECRET_KEY = os.environ['SECRET_KEY']
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'+os.path.abspath(os.environ['SQLITE3_DB_PATH'])
    SQLALCHEMY_TRACK_MODIFICATIONS = False
