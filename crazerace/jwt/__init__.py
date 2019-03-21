# Standard library
from dataclasses import dataclass
from datetime import datetime, timedelta

# 3rd party modules
import jwt

# Internal modules
from crazerace.http.error import BadRequestError, UnauthorizedError


DEFAULT_EXPIRY: int = 24 * 3600
DEFAULT_ALGORITHM: str = "HS256"


@dataclass
class TokenBody:
    subject: str
    role: str


def create_token(
    sub: str,
    role: str,
    secret: str,
    expiry: int = DEFAULT_EXPIRY,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    issued_at = datetime.utcnow().strftime("%s")
    not_before = (datetime.utcnow() - timedelta(seconds=60)).strftime("%s")
    expires_at = (datetime.utcnow() + timedelta(seconds=expiry)).strftime("%s")
    payload = {
        "sub": sub,
        "role": role,
        "iss": int(issued_at),
        "nbf": int(not_before),
        "exp": int(expires_at),
    }
    return jwt.encode(payload, secret, algorithm=algorithm).decode()


def decode(token: str, secret: str, algorithm: str = DEFAULT_ALGORITHM) -> TokenBody:
    try:
        token = jwt.decode(token, secret, algorithms=[algorithm])
        return TokenBody(subject=token["sub"], role=token["role"])
    except KeyError:
        raise BadRequestError()
    except jwt.PyJWTError as e:
        raise UnauthorizedError()

