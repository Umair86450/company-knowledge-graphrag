from fastapi import FastAPI

app = FastAPI(title="Multi-User AI Chatbot")


@app.get("/")
def root() -> dict:
    return {"message": "Chatbot backend is running"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}