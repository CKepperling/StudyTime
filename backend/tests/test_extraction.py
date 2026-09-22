import base64
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.user import User
from app.storage import UPLOAD_DIR
from app.workers.tasks import extract_document_text

client = TestClient(app)

TEST_PASSWORD = "TestPassword123!"

# A tiny real PDF (built with reportlab, not hand-written here) whose
# only content is the text "Hello StudyTime" - this is what proves the
# worker extracts REAL text, not just that it doesn't crash on a
# well-formed file.
REAL_PDF_WITH_TEXT = base64.b64decode(
    "JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3Vy"
    "Y2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAv"
    "SGVsdmV0aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAv"
    "VHlwZTEgL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDcgMCBSIC9N"
    "ZWRpYUJveCBbIDAgMCAyMDAgMjAwIF0gL1BhcmVudCA2IDAgUiAvUmVzb3VyY2VzIDw8Ci9Gb250"
    "IDEgMCBSIC9Qcm9jU2V0IFsgL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSSBdCj4+"
    "IC9Sb3RhdGUgMCAvVHJhbnMgPDwKCj4+IAogIC9UeXBlIC9QYWdlCj4+CmVuZG9iago0IDAgb2Jq"
    "Cjw8Ci9QYWdlTW9kZSAvVXNlTm9uZSAvUGFnZXMgNiAwIFIgL1R5cGUgL0NhdGFsb2cKPj4KZW5k"
    "b2JqCjUgMCBvYmoKPDwKL0F1dGhvciAoYW5vbnltb3VzKSAvQ3JlYXRpb25EYXRlIChEOjIwMjYw"
    "OTIyMDAzOTU3LTA0JzAwJykgL0NyZWF0b3IgKGFub255bW91cykgL0tleXdvcmRzICgpIC9Nb2RE"
    "YXRlIChEOjIwMjYwOTIyMDAzOTU3LTA0JzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExp"
    "YnJhcnkgLSBcKG9wZW5zb3VyY2VcKSkgCiAgL1N1YmplY3QgKHVuc3BlY2lmaWVkKSAvVGl0bGUg"
    "KHVudGl0bGVkKSAvVHJhcHBlZCAvRmFsc2UKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0NvdW50IDEg"
    "L0tpZHMgWyAzIDAgUiBdIC9UeXBlIC9QYWdlcwo+PgplbmRvYmoKNyAwIG9iago8PAovRmlsdGVy"
    "IFsgL0FTQ0lJODVEZWNvZGUgL0ZsYXRlRGVjb2RlIF0gL0xlbmd0aCAxMDYKPj4Kc3RyZWFtCkdh"
    "cFFoMEU9RiwwVVxIM1RccE5ZVF5RS2s/dGM+SVAsO1cjVTFeMjNpaFBFTV8/Q1c0S0lTaFwmZEFP"
    "SStoN3B1KmlWLltxJE9xYVYoJVpRUkNUO2MkNmBPWiteLSNdJD0hUkBYcVs2fj5lbmRzdHJlYW0K"
    "ZW5kb2JqCnhyZWYKMCA4CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDA2MSAwMDAwMCBuIAow"
    "MDAwMDAwMDkyIDAwMDAwIG4gCjAwMDAwMDAxOTkgMDAwMDAgbiAKMDAwMDAwMDM5MiAwMDAwMCBu"
    "IAowMDAwMDAwNDYwIDAwMDAwIG4gCjAwMDAwMDA3MjEgMDAwMDAgbiAKMDAwMDAwMDc4MCAwMDAw"
    "MCBuIAp0cmFpbGVyCjw8Ci9JRCAKWzxkYWRkZjFhZjFlYjQzZTNhODE0MDQ5NmNjOTVmNjU0Yz48"
    "ZGFkZGYxYWYxZWI0M2UzYTgxNDA0OTZjYzk1ZjY1NGM+XQolIFJlcG9ydExhYiBnZW5lcmF0ZWQg"
    "UERGIGRvY3VtZW50IC0tIGRpZ2VzdCAob3BlbnNvdXJjZSkKCi9JbmZvIDUgMCBSCi9Sb290IDQg"
    "MCBSCi9TaXplIDgKPj4Kc3RhcnR4cmVmCjk3NgolJUVPRgo="
)

