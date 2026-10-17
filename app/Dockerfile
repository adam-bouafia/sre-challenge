# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-compile --prefix=/install -r requirements.txt


FROM python:3.12-slim AS runtime

RUN groupadd --system --gid 10001 ecorp \
    && useradd --system --uid 10001 --gid ecorp --home-dir /app --shell /usr/sbin/nologin ecorp \
    && mkdir -p /data /tmp/prometheus-multiproc \
    && chown ecorp:ecorp /data /tmp/prometheus-multiproc

COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=ecorp:ecorp ecorp ./ecorp
COPY --chown=ecorp:ecorp templates ./templates
COPY --chown=ecorp:ecorp static ./static
COPY --chown=ecorp:ecorp gunicorn.conf.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV FLASK_APP=ecorp \
    DATABASE_PATH=/data/ecorp.db \
    GUNICORN_BIND=0.0.0.0:8000 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus-multiproc

USER 10001:10001
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
