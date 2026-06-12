# Module Diagnostic de NTL-SysToolbox.
# Verifie la disponibilite des services critiques du siege NTL :
#   - Controleurs de domaine AD/DNS (DC01 et DC02)
#   - Base de donnees MySQL du WMS
#   - Etat systeme local (OS, uptime, CPU, RAM, disques)
# Toutes les connexions sont configurees via le fichier .env (pas de credentials en dur).

import socket
import platform
import json
import datetime
import os
import sys
from dotenv import load_dotenv

# On tente d'importer psutil (mesures CPU/RAM/disques).
# Si la librairie n'est pas installee, on desactive la fonctionnalite
# sans faire planter le script au demarrage.
try:
    import psutil
    PSUTIL_DISPONIBLE = True
except ImportError:
    PSUTIL_DISPONIBLE = False

# Meme principe pour mysql.connector : optionnel au chargement,
# le script signale l'absence de la dependance uniquement quand
# l'utilisateur tente de tester la connexion MySQL.
try:
    import mysql.connector
    MYSQL_DISPONIBLE = True
except ImportError:
    MYSQL_DISPONIBLE = False

# Charge les variables depuis le fichier .env.
# encoding="utf-8-sig" gere le BOM (marqueur invisible) que Windows ajoute
# quand on cree un fichier texte avec Notepad ou PowerShell Set-Content.
load_dotenv(encoding="utf-8-sig")


def _timestamp():
    """Retourne la date et l'heure actuelles au format ISO 8601 (ex: 2026-06-12T14:30:00)."""
    return datetime.datetime.now().isoformat()


def _sauvegarder_log(data, dossier=None):
    """
    Ecrit le resultat d'un diagnostic dans un fichier JSON horodate.
    Le dossier de destination est lu depuis DOSSIER_LOGS dans le .env (defaut : 'logs').
    """
    dossier = dossier or os.environ.get("DOSSIER_LOGS", "logs")
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"diag_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def _get_mysql_config():
    """
    Lit la configuration MySQL depuis les variables d'environnement du .env.
    Leve une EnvironmentError explicite si MYSQL_HOST, MYSQL_USER ou MYSQL_DATABASE
    sont absents, pour eviter un message d'erreur cryptique de mysql.connector.
    """
    obligatoires = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_DATABASE"]
    # Identifie toutes les variables manquantes en une seule passe
    manquantes = [v for v in obligatoires if not os.environ.get(v)]
    if manquantes:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {', '.join(manquantes)}. "
            f"Verifiez votre fichier .env (voir .env.example)."
        )
    return {
        "host":     os.environ.get("MYSQL_HOST"),
        "port":     int(os.environ.get("MYSQL_PORT", 3306)),  # 3306 est le port MySQL par defaut
        "user":     os.environ.get("MYSQL_USER"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),     # Mot de passe vide autorise
        "database": os.environ.get("MYSQL_DATABASE"),
    }


def _get_dc_config():
    """
    Lit les adresses IP des deux controleurs de domaine depuis le .env.
    DC1_IP = controleur principal (DC01), DC2_IP = controleur secondaire (DC02).
    Leve une EnvironmentError si l'une des deux variables est absente.
    """
    obligatoires = ["DC1_IP", "DC2_IP"]
    manquantes = [v for v in obligatoires if not os.environ.get(v)]
    if manquantes:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {', '.join(manquantes)}. "
            f"Verifiez votre fichier .env (voir .env.example)."
        )
    return {
        "dc1": os.environ.get("DC1_IP"),
        "dc2": os.environ.get("DC2_IP"),
    }


