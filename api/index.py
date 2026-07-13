"""Vercel Python 서버리스 진입점.

Vercel이 ASGI 앱을 감지하려면 모듈 최상위에서 FastAPI app 인스턴스를 노출해야 한다.
"""
from app.main import app  # noqa: F401
