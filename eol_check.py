import requests
import json
import csv
from datetime import date, datetime

# ------------------ FONCTION API ------------------
def check_eol(os_name, version):
    try:
        url = f"https://endoflife.date/api/{os_name}.json"
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print("Erreur API :", e)
        return None

    for entry in data:
        if entry.get("cycle") == version:
            return entry

    return None

# ------------------ READ the file system.csv ------------------
def load_csv(path):
    systems = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            systems.append({
                "os": row["os"],
                "version": row["version"]
            })
    return systems

# ------------------ EXPORT JSON ------------------
def export_json(data, filename="eol_results.json"):
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": data
    }

    # Path to the export file
    filepath = f"results/{filename}"

    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Résultat exporté dans : {filepath}")
# ------------------ MAIN ------------------
if __name__ == "__main__":
    systems = load_csv("data\systems.csv")
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