# A well-formed PDF with one page but no text or fonts on it at all -
# the kind of thing an image-only scanned slide deck would produce.
BLANK_PDF_NO_TEXT = base64.b64decode(
    "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWyA0"
    "IDAgUiBdCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9Qcm9kdWNlciAocHlwZGYpCj4+CmVuZG9iagoz"
    "IDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAxIDAgUgo+PgplbmRvYmoKNCAwIG9iago8"
    "PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Cj4+Ci9NZWRpYUJveCBbIDAuMCAwLjAgMjAwIDIw"
    "MCBdCi9QYXJlbnQgMSAwIFIKPj4KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAK"
    "MDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDc0IDAwMDAwIG4gCjAwMDAwMDAxMTMgMDAwMDAg"
    "biAKMDAwMDAwMDE2MiAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMyAwIFIKL0lu"
    "Zm8gMiAwIFIKPj4Kc3RhcnR4cmVmCjI1NgolJUVPRgo="
)

GARBAGE_BYTES = b"this is not a pdf at all, just some random bytes"


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_user():
    """A fresh, signed-up user, returned as a User row (not a token) -
    these tests build Document rows directly rather than going through
    the upload endpoint, since they're testing the WORKER, not the API.
    """
    email = unique_email()
    client.post("/auth/signup", json={"email": email, "password": TEST_PASSWORD})

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.expunge(user)
    db.close()

    yield user

    db = SessionLocal()
    db.query(Document).filter(Document.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def _make_document(user, storage_path: str) -> int:
    db = SessionLocal()
    document = Document(
        user_id=user.id,
        filename="test.pdf",
        storage_path=storage_path,
        status="pending",
    )
    db.add(document)
    db.commit()
    document_id = document.id
    db.close()
    return document_id


def _status_of(document_id: int) -> str:
    db = SessionLocal()
    document = db.get(Document, document_id)
    status_value = document.status
    db.close()
    return status_value


def test_extract_success(test_user):
    storage_path = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / storage_path).write_bytes(REAL_PDF_WITH_TEXT)
    document_id = _make_document(test_user, storage_path)

    extract_document_text(document_id)

    db = SessionLocal()
    document = db.get(Document, document_id)
    assert document.status == "extracted"
    assert "Hello StudyTime" in document.extracted_text
    db.close()

    (UPLOAD_DIR / storage_path).unlink(missing_ok=True)


def test_extract_no_text_found(test_user):
    storage_path = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / storage_path).write_bytes(BLANK_PDF_NO_TEXT)
    document_id = _make_document(test_user, storage_path)

    extract_document_text(document_id)

    assert _status_of(document_id) == "no_text_found"

    (UPLOAD_DIR / storage_path).unlink(missing_ok=True)


def test_extract_corrupt_file_marks_failed(test_user):
    storage_path = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / storage_path).write_bytes(GARBAGE_BYTES)
    document_id = _make_document(test_user, storage_path)

    extract_document_text(document_id)

    assert _status_of(document_id) == "extraction_failed"

    (UPLOAD_DIR / storage_path).unlink(missing_ok=True)


def test_extract_missing_file_marks_failed(test_user):
    # storage_path points at a file that was never written - simulates
    # it being deleted out from under the worker.
    document_id = _make_document(test_user, "does-not-exist.pdf")

    extract_document_text(document_id)

    assert _status_of(document_id) == "extraction_failed"


def test_extract_missing_document_does_not_raise():
    # A document_id that doesn't exist at all (deleted before the
    # worker got to it) - the task should just return quietly.
    extract_document_text(999999999)


def test_upload_triggers_extraction_end_to_end(test_user):
    """With CELERY_TASK_ALWAYS_EAGER set (as it is in CI/tests), the
    extraction task runs synchronously as part of handling the upload
    request - so by the time the response comes back, the DATABASE
    already reflects the final status (even though the JSON response
    itself still shows "pending", captured before the task ran).
    """
    login = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": TEST_PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    client.post(
        "/documents",
        files={"file": ("real.pdf", REAL_PDF_WITH_TEXT, "application/pdf")},
        headers=headers,
    )

    response = client.get("/documents", headers=headers)
    documents = response.json()

    assert len(documents) == 1
    assert documents[0]["status"] == "extracted"
