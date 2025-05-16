import time
from typing import Tuple

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp


# Метрики
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
REQUEST_DURATION = Histogram(
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
    ["method", "path_template"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: ASGIApp, allowed_prefixes: tuple[str] = ("/api/v1",), filter_unhandled_paths: bool = False
    ) -> None:
        super().__init__(app)
        self.filter_unhandled_paths = filter_unhandled_paths
        self.allowed_prefixes = allowed_prefixes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path_template, is_handled_path = self._get_path_template(request)

        if not any(path_template.startswith(api_prefix) for api_prefix in self.allowed_prefixes):
            return await call_next(request)

        if self._is_path_filtered(is_handled_path):
            return await call_next(request)

        REQUESTS_IN_PROGRESS.labels(method, path_template).inc()
        REQUESTS.labels(method, path_template).inc()
        start_time = time.perf_counter()

        status_code = HTTP_500_INTERNAL_SERVER_ERROR

        try:
            response = await call_next(request)
        except Exception as exc:
            EXCEPTIONS.labels(method, path_template, type(exc).__name__).inc()
            raise exc from None
        else:
            status_code = response.status_code
            duration = time.perf_counter() - start_time
            REQUEST_DURATION.labels(method, path_template).observe(duration)
        finally:
            RESPONSES.labels(method, path_template, status_code).inc()
            REQUESTS_IN_PROGRESS.labels(method, path_template).dec()

        return response

    @staticmethod
    def _get_path_template(request: Request) -> Tuple[str, bool]:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return getattr(route, "path", request.url.path), True
        return request.url.path, False

    def _is_path_filtered(self, is_handled_path: bool) -> bool:
        return self.filter_unhandled_paths and not is_handled_path


app.add_middleware(PrometheusMiddleware)

# Прометей эндпоинт
app.mount("/metrics", make_asgi_app())
