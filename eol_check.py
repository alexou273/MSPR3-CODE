import requests
from datetime import date

# ---------------FONCTION------------------
def check_eol(os_name, version):
    """
    Vérifie si une version d'OS est encore supportée via l'API endoflife.date
    """
    try:
        url = f"https://endoflife.date/api/{os_name}.json"
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print("Erreur API :", e)
        return None

    # On cherche la version exacte dans la liste obtenue
    for entry in data:
        if entry.get("cycle") == version:
            return entry

    return None
# ---------------END FONCTION------------------

# __________________VARIABLES______________________
os_name = "debian"
version = "13"         
#__________________END VARIABLE________________________
info = check_eol(os_name, version)

if info is None:
    print(f"Impossible de trouver {os_name} {version} dans l'API.")
else:
    print(f"OS : {os_name} {version}")
    print("Date de fin de support :", info.get("eol"))

    eol_date = info.get("eol") # recuperation de la date selon version

    if eol_date is None:
        print("Statut : encore supporté")
    else:
        today = date.today()
        try:
            eol = date.fromisoformat(eol_date)
            if today > eol:
                print("\033[91mStatut : Obsolete\033[0m") # rouge
            else:
                print("\033[92mStatut : encore supporté\033[0m") # vert
        except:
            print("\033[34mStatut : inconnu\033[0m") # bleu
