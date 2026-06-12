import subprocess # Use for applying nmap ommand line
import json
import os
from datetime import datetime

# ------------------ NETWORK SCAN FUNCTION ------------------
def scan_network(network):
    """
    This scan using nmap and returns a list of detected hosts.
    The scan tries to identify active machines and guess their OS.
    """
    
    print(f"Starting network scan on: {network}")

    # -sn : ping scan (find active hosts)
    # -O  : try to detect the operating system
    command = ["nmap", "-sn", "-O", network]

    try:
        # Run the nmap command and capture the output
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
    except Exception as e:
        print('Do you have nmap on your host ?')
        print("Error running nmap:", e)
        return []

    hosts = []
    current_ip = None
    current_os = "Unknown"

    # Parse nmap output line by line
    for line in result.splitlines():
        line = line.strip()

        # Detect IP address
        if line.startswith("Nmap scan report for"):
            current_ip = line.split()[-1]
            current_os = "Unknown"

        # Detect OS
        if "OS details:" in line:
            current_os = line.replace("OS details:", "").strip()

        # When we reach an empty line, save the host
        if line == "" and current_ip:
            hosts.append({"ip": current_ip, "os": current_os})
            current_ip = None

    return hosts


# ------------------ EXPORT RESULTS TO JSON ------------------
def export_json(data, filename="network_scan.json"):
    """
    Saves scan rin json file inside the 'results' folder.
    """
    
    os.makedirs("results", exist_ok=True)

    output = {
        "timestamp": datetime.now().isoformat(),
        "hosts": data
    }

    filepath = f"results/{filename}"

    with open(filepath, "w") as f:
        json.dump(output, f, indent=4)

    print(f"Scan results exported to: {filepath}")


# ------------------ MAIN PROGRAM ------------------
if __name__ == "__main__":
    # Ask the user for the network to scan
    network = input("Enter your network to scan (example: 192.168.10.0/24): ")

    # Run the scan
    hosts = scan_network(network)

    # Display results
    print("\nDetected hosts:")
    for h in hosts:
        print(f"- {h['ip']} | OS guess: {h['os']}")

    # Export results
    export_json(hosts)