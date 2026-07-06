import os


class Config:
    SERVICE_NAME = "smart-factory-ai-service"
    HOST = os.getenv("AI_SERVICE_HOST", "0.0.0.0")
    PORT = int(os.getenv("AI_SERVICE_PORT", "9000"))
    DEBUG = os.getenv("AI_SERVICE_DEBUG", "True").lower() == "true"
    BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000/api")
