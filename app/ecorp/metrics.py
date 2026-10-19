from __future__ import annotations

from flask import Flask
from prometheus_client import CollectorRegistry, Counter
from prometheus_flask_exporter import PrometheusMetrics


def init_metrics(app: Flask) -> PrometheusMetrics:
    registry = CollectorRegistry()
    metrics = PrometheusMetrics(app, path="/metrics", registry=registry)
    metrics.info("ecorp_app_info", "E-Corp application build info", version="1.0.0")

    login_attempts = Counter(
        "ecorp_login_attempts_total",
        "Total login attempts, by outcome",
        ["outcome"],
        registry=registry,
    )
    app.extensions["ecorp_login_attempts"] = login_attempts
    return metrics


def record_login_attempt(app: Flask, outcome: str) -> None:
    app.extensions["ecorp_login_attempts"].labels(outcome=outcome).inc()
