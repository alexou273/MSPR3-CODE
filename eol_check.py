import requests
import json
import csv
import os
from datetime import datetime, timedelta

# ------------------ API FUNCTION ------------------
def check_eol(os_name, version):
    """
    Checks if an OS version is still supported using the endoflife.date API.
    Returns the full entry if found, otherwise None.
    """
    try:
        url = f"https://endoflife.date/api/{os_name}.json"
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print("API error:", e)
        return None
    
    # Search for the version in the API response
    for entry in data:
        if entry.get("cycle") == version:
            return entry

    return None
# ------------------ READ systems.csv FILE ------------------
def load_csv(path):
    """
    Loads the systems.csv file and returns a list of OS/version pairs.
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
# ------------------ EXPORT RESULTS TO JSON ------------------
def export_json(data, filename="eol_results.json"):
    """
    Exports the audit results to a JSON file inside /results.
    """
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": data
    }
    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/{filename}"
    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)
    print(f"Résultat exporté dans : {filepath}")

# ------------------ EXPORT RESULTS TO HTML ------------------
def export_html(data, filename="eol_report.html"):
    """
    Generates a simple HTML report with color-coded statuses.
    This makes the audit results human-readable and 'exploitable',
    as required by the cahier des charges.
    """

    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/{filename}"

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

    for item in data:
        os_name = item["os"]
        version = item["version"]
        info = item["eol_info"]

        status = "Inconnu"
        css = "unknown"
        eol_date = "-"

        if info is not None:
            eol_date = info.get("eol", None)

            if eol_date:
                eol_dt = datetime.strptime(eol_date, "%Y-%m-%d")
                now = datetime.now()
                soon_threshold = now + timedelta(days=180)  # 6 mois

                if eol_dt < now:
                    status = "Obsolete"
                    css = "obsolete"
                elif now <= eol_dt <= soon_threshold:
                    status = "Bientot EOL"
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

    html += """
        </table>
    </body>
    </html>
    """

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report generated: {filepath}")
# ------------------ MAIN PROGRAM ------------------
if __name__ == "__main__":
    systems = load_csv("data/systems.csv")
    results = []

    for item in systems:
        os_name = item["os"]
        version = item["version"]

        info = check_eol(os_name, version)

        results.append({
            "os": os_name,
            "version": version,
            "eol_info": info
        })

    export_json(results)
    export_html(results)
