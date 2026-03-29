import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_default_connection_params():
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD
    }


def get_scraping_db_connection_params():
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": "scraping_database",
        "user": DB_USER,
        "password": DB_PASSWORD
    }