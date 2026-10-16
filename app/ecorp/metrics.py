"""prometheus metrics, there were none before,

prometheus for http metrics, plus a counter for login attempts"""

from __future__ import annotations

from flask import Flask
from prometheus_client import Counter
from prometheus_flask_exporter import PrometheusMetrics

LOGIN_ATTEMPTS = Counter(
    "ecorp_login_attempts_total",
    "Total login attempts, by outcome",
    ["outcome"],
)


def init_metrics(app: Flask) -> PrometheusMetrics:
    metrics = PrometheusMetrics(app, path="/metrics")
    metrics.info("ecorp_app_info", "E-Corp application build info", version="1.0.0")
    return metrics


def record_login_attempt(outcome: str) -> None:
    LOGIN_ATTEMPTS.labels(outcome=outcome).inc()
