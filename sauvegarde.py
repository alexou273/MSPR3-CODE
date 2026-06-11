import subprocess
import os
import json
import datetime


def _timestamp():
    return datetime.datetime.now().isoformat()


def _horodatage_fichier():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


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


if __name__ == "__main__":
    import sys

    print("=== Module Sauvegarde WMS ===")
    host = input("Hote MySQL : ").strip()
    user = input("Utilisateur : ").strip()
    password = input("Mot de passe : ").strip()
    database = input("Base de donnees : ").strip()

    res, code = sauvegarde_sql(host, user, password, database)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(code)