def check_ad_dns(dc_ip, timeout=3):
    """
    Verifie la disponibilite des services Active Directory et DNS sur un controleur de domaine.
    Teste trois ports caracteristiques d'un DC Windows :
      - Port 53  : DNS (resolution de noms)
      - Port 389 : LDAP (annuaire Active Directory)
      - Port 445 : SMB (partages de fichiers et GPO)
    Retourne un dictionnaire de resultats et un code : 0 = tous les services OK, 1 = au moins un probleme.
    """
    resultats = {
        "horodatage": _timestamp(),
        "hote": dc_ip,
        "services": {}
    }

    # Dictionnaire port_name -> numero_de_port pour faciliter l'iteration
    ports = {
        "DNS (53)":  53,
        "LDAP (389)": 389,
        "SMB (445)":  445,
    }

    for nom, port in ports.items():
        try:
            # On ouvre une connexion TCP et on mesure si elle aboutit
            # connect_ex renvoie 0 si la connexion reussit, un code d'erreur sinon
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            code = sock.connect_ex((dc_ip, port))
            sock.close()
            resultats["services"][nom] = "OK" if code == 0 else "INJOIGNABLE"
        except Exception as e:
            resultats["services"][nom] = f"ERREUR: {e}"

    # Resolution DNS inverse : on tente de retrouver le nom d'hote a partir de l'IP
    # Utile pour verifier que le DNS local repond correctement
    try:
        socket.setdefaulttimeout(timeout)
        nom_hote = socket.gethostbyaddr(dc_ip)[0]
        resultats["nom_hote_resolu"] = nom_hote
    except Exception:
        resultats["nom_hote_resolu"] = "echec"

    # Le statut global est OK uniquement si les trois ports repondent
    tous_ok = all(v == "OK" for v in resultats["services"].values())
    resultats["statut_global"] = "OK" if tous_ok else "DEGRADE"

    return resultats, 0 if tous_ok else 1


