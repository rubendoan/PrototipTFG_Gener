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

    print("Estat HTTP:", new_session_response.status_code)
    print("Resposta de ZAP:", new_session_response.text)

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
        #"/health/missing-header"
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
            print("URL comprovada:", lab_response.url)
            print("Capçalera X-Content-Type-Options:",lab_response.headers.get("X-Content-Type-Options", "NO PRESENT"))
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


    #sistema que analitza si ZAP ha acabat l'anàlisis o no 
    max_wait_seconds = 120
    deadline = time.monotonic() + max_wait_seconds

    # Exigim tres comprovacions consecutives sense activitat.
    idle_checks = 0
    required_idle_checks = 3

    print("Esperant que ZAP acabi l'anàlisi passiva...")

    while True:
        remaining_seconds = deadline - time.monotonic()

        if remaining_seconds <= 0:
            raise RuntimeError(
                "S'ha superat el temps màxim d'espera de ZAP. "
                "Anàlisi no completada."
            )

        # Consultem els registres pendents d'analitzar.
        pending_response = session.get(
            "http://127.0.0.1:8080/JSON/pscan/view/recordsToScan/",
            headers={"X-ZAP-API-Key": api_key},
            timeout=min(10, remaining_seconds),
        )
        pending_response.raise_for_status()
        pending_records = int(
            pending_response.json()["recordsToScan"]
        )

        remaining_seconds = deadline - time.monotonic()

        if remaining_seconds <= 0:
            raise RuntimeError(
                "S'ha superat el temps màxim d'espera de ZAP. "
                "Anàlisi no completada."
            )

        # Consultem les tasques que ZAP està executant.
        tasks_response = session.get(
            "http://127.0.0.1:8080/JSON/pscan/view/currentTasks/",
            headers={"X-ZAP-API-Key": api_key},
            timeout=min(10, remaining_seconds),
        )
        tasks_response.raise_for_status()
        current_tasks = tasks_response.json()["currentTasks"]

        remaining_seconds = deadline - time.monotonic()

        if remaining_seconds <= 0:
            raise RuntimeError(
                "S'ha superat el temps màxim d'espera de ZAP. "
                "Anàlisi no completada."
            )

        print(
            f"Registres pendents: {pending_records} | "
            f"Tasques en execució: {len(current_tasks)}"
        )

        if pending_records == 0 and len(current_tasks) == 0:
            idle_checks += 1
            print(
                f"Comprovacions sense activitat: "
                f"{idle_checks}/{required_idle_checks}"
            )
        else:
            # Si torna a haver-hi activitat, reiniciem el comptador.
            idle_checks = 0

        if idle_checks >= required_idle_checks:
            break

        time.sleep(min(1, remaining_seconds))

    print("ZAP s'ha mantingut sense activitat durant les comprovacions.")
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
now = datetime.now()

execution_id = now.strftime("%d-%m-%Y_%H-%M-%S")  # Generem un identificador únic per a aquesta execució basat en la data i hora actual.


# escrivim la direcció de la carpeta on guardem els resultats
output_dir = project_dir / "evidencies" / "resultats consulta-zap" / execution_id
output_dir.mkdir(parents=True, exist_ok=False) #si falta la carpeta la crea, sino no fa res

execution_file = output_dir / "resposta_procesada.json" #crea un arxiu resultats.json dins la carpeta de resultats
alerts_file = output_dir / "resposta_ZAP.json" #crea un arxiu alerts.json dins la carpeta de resultats

date_text = now.strftime("%H:%M %d-%m-%Y")#obte data i hora actual i la posa en format Hora:Minuts Dia-Mes-Any


# Creem la data com a primer camp i mantenim les dades de ZAP.
data = {
    "consulta realitzada el dia": date_text,
    "objectiu": target_url,
    "tots els endpoints han respost HTTP 200": len(incidencies) == 0,
    "incidencies": incidencies,
}

if incidencies:
    print(
        f"AVÍS: Execució amb {len(incidencies)} incidències. "
        "Reviseu-les al JSON."
    )

 #convertim el diccionari a JSON amb indentació de 4 espais
json_text = json.dumps(data,ensure_ascii=False, indent=4) #ensure_ascii es pq no peti amb els accents
execution_file.write_text(json_text,encoding="utf-8") #Escriu les dades al arxiu, encoding li diu com ha de passar el text a bytes

alerts_file.write_bytes(alerts_response.content)

print()
print("Dades de l'execució desades a :", execution_file)
print("Resposta de ZAP desada :", alerts_file)




