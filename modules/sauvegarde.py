# Module Sauvegarde WMS de NTL-SysToolbox.
# Gere les sauvegardes logiques de la base de donnees MySQL du systeme d'entrepot (WMS) :
#   - Dump SQL complet via mysqldump
#   - Export d'une table au format CSV
#   - Rotation des sauvegardes (suppression des plus anciennes)
# Toutes les connexions et les chemins sont configures via le fichier .env.

import subprocess
import os
import csv
import json
import datetime
import shutil
import sys
from dotenv import load_dotenv

# On tente d'importer mysql.connector pour l'export CSV.
# Le dump SQL (mysqldump) est un outil externe et ne necessite pas cette librairie.
try:
    import mysql.connector
    MYSQL_DISPONIBLE = True
except ImportError:
    MYSQL_DISPONIBLE = False

# Charge les variables depuis le fichier .env.
# encoding="utf-8-sig" gere le BOM que Windows ajoute dans certains editeurs de texte.
load_dotenv(encoding="utf-8-sig")


def _timestamp():
    """Retourne la date et l'heure actuelles au format ISO 8601."""
    return datetime.datetime.now().isoformat()


def _horodatage_fichier():
    """
    Retourne un horodatage compact au format AAAAMMJJ_HHMMSS.
    Utilise dans les noms de fichiers de sauvegarde pour un tri chronologique naturel.
    """
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_config():
    """
    Lit toute la configuration necessaire depuis les variables d'environnement du .env.
    Les trois variables suivantes sont obligatoires et declenchent une erreur si absentes :
      - MYSQL_HOST     : adresse du serveur MySQL
      - MYSQL_USER     : utilisateur MySQL
      - MYSQL_DATABASE : nom de la base a sauvegarder
    Les autres variables ont des valeurs par defaut utilisables en test ou en dev.
    """
    obligatoires = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_DATABASE"]
    # Liste toutes les variables manquantes en une seule passe pour un message d'erreur complet
    manquantes = [v for v in obligatoires if not os.environ.get(v)]
    if manquantes:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {', '.join(manquantes)}. "
            f"Verifiez votre fichier .env (voir .env.example)."
        )

    return {
        "host":      os.environ.get("MYSQL_HOST"),
        "port":      int(os.environ.get("MYSQL_PORT", 3306)),        # Port MySQL par defaut : 3306
        "user":      os.environ.get("MYSQL_USER"),
        "password":  os.environ.get("MYSQL_PASSWORD", ""),           # Mot de passe vide autorise
        "database":  os.environ.get("MYSQL_DATABASE"),
        "dossier":   os.environ.get("DOSSIER_SAUVEGARDES", "sauvegardes"),  # Dossier de sortie des fichiers
        "nb_garder": int(os.environ.get("NB_SAUVEGARDES_GARDER", 7)),       # Nombre de sauvegardes a conserver
    }


def _sauvegarder_log(data, dossier="logs"):
    """Ecrit le resultat d'une operation de sauvegarde dans un fichier JSON horodate."""
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"sauvegarde_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def _trouver_mysqldump():
    """
    Localise l'executable mysqldump sur le systeme.
    Cherche d'abord dans le PATH (Linux / Windows avec MySQL dans le PATH),
    puis dans les emplacements d'installation typiques de MySQL sur Windows.
    Retourne le chemin complet ou None si introuvable.
    """
    # shutil.which cherche l'executable dans le PATH systeme (equivalent du 'which' Unix)
    chemin = shutil.which("mysqldump")
    if chemin:
        return chemin

    # Emplacements par defaut de mysqldump sur Windows et Linux
    candidats = [
        r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        "/usr/bin/mysqldump",
        "/usr/local/bin/mysqldump",
    ]
    for c in candidats:
        if os.path.exists(c):
            return c

    # mysqldump est introuvable : l'appelant devra gerer ce cas
    return None


