import requests
import json
import csv
import os
from datetime import datetime

# ------------------ API FUNCTION ------------------
def check_eol(os_name, version):
    """
    Checks if an OS version is still supported using the endoflife.date API.
    """
    try:
        url = f"https://endoflife.date/api/{os_name}.json"
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print("API error:", e)
        return None
    
    for entry in data:
        if entry.get("cycle") == version:
            return entry

    return None


# ------------------ READ systems.csv FILE ------------------
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


# ------------------ EXPORT RESULTS TO JSON ------------------
def export_json(data, filename="eol_results.json"):
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": data
    }

    # Create the results folder if it doesn't exist
    if not os.path.exists("results"):
        os.makedirs("results")

    # Path to the export file
    filepath = f"results/{filename}"

    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Export completed: {filepath}")

# ------------------ MAIN PROGRAM ------------------
if __name__ == "__main__":
    # Load OS list from /data/systems.csv
    systems = load_csv("data/systems.csv")
    results = []

    for item in systems:
        os_name = item["os"]
        version = item["version"]

        # Call the API function
        info = check_eol(os_name, version)

        # Append result to the final list
        results.append({
            "os": os_name,
            "version": version,
            "eol_info": info
        })

    # Export final JSON report
    export_json(results)
