from fastapi import FastAPI, Response 

app = FastAPI(
    title="Laboratorio de seguridad de APIs",
    version="0.1.1",
)


@app.get("/health")
def health(response: Response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return {"status": "ok"}