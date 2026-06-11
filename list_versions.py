import requests
import json
import os
from datetime import datetime

def list_versions(os_name):
    
    os_name = os_name.lower()

    url = f"https://endoflife.date/api/{os_name}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except:
        print("OS non supporté par l’API endoflife.date")
        return

    data = response.json()

    versions = [item["cycle"] for item in data]

    output = {
        "timestamp": datetime.now().isoformat(),
        "os": os_name,
        "versions": versions
    }

    os.makedirs("results", exist_ok=True)
    with open(f"results/versions_{os_name}.json", "w") as f:
        json.dump(output, f, indent=4)

    print(f"Versions connues pour {os_name} :")
    for v in versions:
        print("-", v)

    print("\nExport JSON effectué.")
    
os_name = input("De quel OS voulez-vous lister ses versions ? ")
list_versions(os_name)