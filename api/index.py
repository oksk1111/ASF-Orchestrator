import os
import sys

# Make services/backend importable as 'app' package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "backend"))

from app.main import app  # noqa: F401  (Vercel reads the ASGI 'app' export)
