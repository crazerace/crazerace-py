# Standard library
import logging
from functools import wraps
from uuid import uuid4
from typing import Any, Callable

# 3rd party modules.
from flask import request

# Internal modules
from .error import InternalServerError


_log = logging.getLogger("crazerace.http.instrumentation")


REQUEST_ID_HEADER: str = "X-Request-ID"


def add_request_id() -> None:
    """Adds a request id to an incomming request."""
    incomming_id: Optional[str] = request.headers.get(REQUEST_ID_HEADER)
    request.id = incomming_id or str(uuid4()).lower()
    _log.info(
        f"Incomming request {request.method} {request.path} requestId=[{request.id}]"
    )


def get_request_id(fail_if_missing: bool = True) -> str:
    try:
        return request.id
    except Exception as e:
        if fail_if_missing:
            raise InternalServerError(f"Getting request id failed. Exception=[{e}]")
        return ""


def trace(namespace: str) -> Callable:
    def trace_with_namespce(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs) -> Any:
            req_id = get_request_id(fail_if_missing=False)
            name: str = f"{namespace}.{f.__qualname__}]" if namespace else f.__qualname__
            _log.info(f"function=[{name}] requestId=[{req_id}]")
            return f(*args, **kwargs)

        return decorated

    return trace_with_namespce
