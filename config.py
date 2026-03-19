import os
from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load .env file from the project root (works regardless of working directory)
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "Isma-Ultra-Rules")


    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Always store sqlite DB inside the project /instance folder
    DB_PATH = os.path.join(BASE_DIR, "instance", "app.db")

    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + DB_PATH
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
