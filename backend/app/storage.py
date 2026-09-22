import os
from pathlib import Path

# Where uploaded files actually live on disk. Configurable via env var
# (a real deployment would point this at a mounted volume or object
# storage) but defaults to a local "uploads" folder for dev/CI.
#
# Lives in its own module, rather than inside api/documents.py, so
# both the upload endpoint (writes files here) and the text-extraction
# worker (reads them back) share one definition instead of the worker
# reaching into the API layer for something that isn't really an API
# concern.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
