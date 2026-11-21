# Prototip d’anàlisi de seguretat d’APIs

[English version](README.en.md)
- [Prova 01: capçalera X-Content-Type-Options](docs/prova-01-capçalera-nosniff.md)

Prototip del TFG: motor d’anàlisi de seguretat d’APIs integrat
amb MCP i models de llenguatge.

## Objectiu

Permetre que un client compatible amb MCP sol·liciti l’anàlisi
d’una API de laboratori i rebi un informe basat en els resultats
d’eines de seguretat.

## Estat actual

- Entorn virtual de Python preparat i dependències registrades.
- API de laboratori implementada amb FastAPI.
- GET /health retorna la capçalera X-Content-Type-Options: nosniff.
- GET /health/missing-header omet aquesta capçalera intencionadament.
- Peticions als dos endpoints enviades a través del proxy de ZAP.
- Alerta 10021 observada a /health/missing-header: absència de
  X-Content-Type-Options, amb risc baix i confiança mitjana.
- Consulta de la versió i de les alertes de ZAP des de check_zap.py.
- Resultats desats en fitxers JSON numerats amb la data de consulta.

Pendent: automatitzar l'enviament de peticions, l'espera de l'anàlisi
passiva i la separació dels resultats de cada execució; implementar
el processament de troballes, la generació de l'informe del motor
i la integració MCP.

Actualment, check_zap.py consulta les alertes existents de la sessió
de ZAP. No inicia una anàlisi nova.

## Entorn utilitzat

- Windows 11.
- Python 3.14.8.
- Dependències Python registrades a requirements.txt.
- ZAP 2.17.0, executat com a aplicació d'escriptori.
- Java 25.

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

## Prova manual amb ZAP

### Preparació

1. Arrencar l'API amb el comandament de l'apartat «Execució del laboratori».
2. Obrir l'aplicació ZAP.
3. Comprovar que el proxy principal de ZAP escolta a localhost:8080.
4. Per repetir la prova sense barrejar resultats anteriors, iniciar una
   sessió nova de ZAP. Desar prèviament la sessió anterior si es vol conservar.

L'API del laboratori escolta a 127.0.0.1:8000.
ZAP escolta al port 8080.

### Enviament de peticions

En una segona terminal de PowerShell, executar:

```powershell
curl.exe --% -i --noproxy "" --proxy http://127.0.0.1:8080 http://127.0.0.1:8000/health
```

```powershell
curl.exe --% -i --noproxy "" --proxy http://127.0.0.1:8080 http://127.0.0.1:8000/health/missing-header
```

El marcador --% evita que PowerShell interpreti els arguments següents.
En aquest procediment permet passar correctament les cometes buides
de --noproxy a curl.

Comprovar que les dues peticions apareixen a l'Historial de ZAP i
esperar que Passive Scan Queue arribi a 0.

### Resultat esperat i observat

Els dos endpoints retornen HTTP 200 i el cos {"status":"ok"}.

| Endpoint | Capçalera X-Content-Type-Options | Alerta 10021 |
|---|---|---|
| /health | nosniff | No observada |
| /health/missing-header | Absent | Observada |

La prova utilitza l'anàlisi passiva de ZAP sobre les respostes HTTP.
No s'ha executat un escaneig actiu en aquest experiment.

L'alerta té risc baix i confiança mitjana. El resultat demostra
la detecció d'una configuració de seguretat absent; no demostra
una explotació ni que l'altre endpoint estigui lliure de vulnerabilitats.

## Consulta i desament de les alertes amb Python

A ZAP, consultar la clau d'API a Herramientas → Opciones → API.

Crear un fitxer .env a l'arrel del projecte amb la clau de la
instal·lació local de ZAP:

```dotenv
ZAP_API_KEY=la_teva_clau_local
```

El fitxer .env ha d'estar exclòs de Git mitjançant .gitignore.
El repositori pot incloure un .env.example sense cap clau real:

```dotenv
ZAP_API_KEY=
```

Amb ZAP obert i la prova manual completada, executar:

```powershell
.\.venv\Scripts\python.exe check_zap.py
```

El script consulta la versió de ZAP i recupera les alertes corresponents
a l'adreça base http://127.0.0.1:8000.

Els resultats es guarden a:

```text
evidencies/resultats consulta-zap/
```

Cada execució crea un fitxer numerat: alertes-zap-1.JSON,
alertes-zap-2.JSON, etc.

El camp "consulta realitzada el dia" indica quan s'han consultat i
desat les dades, no necessàriament quan es van generar les alertes.

Aquests fitxers contenen la resposta de la consulta amb metadades
afegides pel script. No són una exportació completa de la sessió de ZAP.

## Abast del laboratori

L’API escolta únicament a l’adreça local 127.0.0.1.
Les anàlisis es faran sobre el laboratori propi.

La resposta de /health comprova que l’aplicació respon;
no demostra que sigui segura.

## Proves documentades

- [Prova 01: capçalera X-Content-Type-Options](docs\prova-01-capçalera-nosniff.md)