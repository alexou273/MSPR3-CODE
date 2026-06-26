# Module Sauvegarde WMS : sauvegarde SQL, export CSV et rotation des sauvegardes.

import subprocess
import os
import csv
import json
import datetime
import shutil
import sys
from dotenv import load_dotenv

# mysql.connector sert pour l'export CSV (le dump SQL passe par mysqldump)
try:
    import mysql.connector
    MYSQL_DISPONIBLE = True
except ImportError:
    MYSQL_DISPONIBLE = False

# On lit le fichier .env
load_dotenv(encoding="utf-8-sig")


def _timestamp():
    """Retourne la date et l'heure actuelles."""
    return datetime.datetime.now().isoformat()


def _horodatage_fichier():
    """Horodatage compact (AAAAMMJJ_HHMMSS) pour les noms de fichiers."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_config():
    """Lit la config depuis le .env. Erreur si une variable obligatoire manque."""
    obligatoires = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_DATABASE"]
    manquantes = [v for v in obligatoires if not os.environ.get(v)]
    if manquantes:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {', '.join(manquantes)}. "
            f"Verifiez votre fichier .env (voir .env.example)."
        )

    return {
        "host": os.environ.get("MYSQL_HOST"),
        "port": int(os.environ.get("MYSQL_PORT", 3306)),
        "user": os.environ.get("MYSQL_USER"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE"),
        "dossier": os.environ.get("DOSSIER_SAUVEGARDES", "sauvegardes"),
        "nb_garder": int(os.environ.get("NB_SAUVEGARDES_GARDER", 7)),
    }


def _sauvegarder_log(data, dossier="logs"):
    """Ecrit le resultat dans un fichier JSON horodate."""
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"sauvegarde_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def _trouver_mysqldump():
    """
    Cherche l'executable mysqldump : d'abord dans le PATH,
    puis dans les emplacements habituels de MySQL sous Windows et Linux.
    """
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
    Sauvegarde complete de la base au format SQL via mysqldump.
    Le fichier est horodate et place dans le dossier de sauvegardes (.env).
    Retourne un dict et un code (0 = OK, 1 = erreur).
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

    # Commande mysqldump (--single-transaction pour ne pas bloquer les tables)
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
        # On redirige la sortie de mysqldump directement dans le fichier .sql
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300)

        if proc.returncode == 0:
            resultat["statut"] = "OK"
            resultat["fichier"] = chemin_sortie
            resultat["taille_octets"] = os.path.getsize(chemin_sortie)
        else:
            # En cas d'erreur on supprime le fichier incomplet
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
    Exporte une table MySQL au format CSV (separateur point-virgule).
    Retourne un dict et un code (0 = OK, 1 = erreur).
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

    if not MYSQL_DISPONIBLE:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysql-connector-python non installe : pip install -r requirements.txt"
        return resultat, 1

    try:
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

        # Noms des colonnes puis toutes les lignes
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

    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def rotation_sauvegardes():
    """
    Garde seulement les N sauvegardes les plus recentes (N depuis le .env).
    Supprime les fichiers .sql et .csv les plus anciens.
    Retourne un dict et un code (0 = OK, 1 = erreur).
    """
    config = _get_config()
    dossier = config["dossier"]
    nb_garder = config["nb_garder"]

    resultat = {"horodatage": _timestamp(), "type": "rotation", "dossier": dossier}

    try:
        # On trie les fichiers du plus ancien au plus recent
        fichiers = sorted(
            [os.path.join(dossier, f) for f in os.listdir(dossier)
             if f.endswith(".sql") or f.endswith(".csv")],
            key=os.path.getmtime
        )

        supprimes = []
        # On supprime les plus anciens tant qu'on depasse le nombre a garder
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


# Permet de lancer le module seul pour le tester
if __name__ == "__main__":
    print("=== Module Sauvegarde WMS ===")

    while True:
        print("\n1. Sauvegarde SQL complete")
        print("2. Export CSV d'une table")
        print("3. Rotation des sauvegardes (nettoyage)")
        print("0. Quitter")

        choix = input("\nChoix : ").strip()

        if choix == "1":
            try:
                res, code = sauvegarde_sql()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log sauvegarde : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "2":
            table = input("Nom de la table : ").strip()
            try:
                res, code = export_csv(table)
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log sauvegarde : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "3":
            try:
                res, code = rotation_sauvegardes()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "0":
            print("Au revoir.")
            sys.exit(0)

        else:
            print("Choix invalide.")
