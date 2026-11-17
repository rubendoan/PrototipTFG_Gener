# Prototip d’anàlisi de seguretat d’APIs

[English version](README.en.md)

Prototip del TFG: motor d’anàlisi de seguretat d’APIs integrat
amb MCP i models de llenguatge.

## Objectiu

Permetre que un client compatible amb MCP sol·liciti l’anàlisi
d’una API de laboratori i rebi un informe basat en els resultats
d’eines de seguretat.

## Estat actual

- Entorn virtual de Python preparat.
- API mínima creada amb FastAPI.
- Endpoint GET /health comprovat manualment.

Pendent: cas insegur, anàlisi amb ZAP, automatització,
processament de troballes, generació d’informes i integració MCP.

## Entorn utilitzat

- Windows 11.
- Python 3.14.8.
- Dependències Python registrades a requirements.txt.

Les instruccions actuals estan preparades per a PowerShell a Windows.
La compatibilitat amb altres sistemes està pendent de comprovar.

## Instal·lació

Des de la carpeta arrel del repositori, crear l’entorn virtual:

```powershell
py -3.14 -m venv .venv
```

Instal·lar les dependències:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La carpeta .venv no s’inclou a Git. Cada persona ha de crear
el seu propi entorn.

## Execució del laboratori

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

El servidor ha de continuar executant-se mentre s’utilitza l’API.
Per aturar-lo, prémer Ctrl + C.

## Comprovació manual

Obrir http://127.0.0.1:8000/health al navegador.

Resposta esperada:

```json
{"status":"ok"}
```

Documentació interactiva: http://127.0.0.1:8000/docs

## Abast del laboratori

L’API escolta únicament a l’adreça local 127.0.0.1.
Les anàlisis es faran sobre el laboratori propi.

La resposta de /health comprova que l’aplicació respon;
no demostra que sigui segura.

## Proves documentades

- [Prova 01: capçalera X-Content-Type-Options](docs\prova-01-capçalera-nosniff.md)