import time
import json

from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest
from aiohttp import web

metric_registry = CollectorRegistry()
api_request_counter = Counter(
    'api_request_count', 'Inventory API request count',
    ['path', 'method', 'status', 'http_code', 'error_code'],
    registry=metric_registry
)
api_response_time_hist = Histogram(
    'api_response_time_seconds', 'Inventory API request time',
    ['path', 'method', 'status', 'http_code'],
    registry=metric_registry
)


def inc_api_request_counter(path, method, status, http_code, error_code=None):
    api_request_counter.labels(
        path=path,
        method=method,
        status=status,
        http_code=http_code,
        error_code=error_code
    ).inc()


def record_api_response_time(latency, path, method, status, http_code):
    api_response_time_hist.labels(
        path=path,
        method=method,
        status=status,
        http_code=http_code
    ).observe(latency)


@web.middleware
async def monitoring_middleware(request: web.Request, handler) -> web.StreamResponse:
    start_time = time.time()
    response = await handler(request)
    finish_time = time.time()
    response_time = finish_time - start_time

    if response.status == 200:
        status = 'ok'
        error_code = None
    else:
        status = 'error'
        try:
            error_code = json.loads(response.text)['error_code']
        except ValueError:
            error_code = 'unknown_code'

    inc_api_request_counter(
        path=request.path,
        method=request.method,
        status=status,
        http_code=response.status,
        error_code=error_code
    )
    record_api_response_time(
        response_time,
        path=request.path,
        method=request.method,
        status=status,
        http_code=response.status
    )
    return response

async def metrics_view(_request: web.Request):
    latest_metrics = generate_latest(metric_registry)
    data = latest_metrics.decode('utf-8')
    return web.Response(text=data, status=200, content_type="text/plain")


