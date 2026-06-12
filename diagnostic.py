import socket
import platform
import json
import datetime
import os
import shutil
from dotenv import load_dotenv

# Charge les variables depuis le fichier .env s'il existe
load_dotenv()

try:
    import psutil
    PSUTIL_DISPONIBLE = True
except ImportError:
    PSUTIL_DISPONIBLE = False


def _timestamp():
    return datetime.datetime.now().isoformat()


def _sauvegarder_log(data, dossier=None):
    dossier = dossier or os.environ.get("DOSSIER_LOGS", "logs")
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier, f"diag_{ts}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return chemin


def _get_mysql_config():
    """
    Recupere la configuration MySQL depuis les variables d'environnement.
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
        "host":     os.environ.get("MYSQL_HOST"),
        "port":     int(os.environ.get("MYSQL_PORT", 3306)),
        "user":     os.environ.get("MYSQL_USER"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE"),
    }


def _get_dc_config():
    """
    Recupere les IPs des controleurs de domaine depuis les variables d'environnement.
    Leve une EnvironmentError si DC1_IP ou DC2_IP est absent.
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
    Verifie la disponibilite des services AD/DNS sur un controleur de domaine.
    Teste les ports 53 (DNS), 389 (LDAP) et 445 (SMB).
    Retourne un dict de resultats et un code de retour (0=OK, 1=probleme).
    """
    resultats = {
        "horodatage": _timestamp(),
        "hote": dc_ip,
        "services": {}
    }

    ports = {
        "DNS (53)": 53,
        "LDAP (389)": 389,
        "SMB (445)": 445,
    }

    for nom, port in ports.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            code = sock.connect_ex((dc_ip, port))
            sock.close()
            resultats["services"][nom] = "OK" if code == 0 else "INJOIGNABLE"
        except Exception as e:
            resultats["services"][nom] = f"ERREUR: {e}"

    try:
        socket.setdefaulttimeout(timeout)
        nom_hote = socket.gethostbyaddr(dc_ip)[0]
        resultats["nom_hote_resolu"] = nom_hote
    except Exception:
        resultats["nom_hote_resolu"] = "echec"

    tous_ok = all(v == "OK" for v in resultats["services"].values())
    resultats["statut_global"] = "OK" if tous_ok else "DEGRADE"

    return resultats, 0 if tous_ok else 1


def test_mysql():
    """
    Teste la connexion a un serveur MySQL.
    Les credentials sont lus depuis les variables d'environnement (fichier .env).
    Retourne un dict et un code de retour (0=OK, 1=erreur).
    """
    config = _get_mysql_config()

    resultat = {
        "horodatage": _timestamp(),
        "hote": config["host"],
        "port": config["port"],
        "utilisateur": config["user"]
    }

    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            connection_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("SHOW STATUS LIKE 'Uptime'")
        uptime_row = cursor.fetchone()
        uptime_sec = int(uptime_row[1]) if uptime_row else 0
        cursor.close()
        conn.close()

        resultat["statut"] = "OK"
        resultat["version_mysql"] = version
        resultat["uptime_serveur_sec"] = uptime_sec

    except ImportError:
        resultat["statut"] = "ERREUR"
        resultat["message"] = "mysql.connector non installe : pip install mysql-connector-python"
    except Exception as e:
        resultat["statut"] = "ERREUR"
        resultat["message"] = str(e)

    return resultat, 0 if resultat["statut"] == "OK" else 1


def diag_systeme():
    """
    Collecte les informations systeme locales : OS, uptime, CPU, RAM, Disques.
    Fonctionne sous Windows Server et Ubuntu.
    Retourne un dict et un code (0=OK, 1=erreur, 2=avertissement ressources).
    """
    info = {
        "horodatage": _timestamp(),
        "os": platform.platform(),
        "version_os": platform.version(),
        "architecture": platform.architecture()[0],
        "hostname": platform.node(),
    }

    if not PSUTIL_DISPONIBLE:
        info["erreur"] = "psutil non disponible : pip install psutil"
        return info, 1

    try:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        duree = datetime.datetime.now() - boot
        heures = int(duree.total_seconds() // 3600)
        minutes = int((duree.total_seconds() % 3600) // 60)
        info["uptime"] = f"{heures}h{minutes:02d}m"
        info["dernier_demarrage"] = boot.isoformat()
    except Exception as e:
        info["uptime"] = f"erreur: {e}"

    try:
        info["cpu"] = {
            "coeurs_physiques": psutil.cpu_count(logical=False),
            "coeurs_logiques": psutil.cpu_count(logical=True),
            "utilisation_pct": psutil.cpu_percent(interval=1)
        }
    except Exception as e:
        info["cpu"] = {"erreur": str(e)}

    try:
        mem = psutil.virtual_memory()
        info["ram"] = {
            "total_go": round(mem.total / (1024 ** 3), 2),
            "disponible_go": round(mem.available / (1024 ** 3), 2),
            "utilisation_pct": mem.percent
        }
    except Exception as e:
        info["ram"] = {"erreur": str(e)}

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
                continue
        info["disques"] = disques
    except Exception as e:
        info["disques"] = {"erreur": str(e)}

    cpu_pct = info.get("cpu", {}).get("utilisation_pct", 0)
    ram_pct = info.get("ram", {}).get("utilisation_pct", 0)
    info["statut_global"] = "OK" if (cpu_pct < 90 and ram_pct < 90) else "AVERTISSEMENT"

    return info, 0 if info["statut_global"] == "OK" else 2


if __name__ == "__main__":
    import sys

    print("=== Module Diagnostic NTL ===")
    print("1. Verifier AD/DNS sur DC01")
    print("2. Verifier AD/DNS sur DC02")
    print("3. Tester la connexion MySQL (WMS-DB)")
    print("4. Diagnostic systeme local (OS/CPU/RAM/Disques)")
    choix = input("\nChoix : ").strip()

    if choix in ("1", "2"):
        dc_config = _get_dc_config()
        dc_ip = dc_config["dc1"] if choix == "1" else dc_config["dc2"]
        res, code = check_ad_dns(dc_ip)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"Log sauvegarde : {_sauvegarder_log(res)}")
        sys.exit(code)

    elif choix == "3":
        res, code = test_mysql()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"Log sauvegarde : {_sauvegarder_log(res)}")
        sys.exit(code)

    elif choix == "4":
        res, code = diag_systeme()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"Log sauvegarde : {_sauvegarder_log(res)}")
        sys.exit(code)

    else:
        print("Choix invalide.")
        sys.exit(1)
