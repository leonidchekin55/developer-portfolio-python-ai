from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
REQUESTS=Counter("http_requests_total","HTTP requests",["method","path","status"])
LATENCY=Histogram("http_request_duration_seconds","Request latency")
def metrics_response(): return generate_latest(),CONTENT_TYPE_LATEST
