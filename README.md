# NTL-SysToolbox

Outil en ligne de commande développé pour **NordTransit Logistics** dans le cadre de la MSPR3.  
Il regroupe trois modules indépendants : diagnostic des services critiques, sauvegarde de la base WMS et audit d'obsolescence des systèmes.

---

## Prérequis

| Composant | Version minimale | Rôle |
|-----------|-----------------|------|
| Python | 3.9+ | Exécution de l'outil |
| MySQL / mysqldump | 8.0+ | Sauvegarde SQL (module Sauvegarde) |
| nmap | toute version récente | Scan réseau (module Audit) |

> **Windows** : installer nmap depuis [nmap.org](https://nmap.org/download.html)  
> **Linux** : `sudo apt install nmap`

---

## Installation

**1. Cloner le dépôt**
```bash
git clone https://github.com/alexou273/MSPR3-CODE.git
cd MSPR3-CODE
```

**2. Installer les dépendances Python**
```bash
pip install -r requirements.txt
```

**3. Créer le fichier de configuration**
```bash
cp .env.example .env
```
Puis éditer `.env` avec les valeurs réelles de l'infrastructure (voir section [Configuration](#configuration)).

---

## Configuration

Toute la configuration se fait dans le fichier `.env` à la racine du projet.  
Ce fichier n'est jamais versionné (voir `.gitignore`) car il contient des informations sensibles.  
Le fichier `.env.example` fourni dans le dépôt sert de modèle.

```ini
# Adresses IP des contrôleurs de domaine
DC1_IP=192.168.10.10
DC2_IP=192.168.10.11

# Connexion à la base MySQL du WMS
MYSQL_HOST=192.168.10.21
MYSQL_PORT=3306
MYSQL_USER=wms_user
MYSQL_PASSWORD=motdepasse
MYSQL_DATABASE=wms

# Dossier de stockage des sauvegardes (créé automatiquement)
DOSSIER_SAUVEGARDES=sauvegardes

# Nombre de sauvegardes à conserver lors de la rotation
NB_SAUVEGARDES_GARDER=7

# Dossier des logs JSON horodatés (créé automatiquement)
DOSSIER_LOGS=logs
```

> **Important (Windows)** : créer le `.env` avec un éditeur qui n'ajoute pas de BOM (VS Code, Notepad++).  
> Éviter le Bloc-notes Windows ou `Set-Content` PowerShell sans `-Encoding utf8NoBOM`.

---

## Lancement

```bash
python main.py
```

Le menu principal s'affiche :

```
==================================================
   NTL-SysToolbox - NordTransit Logistics
   Outil de diagnostic et supervision v1.2
==================================================

=== MENU PRINCIPAL ===
1. Module Diagnostic
2. Module Sauvegarde WMS
3. Module Audit d'obsolescence
0. Quitter
```

---

## Modules

### 1. Diagnostic

Vérifie la disponibilité des services critiques du siège NTL.

| Option | Fonction |
|--------|----------|
| 1 | Vérifier AD/DNS sur DC01 (IP depuis `.env`) |
| 2 | Vérifier AD/DNS sur DC02 (IP depuis `.env`) |
| 3 | Vérifier AD/DNS sur une IP personnalisée |
| 4 | Tester la connexion MySQL (credentials depuis `.env`) |
| 5 | Diagnostic système local (OS, uptime, CPU, RAM, disques) |

Les résultats sont affichés en JSON et enregistrés dans `logs/`.  
Codes de retour : `0` = OK, `1` = erreur, `2` = avertissement ressources (CPU/RAM > 90 %).

---

### 2. Sauvegarde WMS

Gère les sauvegardes logiques de la base MySQL du système d'entrepôt.

| Option | Fonction |
|--------|----------|
| 1 | Dump SQL complet via `mysqldump` |
| 2 | Export d'une table au format CSV |
| 3 | Rotation des sauvegardes (supprime les plus anciennes) |

Les fichiers générés sont horodatés et placés dans le dossier `DOSSIER_SAUVEGARDES` (défaut : `sauvegardes/`).  
La rotation conserve les `NB_SAUVEGARDES_GARDER` fichiers les plus récents (défaut : 7).

---

### 3. Audit d'obsolescence

Inventorie le réseau et qualifie le statut de support des systèmes d'exploitation via l'API publique [endoflife.date](https://endoflife.date).

| Option | Fonction |
|--------|----------|
| 1 | Scanner une plage réseau (détection des hôtes et OS via nmap) |
| 2 | Lister toutes les versions d'un OS et leurs dates EOL |
| 3 | Vérifier le statut EOL d'une version précise |
| 4 | Analyser un fichier CSV d'inventaire et générer un rapport |

**Format du fichier CSV d'inventaire** (colonnes `os` et `version`) :
```csv
os,version
debian,13
ubuntu,20.04
windowsserver,2022
windows,10-21h2-w
windows,2022
```

Les noms d'OS correspondent aux identifiants de l'API endoflife.date (`ubuntu`, `debian`, `windows`, `windowsserver`, etc.).

Deux fichiers d'exemple sont fournis dans `data/` :
- `systems.csv` — jeu de démonstration
- `inventaire_ntl.csv` — inventaire de référence basé sur l'infrastructure de NTL

Les rapports sont générés dans `results/` :
- `eol_results.json` — données brutes horodatées
- `eol_report.html` — rapport visuel color-codé (voir ci-dessous)
- `network_scan.json` — résultats du scan réseau
- `versions_<os>.json` — liste des versions d'un OS

**Statuts du rapport HTML :**

| Couleur | Statut | Signification |
|---------|--------|---------------|
| Vert | Supporté | Date EOL dans plus de 6 mois |
| Orange | Bientôt EOL | Date EOL dans moins de 6 mois |
| Rouge | Obsolète | Date EOL dépassée |
| Gris | Inconnu | OS ou version non trouvé dans l'API |

---

## Artefacts produits

| Dossier | Contenu |
|---------|---------|
| `logs/` | Fichiers JSON horodatés des résultats de diagnostic et de sauvegarde |
| `sauvegardes/` | Dumps SQL (`.sql`) et exports CSV (`.csv`) |
| `results/` | Rapports d'audit (JSON, HTML, scan réseau) |

Ces dossiers sont créés automatiquement au premier lancement. Tous trois figurent dans le `.gitignore` (`logs/`, `sauvegardes/`, `results/`) et ne sont donc jamais versionnés.

---

## Structure du projet

```
MSPR3-CODE/
├── main.py                  # Point d'entrée — menu CLI interactif
├── requirements.txt         # Dépendances Python
├── .env.example             # Modèle de configuration (à copier en .env)
├── .gitignore
├── data/
│   ├── systems.csv          # Jeu de démonstration pour l'audit
│   └── inventaire_ntl.csv   # Inventaire de référence NTL
└── modules/
    ├── diagnostic.py        # Module Diagnostic (AD/DNS, MySQL, système)
    ├── sauvegarde.py        # Module Sauvegarde WMS (SQL, CSV, rotation)
    ├── eol_check.py         # Audit EOL — vérification et rapport HTML
    ├── list_versions.py     # Audit EOL — liste des versions d'un OS
    └── network_scan.py      # Audit EOL — scan réseau via nmap
```

---

## Dépendances Python

```
psutil>=5.9.0                # Métriques système (CPU, RAM, disques, uptime)
mysql-connector-python>=8.0.0 # Connexion MySQL
requests>=2.28.0             # Appels API endoflife.date
python-dotenv>=1.0.0         # Chargement du fichier .env
```
