import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# include=[...] is how Celery finds task modules without this file
# importing tasks.py directly at the bottom - that would create an
# import cycle, since tasks.py needs `celery_app` (defined right here)
# to declare its own @celery_app.task functions. Whatever process
# starts this app - a `celery worker` command, or just calling
# .delay() from the API - gets tasks.py imported as a side effect.
celery_app = Celery(
    "studytime",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Runs a task synchronously, in the calling process, with no
    # broker or worker involved at all - set to "true" in tests/CI so
    # pytest can exercise the upload -> extraction flow without a real
    # Redis instance or a separate worker process running alongside it.
    task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower()
    == "true",
)
