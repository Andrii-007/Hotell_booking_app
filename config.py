import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    
    # Get Database URL from environment
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Ensure it uses postgresql+pg8000:// for the pure Python driver
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
        elif DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
        
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
