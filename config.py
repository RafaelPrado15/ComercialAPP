import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-pradolux'
    # SQLite Database for User Management
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///pradolux.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQL Server Creds
    SQL_SERVER_USER = os.environ.get('SQL_SERVER_USER') or 'basico'
    SQL_SERVER_PASSWORD = os.environ.get('SQL_SERVER_PASSWORD') or 'uSxT@JWG@VMn'
    # Assuming the server address is needed, but user didn't provide it explicitly in the prompt.
    # I will add a placeholder or try to infer if there's a default. 
    # The user gave queries and credentials but not the HOST. I'll use a placeholder variable.
    SQL_SERVER_HOST = os.environ.get('SQL_SERVER_HOST') or '192.168.117.10' 
    SQL_SERVER_DB = os.environ.get('SQL_SERVER_DB') or 'Totvs12'
    # ODBC Driver 17 is standard for recent setups
    SQL_DRIVER = 'ODBC Driver 17 for SQL Server'
    
    # N8N Configuration
    # Webhook ID from 'Faq Inteligente.json': 3d061473-a4b8-4ee9-9796-848e05a5596e
    # User provided test URL
    N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL') or 'http://192.168.117.53:5678/webhook/77bf3863-6382-4322-af2f-8d39f961952b'
