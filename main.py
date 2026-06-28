# Fichier principal de NTL-SysToolbox : menu CLI qui appelle les trois modules.

import sys
import json
import os
import datetime
from dotenv import load_dotenv

# On force l'UTF-8 sur la console Windows pour bien afficher les accents
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Permet d'importer les fichiers du dossier modules/
sys.path.insert(0, os.path.dirname(__file__))

# On lit le fichier .env
load_dotenv(encoding="utf-8-sig")


def _sauvegarder_log(data, dossier=None):
    """
    Ecrit le resultat d'une action dans un fichier JSON horodate.
    Le dossier est lu depuis le .env (variable DOSSIER_LOGS, defaut : logs).
    """
    dossier = dossier or os.environ.get("DOSSIER_LOGS", "logs")
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"log_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def menu_diagnostic():
    """Sous-menu du module Diagnostic (AD/DNS, MySQL, systeme local)."""
    from modules.diagnostic import check_ad_dns, test_mysql, diag_systeme

    while True:
        print("\n--- MODULE DIAGNOSTIC ---")
        print("1. Verifier AD/DNS sur DC01 (depuis .env)")
        print("2. Verifier AD/DNS sur DC02 (depuis .env)")
        print("3. Verifier AD/DNS sur une IP personnalisee")
        print("4. Tester la connexion MySQL (depuis .env)")
        print("5. Diagnostic systeme local")
        print("0. Retour")

        choix = input("\nVotre choix : ").strip()

        if choix in ("1", "2", "3"):
            try:
                # Options 1 et 2 : on prend l'IP dans le .env, option 3 : saisie a la main
                if choix == "1":
                    dc_ip = os.environ.get("DC1_IP")
                    if not dc_ip:
                        print("Erreur : DC1_IP manquant dans .env")
                        continue
                elif choix == "2":
                    dc_ip = os.environ.get("DC2_IP")
                    if not dc_ip:
                        print("Erreur : DC2_IP manquant dans .env")
                        continue
                else:
                    dc_ip = input("IP du controleur de domaine : ").strip()
                res, code = check_ad_dns(dc_ip)
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except Exception as e:
                print(f"Erreur : {e}")

        elif choix == "4":
            try:
                res, code = test_mysql()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "5":
            res, code = diag_systeme()
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "0":
            break
        else:
            print("Choix invalide.")


def menu_sauvegarde():
    """Sous-menu du module Sauvegarde WMS (dump SQL, export CSV, rotation)."""
    while True:
        print("\n--- MODULE SAUVEGARDE WMS ---")
        print("1. Sauvegarde SQL complete")
        print("2. Export CSV d'une table")
        print("3. Rotation des sauvegardes")
        print("0. Retour")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            from modules.sauvegarde import sauvegarde_sql
            try:
                res, code = sauvegarde_sql()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "2":
            from modules.sauvegarde import export_csv
            table = input("Nom de la table : ").strip()
            try:
                res, code = export_csv(table)
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "3":
            from modules.sauvegarde import rotation_sauvegardes
            try:
                res, code = rotation_sauvegardes()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "0":
            break
        else:
            print("Choix invalide.")


def menu_audit():
    """
    Sous-menu du module Audit d'obsolescence.
    Scan reseau, liste des versions EOL et generation du rapport HTML.
    """
    while True:
        print("\n--- MODULE AUDIT D'OBSOLESCENCE ---")
        print("1. Scanner le reseau (detection des hotes)")
        print("2. Lister les versions d'un OS et leurs dates EOL")
        print("3. Verifier le statut EOL d'une version specifique")
        print("4. Analyser un CSV d'inventaire (rapport JSON + HTML)")
        print("0. Retour")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            from modules.network_scan import scan_network, export_json as export_scan
            reseau = input("Plage reseau a scanner (ex: 192.168.10.0/24) : ").strip()
            hosts = scan_network(reseau)
            if hosts:
                print(f"\n{len(hosts)} hote(s) detecte(s) :")
                for h in hosts:
                    print(f"  - {h['ip']} | OS : {h['os']}")
                export_scan(hosts)
            else:
                print("Aucun hote detecte ou nmap non disponible.")

        elif choix == "2":
            from modules.list_versions import list_versions, export_versions
            os_name = input("Nom de l'OS (ex: ubuntu, debian, windows-server) : ").strip().lower()
            versions = list_versions(os_name)
            if versions:
                print(f"\nVersions connues pour {os_name} :")
                for v in versions:
                    print(f"  - {v['cycle']} | EOL : {v['eol']}")
                export_versions(os_name, versions)
            else:
                print("OS non reconnu ou erreur API.")

        elif choix == "3":
            from modules.eol_check import check_eol
            from datetime import datetime, timedelta
            os_name = input("Nom de l'OS (ex: ubuntu, debian) : ").strip().lower()
            version = input("Version (ex: 20.04, 11) : ").strip()
            info = check_eol(os_name, version)
            if info:
                eol_date = info.get("eol")
                # eol peut etre une date, ou True/False quand l'API ne donne pas de date
                if eol_date and eol_date is not True:
                    try:
                        eol_dt = datetime.strptime(eol_date, "%Y-%m-%d")
                        now = datetime.now()
                        if eol_dt < now:
                            print(f"Statut : OBSOLETE (EOL : {eol_date})")
                        elif eol_dt <= now + timedelta(days=180):
                            print(f"Statut : BIENTOT EOL (EOL : {eol_date})")
                        else:
                            print(f"Statut : SUPPORTE (EOL : {eol_date})")
                    except ValueError:
                        print(f"Statut : SUPPORTE (EOL : {eol_date})")
                else:
                    print("Statut : SUPPORTE (pas de date EOL definie)")
            else:
                print("Version non trouvee dans l'API endoflife.date.")

        elif choix == "4":
            from modules.eol_check import load_csv, check_eol, export_json, export_html
            chemin = input("Chemin du fichier CSV (ex: data/systems.csv) : ").strip()
            if os.path.exists(chemin):
                systems = load_csv(chemin)
                results = []
                for item in systems:
                    info = check_eol(item["os"], item["version"])
                    results.append({
                        "os": item["os"],
                        "version": item["version"],
                        "eol_info": info
                    })
                export_json(results)
                export_html(results)
                print(f"Rapport genere dans results/ ({len(results)} entree(s))")
            else:
                print(f"Fichier introuvable : {chemin}")

        elif choix == "0":
            break
        else:
            print("Choix invalide.")


def menu_principal():
    """Menu principal : choix du module."""
    print("=" * 50)
    print("   NTL-SysToolbox - NordTransit Logistics")
    print("   Outil de diagnostic et supervision v1.1")
    print("=" * 50)

    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1. Module Diagnostic")
        print("2. Module Sauvegarde WMS")
        print("3. Module Audit d'obsolescence")
        print("0. Quitter")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            menu_diagnostic()
        elif choix == "2":
            menu_sauvegarde()
        elif choix == "3":
            menu_audit()
        elif choix == "0":
            print("\nAu revoir.")
            sys.exit(0)
        else:
            print("Choix invalide.")


# Point d'entree : ce bloc s'execute uniquement quand on lance le fichier directement
# (python main.py), pas quand il est importe comme module.
if __name__ == "__main__":
    menu_principal()
