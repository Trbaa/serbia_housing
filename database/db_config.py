import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError, InterfaceError,DatabaseError

load_dotenv(".env.aws")
#load_dotenv(".env") Odkomentarisi samo kad hoces lokalno da radis


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


def ensure_connection(conn, cursor, get_params):
    try:
        # 1) nema konekcije ili je zatvorena
        if conn is None or conn.closed != 0:
            conn = psycopg2.connect(**get_params())
            cursor = conn.cursor()
            return conn, cursor

        # 2) ako je transakcija pukla, očisti je
        try:
            conn.rollback()
        except Exception:
            pass

        # 3) proveri da li konekcija i cursor stvarno rade
        cursor.execute("SELECT 1")
        cursor.fetchone()

    except (OperationalError, InterfaceError, DatabaseError):
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass

        try:
            if conn:
                conn.close()
        except Exception:
            pass

        conn = psycopg2.connect(**get_params())
        cursor = conn.cursor()

    return conn, cursor