import requests
import json
import csv
import os
from datetime import datetime, timedelta

# ------------------ FONCTION API ------------------
def check_eol(os_name, version):
    """
    Vérifie si une version d'un OS est encore supportée en utilisant l'API endoflife.date.
    Retourne l'entrée complète si trouvée, sinon None.
    """
    try:
        url = f"https://endoflife.date/api/{os_name}.json"
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print("Erreur API :", e)
        return None
    
    # Recherche de la version dans la réponse de l’API
    for entry in data:
        if entry.get("cycle") == version:
            return entry

    return None
# ------------------ LECTURE DU FICHIER systems.csv ------------------
def load_csv(path):
    """
    Charge le fichier systems.csv et retourne une liste de couples OS / version.
    """
    systems = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            systems.append({
                "os": row["os"],
                "version": row["version"]
            })
    return systems
# ------------------ EXPORT DES RÉSULTATS EN JSON ------------------
def export_json(data, filename="eol_results.json"):
    """
    Exporte les résultats de l’audit dans un fichier JSON dans le dossier /results.
    """
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": data
    }

    # Création du dossier results si nécessaire
    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/{filename}"
    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Résultat exporté dans : {filepath}")


# ------------------ EXPORT DES RÉSULTATS EN HTML ------------------
def export_html(data, filename="eol_report.html"):
    """
    Génère un rapport HTML simple avec un code couleur selon le statut.
    Ce rapport est lisible par un humain et répond aux exigences du cahier des charges.
    """
    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/{filename}"
    # En-tête HTML + styles
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport d'obsolescence</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .supported {{ background-color: #c8f7c5; }}   /* Vert */
            .soon {{ background-color: #ffe5b4; }}        /* Orange */
            .obsolete {{ background-color: #f7d7c5; }}     /* Rouge */
            .unknown {{ background-color: #e0e0e0; }}      /* Gris */
        </style>
    </head>
    <body>
        <h1>Rapport d'obsolescence</h1>
        <p>Généré le : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

        <table>
            <tr>
                <th>OS</th>
                <th>Version</th>
                <th>Statut</th>
                <th>Date EOL</th>
            </tr>
    """
    # Construction des lignes du tableau
    for item in data:
        os_name = item["os"]
        version = item["version"]
        info = item["eol_info"]

        status = "Inconnu"
        css = "unknown"
        eol_date = "-"

        # Si l’API a retourné une entrée valide
        if info is not None:
            eol_date = info.get("eol", None)

            if eol_date:
                eol_dt = datetime.strptime(eol_date, "%Y-%m-%d")
                now = datetime.now()
                soon_threshold = now + timedelta(days=180)  # 6 mois

                # Détermination du statut selon la date EOL
                if eol_dt < now:
                    status = "Obsolete"
                    css = "obsolete"
                elif now <= eol_dt <= soon_threshold:
                    status = "Bientôt EOL"
                    css = "soon"
                else:
                    status = "Supporté"
                    css = "supported"

        html += f"""
            <tr class="{css}">
                <td>{os_name}</td>
                <td>{version}</td>
                <td>{status}</td>
                <td>{eol_date}</td>
            </tr>
        """
    # Fermeture de HTML
    html += """
        </table>
    </body>
    </html>
    """
    # Écriture du fichier HTML
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Rapport HTML généré : {filepath}")
# ------------------ MAIN ------------------
if __name__ == "__main__":
    # Chargement du fichier CSV
    systems = load_csv("data/systems.csv")
    results = []

    # Vérification EOL pour chaque OS/version
    for item in systems:
        os_name = item["os"]
        version = item["version"]

        info = check_eol(os_name, version)

        results.append({
            "os": os_name,
            "version": version,
            "eol_info": info
        })
    # Export JSON + HTML
    export_json(results)
    export_html(results)
