import subprocess
import os
import csv
import json
import datetime
import shutil
from dotenv import load_dotenv

# Charge les variables depuis le fichier .env s'il existe
load_dotenv()


def _timestamp():
    return datetime.datetime.now().isoformat()


def _horodatage_fichier():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_config():
    """
    Recupere la configuration depuis les variables d'environnement.
    Leve une EnvironmentError si une variable obligatoire est absente.
    """
    obligatoires = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_DATABASE"]
    manquantes = [v for v in obligatoires if not os.environ.get(v)]
    if manquantes:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {', '.join(manquantes)}. "
            f"Verifiez votre fichier .env (voir .env.example)."
        )

    return {
        "host":      os.environ.get("MYSQL_HOST"),
        "port":      int(os.environ.get("MYSQL_PORT", 3306)),
        "user":      os.environ.get("MYSQL_USER"),
        "password":  os.environ.get("MYSQL_PASSWORD", ""),
        "database":  os.environ.get("MYSQL_DATABASE"),
        "dossier":   os.environ.get("DOSSIER_SAUVEGARDES", "sauvegardes"),
        "nb_garder": int(os.environ.get("NB_SAUVEGARDES_GARDER", 7)),
    }


def _sauvegarder_log(data, dossier="logs"):
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"sauvegarde_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def _trouver_mysqldump():
    """Cherche mysqldump dans le PATH puis dans les emplacements MySQL courants."""
    chemin = shutil.which("mysqldump")
    if chemin:
        return chemin
    candidats = [
        r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        "/usr/bin/mysqldump",
        "/usr/local/bin/mysqldump",
    ]
    for c in candidats:
        if os.path.exists(c):
            return c
    return None


def sauvegarde_sql():
    """
    Realise un dump SQL complet de la base de donnees via mysqldump.
    Les credentials sont lus depuis les variables d'environnement (fichier .env).
    Retourne un dict de resultat et un code de retour (0=OK, 1=erreur).
    """
    config = _get_config()

    resultat = {
        "horodatage": _timestamp(),
        "type": "sauvegarde_sql",
        "base": config["database"],
        "hote": config["host"]
    }

    os.makedirs(config["dossier"], exist_ok=True)
    nom_fichier = f"{config['database']}_{_horodatage_fichier()}.sql"
    chemin_sortie = os.path.join(config["dossier"], nom_fichier)

    mysqldump = _trouver_mysqldump()
    if not mysqldump:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysqldump introuvable - verifier l'installation MySQL"
        return resultat, 1

    cmd = [
        mysqldump,
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--user={config['user']}",
        f"--password={config['password']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        config["database"]
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

    except subprocess.TimeoutExpired:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "Timeout depasse lors du dump"
    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def export_csv(table):
    """
    Exporte le contenu d'une table MySQL au format CSV.
    Les credentials sont lus depuis les variables d'environnement (fichier .env).
    Retourne un dict de resultat et un code de retour (0=OK, 1=erreur).
    """
    config = _get_config()

    resultat = {
        "horodatage": _timestamp(),
        "type": "export_csv",
        "base": config["database"],
        "table": table,
        "hote": config["host"]
    }

    os.makedirs(config["dossier"], exist_ok=True)
    nom_fichier = f"{config['database']}_{table}_{_horodatage_fichier()}.csv"
    chemin_sortie = os.path.join(config["dossier"], nom_fichier)

    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            connection_timeout=10
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


def rotation_sauvegardes():
    """
    Supprime les anciennes sauvegardes, conserve les N plus recentes.
    N est defini par la variable d'environnement NB_SAUVEGARDES_GARDER.
    """
    config = _get_config()
    dossier = config["dossier"]
    nb_garder = config["nb_garder"]

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
        res, code = sauvegarde_sql()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        chemin = _sauvegarder_log(res)
        print(f"Log sauvegarde : {chemin}")
        sys.exit(code)

    elif choix == "2":
        table = input("Nom de la table : ").strip()
        res, code = export_csv(table)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        chemin = _sauvegarder_log(res)
        print(f"Log sauvegarde : {chemin}")
        sys.exit(code)

    elif choix == "3":
        res, code = rotation_sauvegardes()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(code)

    else:
        print("Choix invalide.")
        sys.exit(1)
