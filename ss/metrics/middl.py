import time
from typing import Callable

from flask import request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define Prometheus metrics
REQUESTS = Counter(
    "http_requests_total",
    "Total number of requests",
    ["method", "path_template"],
)
RESPONSES = Counter(
    "http_responses_total",
    "Total number of responses",
    ["method", "path_template", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["method", "path_template"],
)
EXCEPTIONS = Counter(
    "http_exceptions_total",
    "Total number of exceptions",
    ["method", "path_template", "exception_type"],
)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method"],
)




ENDPOINT_MATCHER: list[tuple[Callable[[str], bool], str]] = [
    (lambda s: s.startswith("/api/v1/dashboard/"), "dashboard"),
    (lambda s: s.startswith("/api/v1/chart/"), "chart"),
    (lambda s: s.startswith("/api/v1/slice/"), "slice"),
    (lambda s: "/explore/" in s, "explore"),
]


def get_metric_label(rule):
    for matcher, label in ENDPOINT_MATCHER:
        if matcher(rule):
            return label
        return None


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

        @self.app.route("/metrics")
        def metrics():
            return Response(generate_latest(), mimetype="text/plain")

        @self.app.before_request
        def start_timer():
            REQUESTS_IN_PROGRESS.labels(request.method).inc()
            label = get_metric_label(request.path)
            if label:
                start_time = time.perf_counter()
                REQUESTS.labels(request.method, label).inc()

                request._start_time = start_time
                request._label = label

        @self.app.after_request
        def record_metrics(response):
            start = getattr(request, "_start_time", None)
            label = getattr(request, "_label", None)
            if start and label:
                latency = time.perf_counter() - start
                REQUEST_LATENCY.labels(request.method, label).observe(latency)
                RESPONSES.labels(request.method, label, str(response.status_code)).inc()

            return response

        @app.teardown_request
        def teardown_request(exc):
            REQUESTS_IN_PROGRESS.labels(request.method).dec()
            if exc is not None:
                EXCEPTIONS.labels(request.method, request.path, type(exc).__name__).inc()
                RESPONSES.labels(request.method, request.path, 500).inc()