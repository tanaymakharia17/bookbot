import os

BACKEND_URL = os.getenv("BOOKBOT_BACKEND_URL", "http://localhost:8000")
USE_MOCK = os.getenv("BOOKBOT_USE_MOCK", "true").lower() == "true"