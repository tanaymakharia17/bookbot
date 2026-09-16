import os

BACKEND_URL = os.getenv("BOOKBOT_BACKEND_URL", "http://localhost:8000")

# Browser-reachable backend URL (used for the fallback upload page link)
BACKEND_PUBLIC_URL = os.getenv("BOOKBOT_BACKEND_PUBLIC_URL", "http://localhost:8000")

# mock   -> in-memory only
# hybrid -> implemented APIs hit Django, the rest stay mock
# real   -> everything hits Django
API_MODE = os.getenv("BOOKBOT_API_MODE", "mock").lower()

# Accounting constant used to flag capitalizable items (IRS de minimis safe harbor).
DEFAULT_CAPEX_THRESHOLD = 2500.00