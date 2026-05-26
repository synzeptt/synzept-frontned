import pytest
from fastapi.testclient import TestClient

from app.core.reliability import sanitize_log_value
from app.infrastructure.monitoring import PerformanceMonitor
from app.main import app
from app.schemas.chat import ChatRequest


def test_chat_request_strips_nulls_and_rejects_blank_message():
    body = ChatRequest(message="  hello\x00  ")

    assert body.message == "hello"
    with pytest.raises(ValueError):
        ChatRequest(message="\x00   ")


def test_sanitize_log_value_redacts_secret_like_values():
    payload = sanitize_log_value({"authorization": "Bearer abc.def.ghi", "api_key": "sk-test"})

    assert payload["authorization"] == "[redacted]"
    assert "api_key" not in payload


def test_monitor_records_aggregate_snapshot():
    monitor = PerformanceMonitor()
    monitor.record("api.request", 120, "success", path="/health")
    monitor.record("api.request", 220, "error", path="/chat")

    snapshot = monitor.snapshot()

    assert snapshot["counts"]["api.request:success"] == 1
    assert snapshot["aggregates"]["api.request"]["max_ms"] == 220


def test_health_metrics_endpoint_is_available():
    response = TestClient(app).get("/health/metrics")

    assert response.status_code == 200
    assert "aggregates" in response.json()
