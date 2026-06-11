import socket
import json
import datetime


def _timestamp():
    return datetime.datetime.now().isoformat()


def check_ad_dns(dc_ip, timeout=3):
    """
    Verifie la disponibilite des services AD/DNS sur un controleur de domaine.
    Teste les ports 53 (DNS) et 389 (LDAP).
    """
    resultats = {
        "horodatage": _timestamp(),
        "hote": dc_ip,
        "services": {}
    }

    ports = {
        "DNS (53)": 53,
        "LDAP (389)": 389,
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

    tous_ok = all(v == "OK" for v in resultats["services"].values())
    resultats["statut_global"] = "OK" if tous_ok else "DEGRADE"

    return resultats, 0 if tous_ok else 1


if __name__ == "__main__":
    dc_ip = input("Adresse IP du controleur de domaine : ").strip()
    res, code = check_ad_dns(dc_ip)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print(f"Code de retour : {code}")
