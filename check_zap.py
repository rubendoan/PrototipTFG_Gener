import json
import os
import argparse
from pathlib import Path

from datetime import datetime

import requests
from dotenv import load_dotenv


# Definim els arguments que accepta el programa per terminal.
parser = argparse.ArgumentParser(
    description="Consulta les alertes de ZAP del laboratori local.",
    allow_abbrev=False,
)

parser.add_argument(
    "--target",
    required=True,
    help="URL base del laboratori. Exemple: http://127.0.0.1:8000",
)

# Llegim els arguments introduïts al terminal.
args = parser.parse_args()

# Eliminem la barra final si hi és per acceptar les dues formes de la URL.
target_url = args.target.removesuffix("/")

# Llista explícita dels objectius permesos.
allowed_targets = {
    "http://127.0.0.1:8000",
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

    #Demana a ZAP les alertes generades per l'escaneig de la nostra API i les guarda en alertes_response.
    alerts_response = session.get(
        "http://127.0.0.1:8080/JSON/core/view/alerts/", #Direcció de l'API de ZAP per recuperar les alertes.
        headers={"X-ZAP-API-Key": api_key}, #Clau d'API per identificar-me amb ZAP.
        params={"baseurl": "target_url"}, #Determinem de quin URL volem les alertes(la nostre API)
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
    **alerts_response.json(), #dades recuperades de ZAP (alertes, etc.)
}
 #convertim el diccionari a JSON amb indentació de 4 espais
json_text = json.dumps(data,ensure_ascii=False, indent=4) #ensure_ascii es pq no peti amb els accents
output_file.write_text(json_text,encoding="utf-8") #Escriu les dades al arxiu, encoding li diu com ha de passar el text a bytes


print()
print("Resposta de ZAP desada a:", output_file)






