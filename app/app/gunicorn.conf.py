"""gunicorn config, why gunicorn to replace the flask dev server? i could use Waitress but gunicorn is more documented and it is the natural choice for flask behind nginx.

binds 127.0.0.1 localhost by default, matching the vm (nginx sits in front there).
container overrides this to 0.0.0.0 since its network namespace is already
isolated anyway.
"""

from __future__ import annotations

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
accesslog = "-"
errorlog = "-"

# gunicorn tries to create a little socket file for live control commands we
# never use. default spot is under $XDG_RUNTIME_DIR, which doesnt exist in
# the container, so it falls back to somewhere under the workdir - which is
# read-only, so that fails too. found this by running the built image with
# --read-only. we dont need the feature anyway, just turning it off instead
# of hunting for somewhere writable to put it

control_socket_disable = True



def child_exit(server, worker):
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client import multiprocess

        multiprocess.mark_process_dead(worker.pid)
