import subprocess
import os
import csv
import json
import datetime


def _timestamp():
    return datetime.datetime.now().isoformat()


def _horodatage_fichier():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _sauvegarder_log(data, dossier="logs"):
    """Sauvegarde le resultat en JSON horodate dans le dossier logs."""
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"sauvegarde_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def sauvegarde_sql(host, user, password, database, dossier_sortie="sauvegardes"):
    """
    Realise un dump SQL complet de la base de donnees via mysqldump.
    Retourne un dict de resultat et un code de retour (0=OK, 1=erreur).
    """
    resultat = {
        "horodatage": _timestamp(),
        "type": "sauvegarde_sql",
        "base": database,
        "hote": host
    }

    os.makedirs(dossier_sortie, exist_ok=True)
    nom_fichier = f"{database}_{_horodatage_fichier()}.sql"
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier)

    cmd = [
        "mysqldump",
        f"--host={host}",
        f"--user={user}",
        f"--password={password}",
        "--single-transaction",
        "--routines",
        "--triggers",
        database
    ]

    try:
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300)

        if proc.returncode == 0:
            resultat["statut"] = "OK"
            resultat["fichier"] = chemin_sortie
            resultat["taille_octets"] = os.path.getsize(chemin_sortie)
        else:
            if os.path.exists(chemin_sortie):
                os.remove(chemin_sortie)
            resultat["statut"] = "ERREUR"
            resultat["message"] = proc.stderr.strip()

    except FileNotFoundError:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysqldump introuvable - verifier l'installation MySQL"
    except subprocess.TimeoutExpired:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "Timeout depasse lors du dump"
    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def export_csv(host, user, password, database, table, dossier_sortie="sauvegardes"):
    """
    Exporte le contenu d'une table MySQL au format CSV.
    Retourne un dict de resultat et un code de retour (0=OK, 1=erreur).
    """
    resultat = {
        "horodatage": _timestamp(),
        "type": "export_csv",
        "base": database,
        "table": table,
        "hote": host
    }

    os.makedirs(dossier_sortie, exist_ok=True)
    nom_fichier = f"{database}_{table}_{_horodatage_fichier()}.csv"
    chemin_sortie = os.path.join(dossier_sortie, nom_fichier)

    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=host, user=user, password=password,
            database=database, connection_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table}`")
        colonnes = [desc[0] for desc in cursor.description]
        lignes = cursor.fetchall()
        cursor.close()
        conn.close()

        with open(chemin_sortie, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(colonnes)
            writer.writerows(lignes)

        resultat["statut"] = "OK"
        resultat["fichier"] = chemin_sortie
        resultat["nb_lignes"] = len(lignes)
        resultat["colonnes"] = colonnes

    except ImportError:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysql.connector non installe : pip install mysql-connector-python"
    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def rotation_sauvegardes(dossier="sauvegardes", nb_garder=7):
    """
    Supprime les anciennes sauvegardes, conserve les N plus recentes.
    Retourne un dict et un code de retour (0=OK, 1=erreur).
    """
    resultat = {"horodatage": _timestamp(), "type": "rotation", "dossier": dossier}

    try:
        fichiers = sorted(
            [os.path.join(dossier, f) for f in os.listdir(dossier)
             if f.endswith(".sql") or f.endswith(".csv")],
            key=os.path.getmtime
        )
        supprimes = []
        while len(fichiers) > nb_garder:
            f = fichiers.pop(0)
            os.remove(f)
            supprimes.append(os.path.basename(f))

        resultat["statut"] = "OK"
        resultat["fichiers_supprimes"] = supprimes
        resultat["fichiers_conserves"] = len(fichiers)

    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


if __name__ == "__main__":
    import sys

    print("=== Module Sauvegarde WMS ===")
    print("1. Sauvegarde SQL complete")
    print("2. Export CSV d'une table")
    print("3. Rotation des sauvegardes (nettoyage)")

    choix = input("\nChoix : ").strip()

    if choix == "1":
        host = input("Hote MySQL : ").strip()
        user = input("Utilisateur : ").strip()
        password = input("Mot de passe : ").strip()
        database = input("Base de donnees : ").strip()
        res, code = sauvegarde_sql(host, user, password, database)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        chemin = _sauvegarder_log(res)
        print(f"Log sauvegarde : {chemin}")
        sys.exit(code)

    elif choix == "2":
        host = input("Hote MySQL : ").strip()
        user = input("Utilisateur : ").strip()
        password = input("Mot de passe : ").strip()
        database = input("Base de donnees : ").strip()
        table = input("Nom de la table : ").strip()
        res, code = export_csv(host, user, password, database, table)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        chemin = _sauvegarder_log(res)
        print(f"Log sauvegarde : {chemin}")
        sys.exit(code)

    elif choix == "3":
        nb = input("Nombre de sauvegardes a conserver [7] : ").strip()
        nb = int(nb) if nb.isdigit() else 7
        res, code = rotation_sauvegardes(nb_garder=nb)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(code)

    else:
        print("Choix invalide.")
        sys.exit(1)
