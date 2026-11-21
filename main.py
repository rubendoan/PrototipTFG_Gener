from fastapi import FastAPI, Response 

#Creació de l'objecte FastAPI( la app) amb informació de la API.
app = FastAPI(
    title="Laboratorio de seguridad de APIs",
    version="0.1.1",
)

#Funcionalitats de les APIS

@app.get("/health")
def health(response: Response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return {"status": "ok"}


@app.get("/health/missing-header")
def health_missing_header():
    """Cas de vulnerabilitat esperada: omitim el header X-Content-Type-Options"""
    return {"status": "ok"}