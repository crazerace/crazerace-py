# Standard library
import time
import sys
from datetime import datetime
from functools import wraps
from uuid import uuid4
from typing import Any, Callable, Set, Optional

# 3rd party modules.
import flask
import prometheus_client
from flask import request
from prometheus_client import Counter, Histogram, multiprocess, CollectorRegistry

# Internal modules
from crazerace import _log
from crazerace.http.error import InternalServerError


REQUEST_ID_HEADER: str = "X-Request-ID"
CONTENT_TYPE_LATEST = str("text/plain; version=0.0.4; charset=utf-8")
_IGNORED_METRIC_ROUTES: Set[str] = {"/health", "/metrics"}

metrics_registry = CollectorRegistry()
multiprocess.MultiProcessCollector(metrics_registry)

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Service Request Count",
    ["method", "endpoint", "http_status"],
    registry=metrics_registry,
)
REQUEST_LATENCY = Histogram(
    "request_latency_ms",
    "Request latency in milliseconds",
    ["method", "endpoint"],
    registry=metrics_registry,
)


def add_request_id() -> None:
    """Adds a request id to an incomming request."""
    incomming_id: Optional[str] = request.headers.get(REQUEST_ID_HEADER)
    request.id = incomming_id or str(uuid4()).lower()
    _log.info(
        f"Incomming request {request.method} {request.path} requestId=[{request.id}]"
    )


def add_request_id_to_response(response: flask.Response) -> flask.Response:
    """Adds request id header to each response.

    :param response: Response to add header to.
    :return: Response with header.
    """
    response.headers[REQUEST_ID_HEADER] = request.id
    response.headers["Date"] = f"{datetime.utcnow()}"
    return response


def get_request_id(fail_if_missing: bool = True) -> str:
    try:
        return request.id
    except Exception as e:
        if fail_if_missing:
            raise InternalServerError(f"Getting request id failed. Exception=[{e}]")
        return ""


def trace(namespace: str = "") -> Callable:
    def trace_with_namespace(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs) -> Any:
            name = f"{namespace}.{f.__qualname__}" if namespace else f.__qualname__
            req_id = get_request_id(fail_if_missing=False)
            _log.info(f"function=[{name}] requestId=[{req_id}]")
            return f(*args, **kwargs)

        return decorated

    return trace_with_namespace


def start_timer() -> None:
    request.start_time = time.time()


def stop_timer(response: flask.Response) -> flask.Response:
    if request.path not in _IGNORED_METRIC_ROUTES:
        latency = _calculate_latency(request.start_time)
        REQUEST_LATENCY.labels(request.method, _parse_endpoint()).observe(latency)
    return response


def record_request_data(response: flask.Response):
    if request.path not in _IGNORED_METRIC_ROUTES:
        REQUESTS_TOTAL.labels(
            request.method, _parse_endpoint(), response.status_code
        ).inc()
    return response


def _calculate_latency(start_time: float) -> float:
    end_time = time.time()
    milliseconds = (end_time - start_time) * 1e3
    return round(milliseconds, 2)


def _parse_endpoint() -> str:
    rule = request.url_rule
    return str(rule) if rule is not None else "NOT_FOUND"


def setup_instrumentation(app: flask.Flask) -> None:
    app.before_request(start_timer)
    app.before_request(add_request_id)
    # The order here matters since we want stop_timer
    # to be executed first
    app.after_request(record_request_data)
    app.after_request(stop_timer)
    app.after_request(add_request_id_to_response)

    @app.route("/metrics")
    def metrics():
        return flask.Response(
            prometheus_client.generate_latest(metrics_registry),
            mimetype=CONTENT_TYPE_LATEST,
        )
