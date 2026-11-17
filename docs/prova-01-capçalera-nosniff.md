# Prova 01 — Detecció i correcció d’una capçalera de seguretat absent

## Objectiu

Comprovar si ZAP detecta l’absència de la capçalera
X-Content-Type-Options en la resposta de GET /health i si deixa
de generar aquesta alerta després d’afegir-hi el valor nosniff.

## Entorn

- Sistema operatiu: Windows 11.
- Python: 3.14.8.
- ZAP: 2.17.0.
- Dependències Python: registrades a requirements.txt.
- API local: http://127.0.0.1:8000.
- Proxy de ZAP: http://127.0.0.1:8080.
- Tipus d’anàlisi: passiva sobre el trànsit enviat amb curl.
- No s’ha executat cap escaneig actiu en aquesta prova.

## Procediment

1. Arrencar l’API amb Uvicorn.
2. Enviar una petició GET /health a través del proxy de ZAP.
3. Esperar que la cua d’anàlisi passiva arribi a zero.
4. Revisar l’alerta i les capçaleres de la resposta.
5. Guardar les evidències del comportament inicial.
6. Afegir X-Content-Type-Options: nosniff a la resposta de /health.
7. Crear una sessió nova de ZAP, mantenint la configuració d’anàlisi.
8. Repetir la petició i esperar que acabi l’anàlisi passiva.
9. Revisar i guardar el resultat posterior a la correcció.

Comanda d’arrencada:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Petició a través de ZAP:

```powershell
curl.exe --proxy http://127.0.0.1:8080 http://127.0.0.1:8000/health
```

## Canvi aplicat

S’ha importat Response des de FastAPI i s’ha modificat l’endpoint:

```python
@app.get("/health")
def health(response: Response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return {"status": "ok"}
```

La versió declarada de l’aplicació passa de 0.1.0 a 0.1.1.
La correcció s’aplica únicament a aquest endpoint.

## Resultats observats

| Aspecte | Abans | Després |
|---|---|---|
| Endpoint | GET /health | GET /health |
| Estat HTTP | 200 OK | 200 OK |
| Cos | {"status":"ok"} | {"status":"ok"} |
| Content-Type | application/json | application/json |
| X-Content-Type-Options | Absent | nosniff |
| Alerta ZAP 10021 | Detectada | No observada |

En la prova inicial, ZAP classifica l’alerta amb risc baix
i confiança mitjana.

## Evidències

- Estat inicial: carpeta evidencies/01-baseline.
- Estat corregit: carpeta evidencies/02-nosniff.
- Cada carpeta conserva les capçaleres, el cos de resposta
  i l’informe JSON exportat de ZAP.

## Conclusió i limitacions

ZAP ha detectat l’absència de X-Content-Type-Options a /health.
Després d’afegir-hi nosniff i repetir la petició en una sessió nova,
no s’ha observat l’alerta 10021.

La prova valida la detecció i correcció d’aquesta configuració
concreta. No demostra una explotació ni que tota l’API sigui segura.
No s’han avaluat altres endpoints ni altres vulnerabilitats.

## Referència

Regla de ZAP 10021:
https://www.zaproxy.org/docs/alerts/10021/