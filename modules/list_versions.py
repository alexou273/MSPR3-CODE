import requests
import json
import os
from datetime import datetime

# ------------------ FONCTION API ------------------
def list_versions(os_name):
    """
    Liste toutes les versions (cycles) connues d’un OS ainsi que leurs dates EOL
    en interrogeant l’API endoflife.date.
    Retourne une liste de dictionnaires {cycle, eol}.
    """
    os_name = os_name.lower()
    url = f"https://endoflife.date/api/{os_name}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Vérifie que la requête s'est bien passée
        data = response.json()
    except Exception as e:
        print("Erreur API :", e)
        return None

    # Extraction des cycles + dates EOL
    versions = []
    for entry in data:
        versions.append({
            "cycle": entry.get("cycle"),
            "eol": entry.get("eol")
        })

    return versions
# ------------------ EXPORT EN JSON ------------------
def export_versions(os_name, versions):
    """
    Exporte la liste des versions + dates EOL dans un fichier JSON
    situé dans le dossier /results.
    """
    output = {
        "timestamp": datetime.now().isoformat(),
        "os": os_name,
        "versions": versions
    }
    # Création du dossier results si nécessaire
    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/versions_{os_name}.json"
    # Écriture du fichier JSON
    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Export effectué : {filepath}")
# ------------------ PROGRAMME PRINCIPAL ------------------
if __name__ == "__main__":
    # Demande du nom de l’OS à l’utilisateur
    os_name = input("Entrez le nom de l'OS : ").strip().lower()
    # Récupération des versions via l’API
    versions = list_versions(os_name)
    # Affichage + export si des versions ont été trouvées
    if versions:
        print(f"\nVersions connues pour {os_name} :\n")
        for v in versions:
            print(f"- Version : {v['cycle']} | EOL : {v['eol']}")

        export_versions(os_name, versions)

    else:
        print("Aucune version trouvée ou OS non supporté.")
