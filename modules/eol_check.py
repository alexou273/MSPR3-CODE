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

    # Recherche de la version dans la réponse de l'API
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
    Exporte les résultats de l'audit dans un fichier JSON dans le dossier /results.
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
    Génère un rapport HTML avec un code couleur selon le statut.
    Ce rapport est lisible par un humain et répond aux exigences du cahier des charges.
    """

    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/{filename}"

    # Compteurs pour le petit résumé en haut du rapport
    nb_supporte = 0
    nb_bientot = 0
    nb_obsolete = 0
    nb_inconnu = 0

    # On construit les lignes du tableau au fur et à mesure
    lignes = ""
    for item in data:
        os_name = item["os"]
        version = item["version"]
        info = item["eol_info"]

        statut = "Inconnu"
        couleur = "inconnu"
        date_eol = "-"

        if info is not None:
            date_eol = info.get("eol")

            if date_eol:
                eol = datetime.strptime(date_eol, "%Y-%m-%d")
                maintenant = datetime.now()
                bientot = maintenant + timedelta(days=180)  # 6 mois

                if eol < maintenant:
                    statut = "Obsolète"
                    couleur = "obsolete"
                elif eol <= bientot:
                    statut = "Bientôt EOL"
                    couleur = "bientot"
                else:
                    statut = "Supporté"
                    couleur = "supporte"
            else:
                date_eol = "-"

        # On met à jour le bon compteur
        if couleur == "supporte":
            nb_supporte += 1
        elif couleur == "bientot":
            nb_bientot += 1
        elif couleur == "obsolete":
            nb_obsolete += 1
        else:
            nb_inconnu += 1

        lignes += f"""
            <tr class="{couleur}">
                <td>{os_name}</td>
                <td>{version}</td>
                <td>{statut}</td>
                <td>{date_eol}</td>
            </tr>"""

    date_jour = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport d'obsolescence</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; color: #333; }}
        h1 {{ color: #1a237e; }}
        .resume {{ margin: 15px 0 25px 0; }}
        .resume span {{ margin-right: 20px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #1a237e; color: white; }}
        .supporte {{ background-color: #c8f7c5; }}   /* Vert */
        .bientot  {{ background-color: #ffe5b4; }}   /* Orange */
        .obsolete {{ background-color: #f7c5c5; }}   /* Rouge */
        .inconnu  {{ background-color: #e0e0e0; }}   /* Gris */
        .pied {{ margin-top: 25px; color: #888; font-size: 13px; }}
    </style>
</head>
<body>
    <h1>Rapport d'obsolescence - NTL-SysToolbox</h1>
    <p>Généré le {date_jour} (source : endoflife.date)</p>

    <div class="resume">
        <span style="color:#27ae60;">Supportés : {nb_supporte}</span>
        <span style="color:#e67e22;">Bientôt EOL : {nb_bientot}</span>
        <span style="color:#c0392b;">Obsolètes : {nb_obsolete}</span>
        <span style="color:#777;">Inconnus : {nb_inconnu}</span>
    </div>

    <table>
        <tr>
            <th>Système</th>
            <th>Version</th>
            <th>Statut</th>
            <th>Date EOL</th>
        </tr>{lignes}
    </table>

    <p class="pied">NTL-SysToolbox v1.2</p>
</body>
</html>"""

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
