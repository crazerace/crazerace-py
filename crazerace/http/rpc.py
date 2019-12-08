# Standard library
import re
import os
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, MutableMapping, Optional, Union
from urllib3.exceptions import HTTPError

# 3rd party libraries
import requests
from requests.exceptions import RequestException

# Internal modules
from crazerace import _log, jwt
from crazerace.http import new_id, status
from crazerace.http.instrumentation import (
    trace,
    get_request_id,
    Timer,
    RPCS_TOTAL,
    RPC_LATENCY,
)


DEFAULT_RPC_TIMEOUT: int = 1
JWT_SECRET: str = os.environ["JWT_SECRET"] if not os.getenv(
    "CRAZERACE_DISABLE_RPC_CLIENT", "0"
) == "1" else ""


@dataclass(frozen=True)
class ResponseMetadata:
    status: int
    request_id: str
    latency: float
    headers: MutableMapping[str, str]


def default_json() -> Dict[str, Any]:
    return {}


@dataclass(frozen=True)
class RPCResponse:
    metadata: ResponseMetadata
    json: Any = field(default_factory=default_json)
    text: str = ""

    @classmethod
    def from_response(
        cls, res: requests.Response, request_id: str, latency: float
    ) -> "RPCResponse":
        metadata = ResponseMetadata(
            status=res.status_code,
            request_id=request_id,
            latency=latency,
            headers=res.headers,
        )
        if "application/json" in res.headers.get("Content-Type", ""):
            return cls(json=res.json(), metadata=metadata)
        return cls(text=res.text, metadata=metadata)


class RPCError(Exception):
    def __init__(self, url: str, message: str, status: int) -> None:
        self.id = new_id()
        self.url = url
        self.message = message
        self.status = status

    def __repr__(self) -> str:
        return (
            f"RPCError(id={self.id}, status={self.status} "
            f"message=[{self.message}] path={self.url} "
            f"requestId={get_request_id()})"
        )


@trace("rpc")
def get(
    url: str,
    user_id: Optional[str] = None,
    role: str = "SYSTEM",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_RPC_TIMEOUT,
) -> RPCResponse:
    return request("get", url, user_id, role, headers, timeout)


@trace("rpc")
def put(
    url: str,
    user_id: Optional[str] = None,
    role: str = "SYSTEM",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_RPC_TIMEOUT,
    body: Optional[Any] = None,
) -> RPCResponse:
    return request("put", url, user_id, role, headers, timeout, body)


@trace("rpc")
def post(
    url: str,
    user_id: Optional[str] = None,
    role: str = "SYSTEM",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_RPC_TIMEOUT,
    body: Optional[Any] = None,
) -> RPCResponse:
    return request("post", url, user_id, role, headers, timeout, body)


@trace("rpc")
def patch(
    url: str,
    user_id: Optional[str] = None,
    role: str = "SYSTEM",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_RPC_TIMEOUT,
    body: Optional[Any] = None,
) -> RPCResponse:
    return request("patch", url, user_id, role, headers, timeout, body)


@trace("rpc")
def delete(
    url: str,
    user_id: Optional[str] = None,
    role: str = "SYSTEM",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_RPC_TIMEOUT,
) -> RPCResponse:
    return request("delete", url, user_id, role, headers, timeout)


def request(
    method: str,
    url: str,
    user_id: Optional[str],
    role: str,
    headers: Optional[Dict[str, str]],
    timeout: int,
    body: Optional[Any] = None,
) -> RPCResponse:
    request_id = get_request_id(default=new_id())
    headers = headers if headers else {}
    request_headers = _create_headers(user_id, role, body, headers, request_id)
    _log_request_start(method, url, user_id, request_id)
    timer = Timer()
    try:
        res = _perform_request(method, url, request_headers, timeout, body)
        res.raise_for_status()
        latency = _record_rpc(method, url, request_id, res.status_code, timer)
        return RPCResponse.from_response(res, request_id, latency)
    except (RequestException, HTTPError) as e:
        code = _extract_status_code(e)
        _record_rpc(method, url, request_id, code, timer)
        _log.warning(f"RPC failed: requestId={request_id} error=[{repr(e)}]")
        raise RPCError(url=url, message=repr(e), status=code)


def _perform_request(
    method: str, url: str, headers: Dict[str, str], timeout: int, body: Optional[Any]
) -> requests.Response:
    res = (
        requests.request(method, url, headers=headers, timeout=timeout)
        if (method.lower() in ["get", "delete"] or not body)
        else requests.request(method, url, headers=headers, timeout=timeout, json=body)
    )
    if res.status_code >= status.HTTP_400_BAD_REQUEST:
        msg = f"RPC failed: requestId={get_request_id()} errorResponse=[{res.json()}]"
        _log.warning(msg)
    return res


def _create_headers(
    user_id: Optional[str],
    role: str,
    body: Optional[Any],
    headers: Dict[str, str],
    request_id: str,
) -> Dict[str, str]:
    request_headers = deepcopy(headers)
    request_headers["X-Request-ID"] = request_id
    if user_id:
        auth_token = jwt.create_token(sub=user_id, role=role, secret=JWT_SECRET)
        request_headers["Authorization"] = f"Bearer {auth_token}"
    if _should_add_content_type(request_headers, body):
        request_headers["Content-Type"] = _create_content_type(body)
    return request_headers


def _should_add_content_type(headers: Dict[str, str], body: Optional[Any]) -> bool:
    lower_case_headers = [h.lower() for h in headers.keys()]
    return "content-type" not in lower_case_headers and body is not None


def _create_content_type(body: Optional[Any]) -> str:
    if isinstance(body, str):
        return "text/plain; charset=utf-8"
    return "application/json; charset=utf-8"


def _record_rpc(
    method: str, url: str, request_id: str, status: int, timer: Timer
) -> float:
    latency = timer.stop()
    endpoint = _sanitize_endpoint(url)
    RPCS_TOTAL.labels(method, endpoint, status).inc()
    RPC_LATENCY.labels(method, endpoint, status).observe(latency)
    log = _log.info if status < 400 else _log.warning
    log(
        f"RPC done: {method.upper()} {url} status={status} "
        f"latency=[{latency} ms] requestId={request_id}"
    )
    return latency


def _log_request_start(
    method: str, url: str, user_id: Optional[str], request_id: str
) -> None:
    _log.info(
        f"RPC initiated: {method.upper()} {url} userId={user_id} requestId={request_id}"
    )


def _sanitize_endpoint(url: str) -> str:
    endpoint_without_query = url.split("?")[0]
    endpoint_without_uuid = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "<id>",
        endpoint_without_query,
    )
    endpoint_without_int_params = re.sub(r"\/[0-9]+", "/<id>", endpoint_without_uuid)
    return endpoint_without_int_params


def _extract_status_code(e: Union[RequestException, HTTPError]) -> int:
    default_code = status.HTTP_502_BAD_GATEWAY
    if isinstance(e, RequestException):
        return e.response.status_code if e.response else default_code
    return default_code
