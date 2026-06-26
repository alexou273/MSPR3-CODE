import subprocess
import json
import os
from datetime import datetime

# ------------------ FONCTION DE SCAN RÉSEAU ------------------
def scan_network(network):
    """
    Scanne un réseau en utilisant nmap et retourne une liste des hôtes détectés.
    Le scan tente d’identifier les machines actives et d’estimer leur système d’exploitation.
    """
    
    print(f"Début du scan réseau sur : {network}")

    # -O : détection du système d'exploitation (fait aussi un scan de ports,
    # nécessaire pour que nmap puisse deviner l'OS)
    command = ["nmap", "-O", network]

    try:
        # Exécute la commande nmap et capture la sortie
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        print("Avez-vous installé nmap sur votre machine ?")
        print("Erreur lors de l'exécution de nmap :", e)
        return []

    hosts = []
    current_ip = None
    current_os = "Inconnu"

    # Analyse ligne par ligne de la sortie nmap
    for line in result.splitlines():
        line = line.strip()

        # Détection de l'adresse IP
        if line.startswith("Nmap scan report for"):
            # nmap affiche soit "...for 192.168.1.5", soit "...for nom (192.168.1.5)"
            # on enlève les parenthèses pour ne garder que l'IP
            current_ip = line.split()[-1].strip("()")
            current_os = "Inconnu"

        # Détection du système d'exploitation
        if "OS details:" in line:
            current_os = line.replace("OS details:", "").strip()
        # Si nmap n'est pas sûr, il donne plusieurs propositions : on garde la première
        elif "Aggressive OS guesses:" in line:
            propositions = line.replace("Aggressive OS guesses:", "").strip()
            current_os = propositions.split(",")[0].strip()

        # Une ligne vide indique la fin d’un bloc d’informations sur un hôte
        if line == "" and current_ip:
            hosts.append({"ip": current_ip, "os": current_os})
            current_ip = None

    return hosts
# ------------------ EXPORT DES RÉSULTATS EN JSON ------------------
def export_json(data, filename="network_scan.json"):
    """
    Sauvegarde les résultats du scan dans un fichier JSON dans le dossier 'results'.
    """
    
    os.makedirs("results", exist_ok=True)

    output = {
        "timestamp": datetime.now().isoformat(),
        "hosts": data
    }

    filepath = f"results/{filename}"

    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Résultats du scan exportés dans : {filepath}")
# ------------------ PROGRAMME PRINCIPAL ------------------
if __name__ == "__main__":
    # Demande à l'utilisateur la plage réseau à scanner
    network = input("Entrez le réseau à scanner (exemple : 192.168.10.0/24) : ")
    # Exécution du scan
    hosts = scan_network(network)
    # Affichage des résultats
    print("\nHôtes détectés :")
    for h in hosts:
        print(f"- {h['ip']} | OS détecté : {h['os']}")
    # Export des résultats
    export_json(hosts)
