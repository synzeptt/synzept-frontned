from .result import HealthResult
import time


def check_basic_health(connector, ctx):
    start = time.time()
    try:
        r = connector.health(ctx)
        latency = time.time() - start
        r.latency_seconds = latency
        return r
    except Exception as e:
        return HealthResult(available=False, latency_seconds=None, message=str(e), failures=1)
