import os

BACKEND_URL = os.getenv("BOOKBOT_BACKEND_URL", "http://localhost:8000")

# mock   -> in-memory only
# hybrid -> implemented APIs hit Django, the rest stay mock
# real   -> everything hits Django
API_MODE = os.getenv("BOOKBOT_API_MODE", "mock").lower()