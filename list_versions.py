import requests
import json
import os
from datetime import datetime

# ------------------ API FUNCTION ------------------
def list_versions(os_name):
    """
    Lists all known versions (cycles) AND their EOL dates
    endoflife.date API.
    """
    os_name = os_name.lower()
    url = f"https://endoflife.date/api/{os_name}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print("Erreur API :", e)
        return None
    # Extract version + EOL
    versions = []
    for entry in data:
        versions.append({
            "cycle": entry.get("cycle"),
            "eol": entry.get("eol")
        })
    return versions
# ------------------ EXPORT JSON ------------------
def export_versions(os_name, versions):
    """
    Exports the list of versions + EOL dates to a JSON file inside /results.
    """
    output = {
        "timestamp": datetime.now().isoformat(),
        "os": os_name,
        "versions": versions
    }
    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/versions_{os_name}.json"
    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Export effectué : {filepath}")
# ------------------ MAIN PROGRAM ------------------
if __name__ == "__main__":
    os_name = input("Entrez le nom de l'OS : ").strip().lower()
    versions = list_versions(os_name)
    if versions:
        print(f"\nVersions connues pour {os_name} :\n")
        for v in versions:
            print(f"- Version : {v['cycle']} | EOL : {v['eol']}")

        export_versions(os_name, versions)
    else:
        print("Aucune version trouvée ou OS non supporté.")
