from flask_sqlalchemy import SQLAlchemy
import pyodbc
from config import Config

db = SQLAlchemy()

def get_sql_server_connection():
    """
    Establishes a connection to the external SQL Server.
    Returns: pyodbc connection object or None if failed.
    """
    try:
        connection_string = (
            f"DRIVER={{{Config.SQL_DRIVER}}};"
            f"SERVER={Config.SQL_SERVER_HOST};"
            f"DATABASE={Config.SQL_SERVER_DB};"
            f"UID={Config.SQL_SERVER_USER};"
            f"PWD={Config.SQL_SERVER_PASSWORD};"
            "TrustServerCertificate=yes;" # Often needed for local/self-signed certs
        )
        conn = pyodbc.connect(connection_string)
        return conn
    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        return None
