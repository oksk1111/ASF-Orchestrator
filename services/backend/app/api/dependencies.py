from fastapi import Header

from app.core.security import TokenError, decode_access_token, unauthorized
from app.repositories.in_memory import repo


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized("Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise unauthorized("Missing bearer token")

    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise unauthorized("Invalid token") from exc

    user_id = payload.get("sub")
    if not user_id or repo.get_user(user_id) is None:
        raise unauthorized("Invalid user")

    return user_id
