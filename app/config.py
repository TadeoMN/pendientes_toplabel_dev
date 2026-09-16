import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'toplabel_default_secret_key')
    
    # Credenciales por defecto ajustadas a toplabel_user
    DB_USER = os.getenv('DB_USER', 'toplabel_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'TopLabel2026!')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'toplabel_pendientes')
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True
    }
    API_AUTH_TOKEN = os.getenv('API_AUTH_TOKEN', 'toplabel_ai_agent_token_secret_2026')
