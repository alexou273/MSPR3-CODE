# Point d'entree principal de NTL-SysToolbox.
# Ce fichier orchestre les trois modules via un menu CLI interactif.
# Il ne contient aucune logique metier : il appelle uniquement les fonctions
# definies dans les modules du dossier modules/.

import sys
import json
import os
import datetime
from dotenv import load_dotenv

# Sur Windows, la console utilise par defaut l'encodage cp1252 qui ne sait pas
# afficher certains caracteres (accents, symboles). On force l'UTF-8 pour eviter
# les caracteres garbles dans les resultats affiches.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ajoute le dossier courant au chemin Python pour que les imports
# de type "from modules.xxx import yyy" fonctionnent correctement
# peu importe depuis quel repertoire l'outil est lance.
sys.path.insert(0, os.path.dirname(__file__))

# Charge les variables depuis le fichier .env situe a la racine du projet.
# encoding="utf-8-sig" gere automatiquement le BOM (marqueur invisible) que
# Windows ajoute quand on cree un fichier texte avec Notepad ou PowerShell.
# Sans cela, la premiere variable du .env serait mal lue et toute la config echouerait.
load_dotenv(encoding="utf-8-sig")


def _sauvegarder_log(data, dossier=None):
    """
    Ecrit le resultat d'une action dans un fichier JSON horodate dans le dossier de logs.
    Le dossier est lu depuis la variable d'environnement DOSSIER_LOGS (defaut : 'logs').
    Cela permet de retrouver l'historique de chaque execution pour audit ou supervision.
    """
    # Si aucun dossier n'est precise, on lit la variable d'env ou on utilise 'logs' par defaut
    dossier = dossier or os.environ.get("DOSSIER_LOGS", "logs")
    # Cree le dossier s'il n'existe pas encore
    os.makedirs(dossier, exist_ok=True)
    # Horodatage en format AAAAMMJJ_HHMMSS pour un tri alphabetique = tri chronologique
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"log_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        # ensure_ascii=False conserve les caracteres accentues dans le fichier JSON
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def menu_diagnostic():
    """
    Sous-menu du module Diagnostic.
    Permet de tester les services AD/DNS, la base MySQL et l'etat systeme local.
    Toutes les connexions sont configurees via le fichier .env, sans saisie de credentials.
    """
    # Import local : on charge le module uniquement quand l'utilisateur entre dans ce menu,
    # ce qui evite de planter au demarrage si une dependance (psutil, mysql) est absente.
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
                # Options 1 et 2 : on lit l'IP directement depuis le .env
                # pour ne pas avoir a la ressaisir a chaque fois
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
                    # Option 3 : l'utilisateur saisit une IP arbitraire (test ad hoc)
                    dc_ip = input("IP du controleur de domaine : ").strip()
                res, code = check_ad_dns(dc_ip)
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except Exception as e:
                print(f"Erreur : {e}")

        elif choix == "4":
            try:
                # test_mysql() lit lui-meme les credentials depuis le .env
                res, code = test_mysql()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                # EnvironmentError est levee si MYSQL_HOST, MYSQL_USER ou MYSQL_DATABASE manquent
                print(f"Erreur de configuration : {e}")

        elif choix == "5":
            # diag_systeme() ne necessite aucun parametre : tout est lu localement via psutil
            res, code = diag_systeme()
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "0":
            # Retour au menu principal
            break
        else:
            print("Choix invalide.")


def menu_sauvegarde():
    """
    Sous-menu du module Sauvegarde WMS.
    Permet de sauvegarder la base MySQL, d'exporter une table en CSV
    et de nettoyer les anciennes sauvegardes.
    Toutes les connexions et les chemins sont lus depuis le .env.
    """
    while True:
        print("\n--- MODULE SAUVEGARDE WMS ---")
        print("1. Sauvegarde SQL complete")
        print("2. Export CSV d'une table")
        print("3. Rotation des sauvegardes")
        print("0. Retour")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            # Import local pour ne charger le module qu'a la demande
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
            # Le nom de la table est le seul parametre a fournir :
            # les credentials MySQL viennent du .env
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
                # Le nombre de sauvegardes a conserver est lu depuis NB_SAUVEGARDES_GARDER dans le .env
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
    Permet de scanner le reseau, de consulter l'API endoflife.date
    et de generer un rapport HTML colore sur l'etat de support des OS.
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
            # network_scan.py utilise nmap en sous-processus ; nmap doit etre installe sur le systeme
            from modules.network_scan import scan_network, export_json as export_scan
            reseau = input("Plage reseau a scanner (ex: 192.168.10.0/24) : ").strip()
            hosts = scan_network(reseau)
            if hosts:
                print(f"\n{len(hosts)} hote(s) detecte(s) :")
                for h in hosts:
                    print(f"  - {h['ip']} | OS : {h['os']}")
                # Exporte les resultats du scan dans results/network_scan.json
                export_scan(hosts)
            else:
                print("Aucun hote detecte ou nmap non disponible.")

        elif choix == "2":
            # Interroge l'API publique endoflife.date pour lister toutes les versions d'un OS
            from modules.list_versions import list_versions, export_versions
            os_name = input("Nom de l'OS (ex: ubuntu, debian, windows-server) : ").strip().lower()
            versions = list_versions(os_name)
            if versions:
                print(f"\nVersions connues pour {os_name} :")
                for v in versions:
                    print(f"  - {v['cycle']} | EOL : {v['eol']}")
                # Exporte la liste dans results/versions_<os>.json
                export_versions(os_name, versions)
            else:
                print("OS non reconnu ou erreur API.")

        elif choix == "3":
            # Verifie si une version precise est encore supportee, bientot en fin de vie
            # ou deja obsolete. Le seuil "bientot EOL" est fixe a 6 mois (180 jours).
            from modules.eol_check import check_eol
            from datetime import datetime, timedelta
            os_name = input("Nom de l'OS (ex: ubuntu, debian) : ").strip().lower()
            version = input("Version (ex: 20.04, 11) : ").strip()
            info = check_eol(os_name, version)
            if info:
                eol_date = info.get("eol")
                # eol peut valoir True (supporte indefiniment), False, ou une date au format YYYY-MM-DD
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
                        # L'API renvoie parfois des valeurs non standard (ex: "true") : on les traite comme supportees
                        print(f"Statut : SUPPORTE (EOL : {eol_date})")
                else:
                    print("Statut : SUPPORTE (pas de date EOL definie)")
            else:
                print("Version non trouvee dans l'API endoflife.date.")

        elif choix == "4":
            # Analyse un fichier CSV d'inventaire (colonnes : os, version) ligne par ligne,
            # interroge l'API pour chaque entree et genere deux rapports dans results/ :
            # - eol_results.json : donnees brutes
            # - eol_report.html  : rapport colore lisible (vert/orange/rouge/gris)
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
                        "eol_info": info  # None si l'OS/version n'est pas trouve dans l'API
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
    """
    Menu principal de NTL-SysToolbox.
    Affiche les trois modules disponibles et redirige vers le sous-menu choisi.
    La boucle tourne indefiniment jusqu'a ce que l'utilisateur choisisse de quitter (option 0).
    """
    print("=" * 50)
    print("   NTL-SysToolbox - NordTransit Logistics")
    print("   Outil de diagnostic et supervision v1.0")
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
