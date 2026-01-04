import os
from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "Isma-Ultra-Rules")


    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing from environment")

    # Always store sqlite DB inside the project /instance folder
    DB_PATH = os.path.join(BASE_DIR, "instance", "app.db")

    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + DB_PATH
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
