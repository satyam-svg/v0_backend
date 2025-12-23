from os import environ
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST = environ.get('DB_HOST')
    DB_USER = environ.get('DB_USER')
    DB_PASSWORD = environ.get('DB_PASSWORD')
    DB_NAME = environ.get('DB_NAME')
    DB_PORT = environ.get('DB_PORT', '3306')
    
    if DB_USER and DB_PASSWORD and DB_HOST and DB_NAME:
        SQLALCHEMY_DATABASE_URI = f'mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///v0_backend.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False