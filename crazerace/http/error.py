# Standard library
import json
from uuid import uuid4
from typing import Dict, Any

# 3rd party modules
from flask import request

# Internal modules
from crazerace.http import status


class RequestError(Exception):
    """Error for failed requests.

    message: Error message as a string.
    """

    def __init__(self, message: str) -> None:
        self.id = str(uuid4()).lower()
        self.message = message

    def __str__(self) -> str:
        return (
            f"RequestError(id={self.id}, status={self.status()} "
            f"message={self.message} path={request.path} requestId={request.id})"
        )

    def asdict(self) -> Dict[str, Any]:
        return {
            "errorId": self.id,
            "status": self.status(),
            "message": self.message,
            "path": request.path,
            "requestId": request.id,
        }

    def status(self) -> int:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


class BadRequestError(RequestError):
    """Error for when the client issued a faulty request."""

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_400_BAD_REQUEST


class UnauthorizedError(RequestError):
    """Error for when the client cannot be authorized to make a request."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_401_UNAUTHORIZED


class ForbiddenError(RequestError):
    """Error for when the client is identified but forbidden to make the request."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_403_FORBIDDEN


class NotFoundError(RequestError):
    """Error for when a resource is not found."""

    def __init__(self, message: str = "Not found"):
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_404_NOT_FOUND


class MethodNotAllowedError(RequestError):
    """Error for when a resource is called with an incorrect method."""

    def __init__(self, message: str = "Method not allowed"):
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_405_METHOD_NOT_ALLOWED


class ConflictError(RequestError):
    """Error for when a resource conflicts with another."""

    def __init__(self, message: str = "Conflict"):
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_409_CONFLICT


class PreconditionRequiredError(RequestError):
    """Error for when a precondtiton is required for the request to be possible."""

    def __init__(self, message: str = "Precondition required"):
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_428_PRECONDITION_REQUIRED


class InternalServerError(RequestError):
    """Error for when an unexpected error occured int the server."""

    def __init__(self, message: str = "Internal error"):
        super().__init__(message)


class BadGatewayError(RequestError):
    """Error for whan an unexpected error happened in a downstream dependency"""

    def __init__(self, message: str = "Bad gateway"):
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_502_BAD_GATEWAY


class ServiceUnavilableError(RequestError):
    """Error for when an the service is a state where it ould not be able to serve request."""

    def __init__(self, message: str = "Service Unavilable"):
        super().__init__(message)

    def status(self) -> int:
        return status.HTTP_503_SERVICE_UNAVAILIBLE


class NotImplementedError(RequestError):
    """Error for when an endpoint has not been implemented."""

    def __init__(self) -> None:
        super().__init__("Not implemented")

    def status(self) -> int:
        return status.HTTP_501_NOT_IMPLEMENTED


class DatabaseError(RequestError):
    """Error for whan an unexpected error occured during database interactions."""

    def __init__(self, cause_message: str) -> None:
        super().__init__("Database interaction error")
        self._cause_message = cause_message

    def full_message(self) -> str:
        return f"DatabaseError(id={self.id} cause=[{self._cause_message}])"
