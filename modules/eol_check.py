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
    Generates an HTML report with color-coded statuses.
    This makes the audit results human-readable and 'exploitable',
    as required by the cahier des charges.
    """

    if not os.path.exists("results"):
        os.makedirs("results")

    filepath = f"results/{filename}"

    # --- Premiere passe : calcul des statuts et compteurs ---
    rows_data = []
    counts = {"supported": 0, "soon": 0, "obsolete": 0, "unknown": 0}

    for item in data:
        os_name = item["os"]
        version  = item["version"]
        info     = item["eol_info"]

        status   = "Inconnu"
        css      = "unknown"
        eol_date = "-"

        if info is not None:
            eol_date = info.get("eol", None)

            if eol_date:
                eol_dt         = datetime.strptime(eol_date, "%Y-%m-%d")
                now            = datetime.now()
                soon_threshold = now + timedelta(days=180)  # 6 mois

                if eol_dt < now:
                    status = "Obsolète"
                    css    = "obsolete"
                elif now <= eol_dt <= soon_threshold:
                    status = "Bientôt EOL"
                    css    = "soon"
                else:
                    status = "Supporté"
                    css    = "supported"

        counts[css] += 1
        rows_data.append((css, os_name, version, status, eol_date or "-"))

    # --- Construction des lignes du tableau ---
    badge_class = {
        "supported": "badge-supported",
        "soon":      "badge-soon",
        "obsolete":  "badge-obsolete",
        "unknown":   "badge-unknown",
    }

    rows_html = ""
    for css, os_name, version, status, eol_date in rows_data:
        rows_html += f"""
                <tr class="{css}">
                    <td><span class="os-name">{os_name}</span></td>
                    <td><span class="version">{version}</span></td>
                    <td><span class="badge {badge_class[css]}">{status}</span></td>
                    <td class="eol-date">{eol_date}</td>
                </tr>"""

    # --- Generation du HTML complet ---
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport d'obsolescence — NTL-SysToolbox</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            color: #2c3e50;
            min-height: 100vh;
        }}

        /* ---- En-tete ---- */
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            color: white;
            padding: 32px 40px;
        }}
        .header h1   {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 4px; }}
        .header .sub {{ font-size: 0.95rem; opacity: 0.75; }}
        .header .meta {{ font-size: 0.82rem; opacity: 0.55; margin-top: 10px; }}

        /* ---- Contenu central ---- */
        .content {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 32px 24px;
        }}

        /* ---- Cartes de resume ---- */
        .cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08);
            text-align: center;
        }}
        .card .count  {{ font-size: 2.4rem; font-weight: 800; line-height: 1; }}
        .card .label  {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: .06em;
            color: #7f8c8d;
            margin-top: 6px;
        }}
        .card.supported .count {{ color: #27ae60; }}
        .card.soon      .count {{ color: #e67e22; }}
        .card.obsolete  .count {{ color: #e74c3c; }}
        .card.unknown   .count {{ color: #95a5a6; }}

        /* ---- Tableau ---- */
        .table-wrapper {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08);
            overflow: hidden;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        thead th {{
            background: #f8f9fa;
            color: #5f6368;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: .06em;
            padding: 14px 20px;
            text-align: left;
            border-bottom: 2px solid #e9ecef;
        }}
        tbody tr {{
            border-bottom: 1px solid #f1f3f4;
            transition: background .12s;
        }}
        tbody tr:last-child {{ border-bottom: none; }}
        tbody tr:hover {{ background: #fafbfc; }}
        tbody td {{ padding: 14px 20px; font-size: 0.92rem; }}

        /* Barre coloree a gauche de chaque ligne selon le statut */
        tr.supported td:first-child {{ border-left: 4px solid #27ae60; }}
        tr.soon      td:first-child {{ border-left: 4px solid #e67e22; }}
        tr.obsolete  td:first-child {{ border-left: 4px solid #e74c3c; }}
        tr.unknown   td:first-child {{ border-left: 4px solid #bdc3c7; }}

        /* ---- Badges de statut ---- */
        .badge {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: .03em;
        }}
        .badge-supported {{ background: #d5f5e3; color: #1e8449; }}
        .badge-soon      {{ background: #fdebd0; color: #a04000; }}
        .badge-obsolete  {{ background: #fadbd8; color: #922b21; }}
        .badge-unknown   {{ background: #eaecee; color: #626567; }}

        /* ---- Cellules specifiques ---- */
        .os-name {{ font-weight: 600; }}
        .version {{
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            background: #f1f3f4;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .eol-date {{ font-size: 0.88rem; color: #5f6368; }}

        /* ---- Pied de page ---- */
        .footer {{
            text-align: center;
            color: #95a5a6;
            font-size: 0.8rem;
            padding: 24px 0 16px;
        }}

        @media (max-width: 640px) {{
            .cards   {{ grid-template-columns: repeat(2, 1fr); }}
            .header  {{ padding: 24px 20px; }}
            .content {{ padding: 20px 16px; }}
        }}
    </style>
</head>
<body>

    <div class="header">
        <h1>Rapport d'obsolescence</h1>
        <div class="sub">NTL-SysToolbox — Audit des systèmes d'exploitation</div>
        <div class="meta">Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")} — Source : endoflife.date</div>
    </div>

    <div class="content">

        <div class="cards">
            <div class="card supported">
                <div class="count">{counts["supported"]}</div>
                <div class="label">Supportés</div>
            </div>
            <div class="card soon">
                <div class="count">{counts["soon"]}</div>
                <div class="label">Bientôt EOL</div>
            </div>
            <div class="card obsolete">
                <div class="count">{counts["obsolete"]}</div>
                <div class="label">Obsolètes</div>
            </div>
            <div class="card unknown">
                <div class="count">{counts["unknown"]}</div>
                <div class="label">Inconnus</div>
            </div>
        </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Système</th>
                        <th>Version</th>
                        <th>Statut</th>
                        <th>Date EOL</th>
                    </tr>
                </thead>
                <tbody>{rows_html}
                </tbody>
            </table>
        </div>

    </div>

    <div class="footer">NTL-SysToolbox v1.0</div>

</body>
</html>"""

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