def test_mysql():
    """
    Teste la connexion a la base de donnees MySQL du WMS.
    Les credentials (host, user, password, database) sont lus depuis le .env.
    En cas de succes, remonte la version MySQL et l'uptime du serveur.
    Retourne un dictionnaire et un code : 0 = connexion OK, 1 = echec.
    """
    # Verifie que la dependance est disponible avant de tenter quoi que ce soit
    if not MYSQL_DISPONIBLE:
        return {
            "horodatage": _timestamp(),
            "statut": "ERREUR",
            "message": "mysql-connector-python non installe : pip install -r requirements.txt"
        }, 1

    config = _get_mysql_config()

    # Initialise le resultat avec les informations de connexion (sans le mot de passe)
    resultat = {
        "horodatage": _timestamp(),
        "hote": config["host"],
        "port": config["port"],
        "utilisateur": config["user"]
    }

    try:
        # Connexion avec un timeout de 5 secondes pour ne pas bloquer longtemps
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            connection_timeout=5
        )
        cursor = conn.cursor()

        # Recupere la version du serveur MySQL
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]

        # Recupere l'uptime du serveur en secondes depuis son dernier demarrage
        cursor.execute("SHOW STATUS LIKE 'Uptime'")
        uptime_row = cursor.fetchone()
        uptime_sec = int(uptime_row[1]) if uptime_row else 0

        cursor.close()
        conn.close()

        resultat["statut"] = "OK"
        resultat["version_mysql"] = version
        resultat["uptime_serveur_sec"] = uptime_sec

    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def diag_systeme():
    """
    Collecte un etat complet de la machine locale : OS, uptime, CPU, RAM, disques.
    Fonctionne sous Windows Server et Ubuntu grace a la librairie psutil (cross-platform).
    Retourne un dictionnaire et un code : 0 = OK, 1 = psutil absent, 2 = ressources sous pression.
    Le seuil d'avertissement est fixe a 90% d'utilisation CPU ou RAM.
    """
    # Informations de base disponibles sans psutil, via le module standard 'platform'
    info = {
        "horodatage": _timestamp(),
        "os": platform.platform(),
        "version_os": platform.version(),
        "architecture": platform.architecture()[0],
        "hostname": platform.node(),
    }

    # Sans psutil, on ne peut pas mesurer CPU/RAM/disques : on signale l'absence et on s'arrete
    if not PSUTIL_DISPONIBLE:
        info["erreur"] = "psutil non disponible : pip install -r requirements.txt"
        return info, 1

    # Calcul de l'uptime : difference entre maintenant et le dernier demarrage systeme
    try:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        duree = datetime.datetime.now() - boot
        heures = int(duree.total_seconds() // 3600)
        minutes = int((duree.total_seconds() % 3600) // 60)
        info["uptime"] = f"{heures}h{minutes:02d}m"
        info["dernier_demarrage"] = boot.isoformat()
    except Exception as e:
        info["uptime"] = f"erreur: {e}"

    # Informations CPU : nombre de coeurs et utilisation instantanee (mesure sur 1 seconde)
    try:
        info["cpu"] = {
            "coeurs_physiques": psutil.cpu_count(logical=False),
            "coeurs_logiques": psutil.cpu_count(logical=True),
            "utilisation_pct": psutil.cpu_percent(interval=1)
        }
    except Exception as e:
        info["cpu"] = {"erreur": str(e)}

    # Informations RAM : total, disponible et pourcentage d'utilisation
    try:
        mem = psutil.virtual_memory()
        info["ram"] = {
            "total_go": round(mem.total / (1024 ** 3), 2),
            "disponible_go": round(mem.available / (1024 ** 3), 2),
            "utilisation_pct": mem.percent
        }
    except Exception as e:
        info["ram"] = {"erreur": str(e)}

    # Informations disques : on parcourt toutes les partitions montees
    try:
        disques = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disques.append({
                    "point_montage": part.mountpoint,
                    "systeme_fichiers": part.fstype,
                    "total_go": round(usage.total / (1024 ** 3), 2),
                    "utilise_go": round(usage.used / (1024 ** 3), 2),
                    "libre_go": round(usage.free / (1024 ** 3), 2),
                    "utilisation_pct": usage.percent
                })
            except PermissionError:
                # Certaines partitions systeme (ex: lecteur CD vide) refusent l'acces, on les ignore
                continue
        info["disques"] = disques
    except Exception as e:
        info["disques"] = {"erreur": str(e)}

    # Statut global : AVERTISSEMENT si CPU ou RAM depasse 90%
    cpu_pct = info.get("cpu", {}).get("utilisation_pct", 0)
    ram_pct = info.get("ram", {}).get("utilisation_pct", 0)
    info["statut_global"] = "OK" if (cpu_pct < 90 and ram_pct < 90) else "AVERTISSEMENT"

    # Code 0 = tout va bien, code 2 = avertissement ressources (pas une erreur bloquante)
    return info, 0 if info["statut_global"] == "OK" else 2


# Ce bloc s'execute uniquement quand le script est lance directement (python diagnostic.py),
# pas quand il est importe par main.py. Utile pour tester le module de facon isolee.
if __name__ == "__main__":
    print("=== Module Diagnostic NTL ===")

    while True:
        print("\n1. Verifier AD/DNS sur DC01")
        print("2. Verifier AD/DNS sur DC02")
        print("3. Tester la connexion MySQL (WMS-DB)")
        print("4. Diagnostic systeme local (OS/CPU/RAM/Disques)")
        print("0. Quitter")

        choix = input("\nChoix : ").strip()

        if choix in ("1", "2"):
            try:
                dc_config = _get_dc_config()
                dc_ip = dc_config["dc1"] if choix == "1" else dc_config["dc2"]
                res, code = check_ad_dns(dc_ip)
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log sauvegarde : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "3":
            try:
                res, code = test_mysql()
                print(json.dumps(res, indent=2, ensure_ascii=False))
                print(f"Log sauvegarde : {_sauvegarder_log(res)}")
                print(f"Code de retour : {code}")
            except EnvironmentError as e:
                print(f"Erreur de configuration : {e}")

        elif choix == "4":
            res, code = diag_systeme()
            print(json.dumps(res, indent=2, ensure_ascii=False))
            print(f"Log sauvegarde : {_sauvegarder_log(res)}")
            print(f"Code de retour : {code}")

        elif choix == "0":
            print("Au revoir.")
            sys.exit(0)

        else:
            print("Choix invalide.")
