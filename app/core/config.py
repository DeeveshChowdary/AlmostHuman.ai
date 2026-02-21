import os

class Settings:
    PROJECT_NAME: str = "AlmostHuman.ai API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Add other configuration variables here, mapped to environment variables
    # e.g., DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()