def sauvegarde_sql():
    """
    Realise un dump SQL complet de la base de donnees via l'outil mysqldump.
    Le fichier genere contient la structure et les donnees de toute la base,
    horodate et place dans le dossier defini par DOSSIER_SAUVEGARDES dans le .env.
    Options mysqldump utilisees :
      --single-transaction : evite de verrouiller les tables pendant le dump (InnoDB)
      --routines           : inclut les procedures stockees
      --triggers           : inclut les declencheurs
    Retourne un dictionnaire de resultat et un code : 0 = OK, 1 = erreur.
    """
    config = _get_config()

    # Resultat de base, enrichi au fil de l'execution
    resultat = {
        "horodatage": _timestamp(),
        "type": "sauvegarde_sql",
        "base": config["database"],
        "hote": config["host"]
    }

    # Cree le dossier de sauvegarde s'il n'existe pas encore
    os.makedirs(config["dossier"], exist_ok=True)
    nom_fichier = f"{config['database']}_{_horodatage_fichier()}.sql"
    chemin_sortie = os.path.join(config["dossier"], nom_fichier)

    # Verifie que mysqldump est disponible avant de lancer quoi que ce soit
    mysqldump = _trouver_mysqldump()
    if not mysqldump:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysqldump introuvable - verifier l'installation MySQL"
        return resultat, 1

    # Construction de la commande mysqldump avec les parametres de connexion
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
        # La sortie standard (le dump SQL) est redirigee directement vers le fichier
        # La sortie d'erreur est capturee separement pour pouvoir l'afficher en cas d'echec
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300)

        if proc.returncode == 0:
            resultat["statut"] = "OK"
            resultat["fichier"] = chemin_sortie
            resultat["taille_octets"] = os.path.getsize(chemin_sortie)
        else:
            # En cas d'echec, on supprime le fichier partiel pour ne pas laisser une sauvegarde corrompue
            if os.path.exists(chemin_sortie):
                os.remove(chemin_sortie)
            resultat["statut"] = "ERREUR"
            resultat["message"] = proc.stderr.strip()

    except subprocess.TimeoutExpired:
        # Le dump a depasse 5 minutes : base trop grosse ou serveur non repondant
        resultat["statut"] = "ERREUR"
        resultat["message"] = "Timeout depasse lors du dump"
    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def export_csv(table):
    """
    Exporte le contenu complet d'une table MySQL au format CSV (separateur point-virgule).
    Utilise mysql.connector pour lire les donnees ligne par ligne et les ecrire dans un fichier.
    Le fichier est horodate et place dans le dossier de sauvegardes.
    Retourne un dictionnaire de resultat et un code : 0 = OK, 1 = erreur.
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

    # L'export CSV necessite mysql.connector pour lire les donnees via SQL
    if not MYSQL_DISPONIBLE:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysql-connector-python non installe : pip install -r requirements.txt"
        return resultat, 1

    try:
        # Connexion avec timeout de 10 secondes
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            connection_timeout=10
        )
        cursor = conn.cursor()

        # Backticks autour du nom de table pour gerer les noms avec des caracteres speciaux
        cursor.execute(f"SELECT * FROM `{table}`")

        # cursor.description contient les metadonnees des colonnes (nom, type, etc.)
        colonnes = [desc[0] for desc in cursor.description]
        lignes = cursor.fetchall()

        cursor.close()
        conn.close()

        # Ecriture du CSV avec point-virgule comme separateur (standard europeen)
        with open(chemin_sortie, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(colonnes)   # Ligne d'en-tete avec les noms de colonnes
            writer.writerows(lignes)    # Toutes les lignes de donnees

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
    Nettoie le dossier de sauvegardes en ne conservant que les N fichiers les plus recents.
    N est defini par la variable NB_SAUVEGARDES_GARDER dans le .env (defaut : 7).
    Les fichiers sont tries par date de modification, les plus anciens sont supprimes en premier.
    Seuls les fichiers .sql et .csv sont pris en compte (les logs ne sont pas touches).
    Retourne un dictionnaire de resultat et un code : 0 = OK, 1 = erreur.
    """
    config = _get_config()
    dossier = config["dossier"]
    nb_garder = config["nb_garder"]

    resultat = {"horodatage": _timestamp(), "type": "rotation", "dossier": dossier}

    try:
        # Liste et trie les fichiers de sauvegarde du plus ancien au plus recent
        fichiers = sorted(
            [os.path.join(dossier, f) for f in os.listdir(dossier)
             if f.endswith(".sql") or f.endswith(".csv")],
            key=os.path.getmtime  # Tri par date de derniere modification
        )

        supprimes = []
        # Supprime les fichiers en debut de liste (les plus anciens) jusqu'a atteindre nb_garder
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


# Ce bloc s'execute uniquement quand le script est lance directement (python sauvegarde.py),
# pas quand il est importe par main.py. Utile pour tester le module de facon isolee.
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
