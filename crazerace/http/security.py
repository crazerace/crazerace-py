# Standard library
from typing import Callable, List, Optional
from functools import wraps

# 3rd party modules
from flask import request

# Internal modules
from crazerace import jwt
from .error import UnauthorizedError, BadRequestError, ForbiddenError


def secured(secret: str, roles: List[str] = []) -> Callable:
    def secured_with_roles(f) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs) -> Callable:
            token = _authorize(secret, roles)
            request.user_id = token.subject
            request.role = token.role
            return f(*args, **kwargs)

        return decorated

    return secured_with_roles


def _authorize(secret: str, roles: List[str]) -> jwt.TokenBody:
    encoded_token = _get_token_header()
    token = jwt.decode(encoded_token, secret)
    if request.role not in roles or not roles:
        raise ForbiddenError()
    return token


def _get_token_header() -> str:
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header:
        raise BadRequestError(message="Missing Authorization header")
    return auth_header.replace("Bearer ", "")
