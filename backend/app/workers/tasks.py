from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.db import SessionLocal
from app.models.document import Document
from app.storage import UPLOAD_DIR
from app.workers.celery_app import celery_app


@celery_app.task(name="extract_document_text")
def extract_document_text(document_id: int) -> None:
    """Pull the text out of an uploaded PDF and store it on the Document row.

    Runs in the Celery worker process, not the web request - this task
    is what api/documents.py's upload_document() hands off to via
    .delay(), so the person who uploaded the file gets an immediate
    201 response instead of waiting on however long extraction takes.

    Opens its own DB session rather than reusing one from a request,
    since this runs in a completely separate process (or synchronously
    in-process during tests, if CELERY_TASK_ALWAYS_EAGER is set) with
    no request-scoped session to borrow.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            # Deleted (or never committed - shouldn't happen) before the
            # worker got to it. Nothing to extract text into.
            return

        document.status = "processing"
        db.commit()

        try:
            reader = PdfReader(str(UPLOAD_DIR / document.storage_path))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, FileNotFoundError, OSError):
            # Corrupt PDF, an encrypted one pypdf can't open, or the
            # file's gone missing from disk - record the failure rather
            # than leaving the document stuck at "processing" forever.
            document.status = "extraction_failed"
            db.commit()
            return

        document.extracted_text = text
        # A PDF that's all images (scanned lecture slides with no
        # actual text layer) parses fine but yields nothing usable -
        # that's a distinct outcome from a hard extraction error, since
        # T31 (non-PDF/OCR support) is the eventual fix for it, not a bug
        # in this task.
        document.status = "extracted" if text.strip() else "no_text_found"
        db.commit()
    finally:
        db.close()
