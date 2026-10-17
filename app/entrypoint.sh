#!/bin/sh
set -eu

mkdir -p "${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus-multiproc}"

flask init-db
exec gunicorn -c gunicorn.conf.py "ecorp:create_app()"
