import json
import os
import argparse
import time
from pathlib import Path

from datetime import datetime

import requests
from dotenv import load_dotenv


# Definim els arguments que accepta el programa per terminal.
parser = argparse.ArgumentParser(
    description="Consulta les alertes de ZAP del laboratori local.",
    allow_abbrev=False,
)

#Posem com a obligatori l'argument --target que indica la URL del laboratori a examinar.
parser.add_argument(
    "--target",
    required=True,
    help="URL base del laboratori. Exemple: http://127.0.0.1:8000",
)

# Llegim els arguments introduïts al terminal.
args = parser.parse_args()

# Eliminem la barra final si hi és per acceptar les dues formes de la URL.
target_url = args.target.removesuffix("/")

# Llista de les adreçes que podem examinar
allowed_targets = {
    "http://127.0.0.1:8000",  #Actualment això ens permet mantindre el control sobre quines adreçes podem examina.
}

# Comprovem l'objectiu abans de fer cap petició.
if target_url not in allowed_targets:
    parser.error(
        f"Adreça no permessa: {target_url}. "
        f"Adreces permeses: {', '.join(sorted(allowed_targets))}"
    )

print("Objectiu seleccionat:", target_url)
print()


#Busquem el fitxer env i agafem la clau d'API de ZAP.

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path) #carrega les variables del arxciu .env a variables del SO

api_key = os.getenv("ZAP_API_KEY")  


if not api_key:
    raise RuntimeError("Falta ZAP_API_KEY al fitxer .env.")

