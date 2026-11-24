import json
import os
import argparse
import time
import signal
import sys
from pathlib import Path

from datetime import datetime

import requests
from dotenv import load_dotenv


# Registrem quan comença el programa i iniciem el cronòmetre.
started_at = datetime.now()
started_monotonic = time.monotonic()

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

# Preparem el registre abans de començar les operacions que poden fallar.
execution_status = "en_curs"
execution_error = None
zap_original_response = None

incidencies = []
#Definim els endpoints de la nostra API que volem examinar amb ZAP.
endpoints = [
    "/health",
    "/health/missing-header"
]
successful_endpoints = 0

max_wait_seconds = 120
exit_code = 1

try:
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
                successful_endpoints += 1
                print("El laboratori ha retornat HTTP 200 correctament.")

            print()


        #sistema que analitza si ZAP ha acabat l'anàlisis o no 
        deadline = time.monotonic() + max_wait_seconds

        # Exigim tres comprovacions consecutives sense activitat.
        idle_checks = 0
        required_idle_checks = 3

        print("Esperant que ZAP acabi l'anàlisi passiva...")

        while True:
            remaining_seconds = deadline - time.monotonic()

            if remaining_seconds <= 0:
                raise TimeoutError(
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
                raise TimeoutError(
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
                raise TimeoutError(
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
        zap_original_response = alerts_response.content

        print("Alertes recuperades:", len(alerts))

        for alert in alerts:
            print()
            print("Alerta:", alert["alert"])
            print("URL:", alert["url"])
            print("Risc:", alert["risk"])
            print("Identificador:", alert["pluginId"])
    # Arribem aquí si hem recuperat els resultats sense un error fatal.
    if incidencies:
        execution_status = "incompleta"
        exit_code = 1
    else:
        execution_status = "completada"
        exit_code = 0
except KeyboardInterrupt:
    # Ignorem nous Ctrl+C mentre desem el registre i tanquem.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    execution_status = "interrompuda"
    execution_error = "Execució interrompuda per l'usuari amb Ctrl+C."
    exit_code = 130

except TimeoutError as e:
    execution_status = "incompleta"
    execution_error = str(e)
    exit_code = 1

except requests.RequestException as e:
    execution_status = "fallida"
    execution_error = f"Error de comunicació amb ZAP: {e}"
    exit_code = 1

except (RuntimeError, ValueError, KeyError) as e:
    execution_status = "fallida"
    execution_error = f"{type(e).__name__}: {e}"
    exit_code = 1

finally:
    # Registrem el final, tant si ha funcionat com si ha fallat.
    finished_at = datetime.now()
    duration_seconds = round(time.monotonic() - started_monotonic, 2)

    #_file_ és el fitxer actual, .parent és la carpeta on està el fitxer, .resolve() és per obtenir la ruta absoluta.Funciona pq hem fet un import de Path.
    project_dir = Path(__file__).resolve().parent
    #project_dir guarda la ruta absoluta de la carpeta on està el fitxer check_zap.py ( la ruta del projecte)

    # Identifiquem l'execució amb la data i hora d'inici.
    execution_id = started_at.strftime("%d-%m-%Y_%H-%M-%S")

    # escrivim la direcció de la carpeta on guardem els resultats
    output_dir = project_dir / "evidencies" / "resultats consulta-zap" / execution_id

    execution_file = output_dir / "resposta_procesada.json" #crea un arxiu resultats.json dins la carpeta de resultats
    alerts_file = output_dir / "resposta_ZAP.json" #crea un arxiu alerts.json dins la carpeta de resultats


    # Creem la data com a primer camp i mantenim les dades de ZAP.
    data = {
        "id_execucio": execution_id,
        "inici": started_at.strftime("%d-%m-%Y %H:%M:%S"),
        "fi": finished_at.strftime("%d-%m-%Y %H:%M:%S"),
        "durada_segons": duration_seconds,
        "objectiu": target_url,
        "estat": execution_status,
        "error": execution_error,
        "configuracio": {
            "endpoints": endpoints,
            "temps_maxim_espera_segons": max_wait_seconds,
        },
        "endpoints_amb_http_200": successful_endpoints,
        "tots els endpoints han respost HTTP 200": (
            bool(endpoints)
            and successful_endpoints == len(endpoints)
        ),
        "incidencies": incidencies,
        "resposta_zap_disponible": zap_original_response is not None,
    }

    print()
    print("Estat de l'execució:", execution_status)

    if execution_error is not None:
        print("ERROR:", execution_error)

    if incidencies:
        print(f"AVÍS: S'han registrat {len(incidencies)} incidències.")

    try:
        output_dir.mkdir(parents=True, exist_ok=False)# Crea la carpeta; si ja existeix, genera un error.

        execution_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

        # Només guardem la resposta de ZAP si l'hem recuperada.
        if zap_original_response is not None:
            alerts_file.write_bytes(zap_original_response)

    except OSError as e:
        print(f"ERROR: No s'han pogut desar tots els resultats: {e}")
        exit_code = 1

    else:
        print("Dades de l'execució desades a:", execution_file)

        if zap_original_response is not None:
            print("Resposta de ZAP desada a:", alerts_file)
        else:
            print("No s'ha recuperat cap resposta d'alertes de ZAP.")

sys.exit(exit_code)



