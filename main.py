from fastapi import FastAPI

app = FastAPI(
    title="Laboratorio de seguridad de APIs",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}