#Prepara client HTTP per comunicar-se amb ZAP i recupera la versió i les alertes.
with requests.Session() as session:
    session.trust_env = False

    #Envia petició GET a ZAP per obtenir la versió de l'API.
    response = session.get(
        "http://127.0.0.1:8080/JSON/core/view/version/",
        headers={"X-ZAP-API-Key": api_key},
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()

    print("Connexió amb ZAP correcta.")
    print("Versió de ZAP:", data["version"])
    print()

    print("Creant una nova sessió a ZAP...")

    new_session_response = session.get(
        "http://127.0.0.1:8080/JSON/core/action/newSession/",
        headers={"X-ZAP-API-Key": api_key},
        params={"name": "", "overwrite": "false"},
        timeout=30,
    )

    new_session_response.raise_for_status()
    new_session_data = new_session_response.json()

    if new_session_data.get("Result") != "OK":
        raise RuntimeError("No s'ha pogut crear una nova sessió a ZAP.")

    print("Nova sessió de ZAP creada correctament.")
    print()

    #Configurem el ZAP (amb la seva adreça i port) com a proxy per a les peticions HTTP i HTTPS.
    proxies = {
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080"
    }

    #Definim els endpoints de la nostra API que volem examinar amb ZAP.
    endpoints = [
        "/health",
        "/health/missing-header"
    ]

    incidencies = []  # Llista per guardar incidències trobades durant l'escaneig.

    for endpoint in endpoints:
        url = target_url + endpoint
        print("Escanejant:", url)

        try:
            lab_response = session.get(
                url,
                proxies=proxies,
                timeout=10,
                allow_redirects=False
            )
        except requests.RequestException as e:
            #Si entrem aqui és que no hem pogut realitzar la petició a l'endpoint, per tant ho guardem com a incidència
            incidencies.append({
                "url": url,
                "tipus": "Error petició",
                "detalls": str(e)
            })

            print(f"AVÍS: No s'ha pogut completar la petició a {url}.")
            print("Continuem amb el següent endpoint.")
            print()

            continue

        if lab_response.status_code != 200:
            incidencies.append({
                "url": url,
                "tipus": "Resposta inesperada",
                "detalls": f"Estat HTTP: {lab_response.status_code}"
            })

            print(
                f"AVÍS: {url} ha retornat HTTP "
                f"{lab_response.status_code}; esperàvem HTTP 200."
            )

        else:
            print("El laboratori ha retornat HTTP 200 correctament.")

        print()

    max_wait_seconds = 120
    deadline = time.monotonic() + max_wait_seconds

    print("Esperant que ZAP acabi l'anàlisi passiva...")

    while True:
        remaining_seconds = deadline - time.monotonic()

        if remaining_seconds <= 0:
            raise RuntimeError(
                "S'ha superat el temps màxim d'espera de ZAP. "
                "Anàlisi no completada."
            )

        pending_response = session.get(
            "http://127.0.0.1:8080/JSON/pscan/view/recordsToScan/",
            headers={"X-ZAP-API-Key": api_key},
            timeout=min(10, remaining_seconds),
        )

        pending_response.raise_for_status()
        pending_records = int(pending_response.json()["recordsToScan"])

        print("Registres pendents d'analitzar:", pending_records)

        remaining_seconds = deadline - time.monotonic()

        if remaining_seconds <= 0:
            raise RuntimeError(
                "S'ha superat el temps màxim d'espera de ZAP. "
                "Anàlisi no completada."
            )

        if pending_records == 0:
            break

        time.sleep(min(1, remaining_seconds))

    print("ZAP ha acabat de processar el trànsit.")
    print()
           

    #Demana a ZAP les alertes generades per l'escaneig de la nostra API i les guarda en alertes_response.
    alerts_response = session.get(
        "http://127.0.0.1:8080/JSON/core/view/alerts/", #Direcció de l'API de ZAP per recuperar les alertes.
        headers={"X-ZAP-API-Key": api_key}, #Clau d'API per identificar-me amb ZAP.
        params={"baseurl": target_url}, #Determinem de quin URL volem les alertes(la nostre API)
        timeout=10,
    )

    alerts_response.raise_for_status() #Comprovem si la petició ha estat correcta(si no es correcte, peta)

    info_obtinguta = alerts_response.json() #Extraiem el JSON de la resposta 
    alerts = info_obtinguta["alerts"] #Extraiem només la llista d'alertes del JSON

    print("Alertes recuperades:", len(alerts))

    for alert in alerts:
        print()
        print("Alerta:", alert["alert"])
        print("URL:", alert["url"])
        print("Risc:", alert["risk"])
        print("Identificador:", alert["pluginId"])

#_file_ és el fitxer actual, .parent és la carpeta on està el fitxer, .resolve() és per obtenir la ruta absoluta.Funciona pq hem fet un import de Path.
project_dir = Path(__file__).resolve().parent
#project_dir guarda la ruta absoluta de la carpeta on està el fitxer check_zap.py ( la ruta del projecte)

# escrivim la direcció de la carpeta on guardem els resultats
output_dir = project_dir / "evidencies" / "resultats consulta-zap"
output_dir.mkdir(parents=True, exist_ok=True) #si falta la carpeta la crea, sino no fa res

# Busquem el número més alt dels fitxers que ja existeixen.
last_number = 0

for file in output_dir.glob("alertes-zap-*.JSON"):
    number_text = file.stem.removeprefix("alertes-zap-")

    if number_text.isdigit():
        last_number = max(last_number, int(number_text))


next_number = last_number + 1 #sumem 1 pq el nou fitxer tingui el següent número 
output_file = output_dir / f"alertes-zap-{next_number}.JSON"


now = datetime.now()
date_text = now.strftime("%H:%M %d-%m-%Y")#obte data i hora actual i la posa en format Hora:Minuts Dia-Mes-Any


# Creem la data com a primer camp i mantenim les dades de ZAP.
data = {
    "consulta realitzada el dia": date_text,
    "objectiu": target_url,
    "tots els endpoints han respost HTTP 200": len(incidencies) == 0,
    "incidencies": incidencies,
    **alerts_response.json(),
}

if incidencies:
    print(
        f"AVÍS: Execució amb {len(incidencies)} incidències. "
        "Reviseu-les al JSON."
    )

 #convertim el diccionari a JSON amb indentació de 4 espais
json_text = json.dumps(data,ensure_ascii=False, indent=4) #ensure_ascii es pq no peti amb els accents
output_file.write_text(json_text,encoding="utf-8") #Escriu les dades al arxiu, encoding li diu com ha de passar el text a bytes


print()
print("Resposta de ZAP desada a:", output_file)






