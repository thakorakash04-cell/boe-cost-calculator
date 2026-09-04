import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "BOE Cost Calculator"
    APP_VERSION: str = "1.0.0"

    # Anthropic API Settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-20250514")

    # File Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    TEMPLATE_PATH: str = os.path.join(BASE_DIR, "templates", "BOE_Cost_Calculation_Form.xlsx")
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")

settings = Settings()

if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR)