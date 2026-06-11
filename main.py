import sys
import json
import os
import datetime

# Ajout du dossier courant au path pour importer les modules
sys.path.insert(0, os.path.dirname(__file__))


def _sauvegarder_log(data, dossier="logs"):
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"log_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def menu_diagnostic():
    while True:
        print("\n--- MODULE DIAGNOSTIC ---")
        print("1. Verifier AD/DNS sur un controleur de domaine")
        print("2. Tester la connexion MySQL")
        print("3. Diagnostic systeme local")
        print("0. Retour")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            from modules.diagnostic import check_ad_dns
            dc_ip = input("IP du controleur de domaine : ").strip()
            res, code = check_ad_dns(dc_ip)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "2":
            from modules.diagnostic import test_mysql
            host = input("Hote MySQL : ").strip()
            user = input("Utilisateur : ").strip()
            password = input("Mot de passe : ").strip()
            db = input("Base de donnees (optionnel) : ").strip()
            res, code = test_mysql(host, 3306, user, password, db)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "3":
            from modules.diagnostic import diag_systeme
            res, code = diag_systeme()
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "0":
            break
        else:
            print("Choix invalide.")


def menu_sauvegarde():
    while True:
        print("\n--- MODULE SAUVEGARDE WMS ---")
        print("1. Sauvegarde SQL complete")
        print("2. Export CSV d'une table")
        print("3. Rotation des sauvegardes")
        print("0. Retour")

        choix = input("\nVotre choix : ").strip()

        if choix in ("1", "2"):
            host = input("Hote MySQL : ").strip()
            user = input("Utilisateur : ").strip()
            password = input("Mot de passe : ").strip()
            database = input("Base de donnees : ").strip()

            if choix == "1":
                from modules.sauvegarde import sauvegarde_sql
                res, code = sauvegarde_sql(host, user, password, database)
            else:
                from modules.sauvegarde import export_csv
                table = input("Nom de la table : ").strip()
                res, code = export_csv(host, user, password, database, table)

            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "3":
            from modules.sauvegarde import rotation_sauvegardes
            nb = input("Nombre de sauvegardes a conserver [7] : ").strip()
            nb = int(nb) if nb.isdigit() else 7
            res, code = rotation_sauvegardes(nb_garder=nb)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Code de retour : {code}")

        elif choix == "0":
            break
        else:
            print("Choix invalide.")


def menu_principal():
    print("=" * 50)
    print("   NTL-SysToolbox - NordTransit Logistics")
    print("   Outil de diagnostic et supervision v0.2")
    print("=" * 50)

    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1. Module Diagnostic")
        print("2. Module Sauvegarde WMS")
        print("3. Module Audit d'obsolescence [bientot disponible]")
        print("0. Quitter")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            menu_diagnostic()
        elif choix == "2":
            menu_sauvegarde()
        elif choix == "3":
            print("\n[Module Audit - integration en cours]")
        elif choix == "0":
            print("\nAu revoir.")
            sys.exit(0)
        else:
            print("Choix invalide.")


if __name__ == "__main__":
    menu_principal()
