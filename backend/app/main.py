from fastapi import FastAPI

app = FastAPI(title="StudyTime API")


@app.get("/health")
def health():
    return {"status": "ok"}