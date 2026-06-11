import sys


def menu_principal():
    print("=" * 50)
    print("   NTL-SysToolbox - NordTransit Logistics")
    print("   Outil de diagnostic et supervision v0.1")
    print("=" * 50)

    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1. Module Diagnostic")
        print("2. Module Sauvegarde WMS")
        print("3. Module Audit d'obsolescence")
        print("0. Quitter")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            print("\n[Module Diagnostic - en cours de developpement]")
        elif choix == "2":
            print("\n[Module Sauvegarde WMS - en cours de developpement]")
        elif choix == "3":
            print("\n[Module Audit d'obsolescence - en cours de developpement]")
        elif choix == "0":
            print("\nAu revoir.")
            sys.exit(0)
        else:
            print("Choix invalide, veuillez reessayer.")


if __name__ == "__main__":
    menu_principal()
