# Learnings — Cloud Engineering Journey

## Datum: 07.–08. Mai 2026

---

## Phase 1: RDS PostgreSQL erstellen und mit EC2 verbinden

### Was wir gemacht haben

Wir haben eine managed PostgreSQL-Datenbank (RDS) erstellt und unsere FastAPI-App auf EC2 damit verbunden.

### Schritte

1. **DB Subnet Group erstellt**
   - Befehl: `aws rds create-db-subnet-group`
   - Was: Definiert in welchen Subnets (mindestens 2 verschiedene Availability Zones) die Datenbank leben darf
   - Warum: AWS RDS verlangt das für Hochverfügbarkeit — falls ein Rechenzentrum ausfällt, kann die DB in ein anderes wechseln

2. **Security Group für RDS erstellt**
   - Befehl: `aws ec2 create-security-group`
   - Was: Eine Firewall speziell für die Datenbank
   - Warum: Standardmäßig blockiert eine Security Group ALLES. Wir brauchen eine eigene, um gezielt Zugriff zu erlauben

3. **Inbound Rule hinzugefügt (EC2 → RDS)**
   - Befehl: `aws ec2 authorize-security-group-ingress --source-group sg-0342f...`
   - Was: Erlaubt TCP Port 5432 (PostgreSQL) NUR von Instanzen mit der EC2 Security Group
   - Warum: So kann nur unser EC2 die Datenbank erreichen — niemand sonst
   - Wichtig: `--source-group` statt einer IP-Adresse → wenn wir den EC2 ersetzen, funktioniert es weiterhin solange die neue Instanz die gleiche Security Group hat

4. **RDS Instance erstellt**
   - Befehl: `aws rds create-db-instance`
   - Parameter: db.t3.micro, postgres, 20GB, --no-publicly-accessible
   - Was: Eine managed PostgreSQL-Datenbank
   - Warum: AWS kümmert sich um Backups, Updates, Patches. Wir müssen nur verbinden
   - `--no-publicly-accessible`: Kein öffentlicher Zugang — nur innerhalb des VPC erreichbar

5. **PostgreSQL Client auf EC2 installiert und Verbindung getestet**
   - Befehl: `sudo yum install -y postgresql15` dann `psql -h <endpoint> -U postgres -d postgres`
   - Was: Nur den Client installiert (nicht den Server!) um die Verbindung zu testen
   - Warum: Beweist dass das Netzwerk korrekt konfiguriert ist bevor wir die App umstellen

6. **FastAPI App mit RDS verbunden**
   - DATABASE_URL als Environment Variable gesetzt
   - `psycopg2-binary` war schon in requirements.txt
   - App gestartet mit `fastapi run main.py --host 0.0.0.0`

### Fehler und Probleme

#### Fehler: `RequestExpired` bei Security Group Befehl
- **Was passiert ist:** `aws ec2 authorize-security-group-ingress` gab "Request has expired" zurück
- **Warum:** AWS SSO Credentials waren abgelaufen (haben eine begrenzte Lebensdauer)
- **Lösung:** `aws sso login` (bzw. `aws login`) ausgeführt um neue Credentials zu bekommen
- **Learning:** SSO Credentials laufen ab! Wenn plötzlich Befehle fehlschlagen die vorher gingen → Credentials refreshen

#### Fehler: RDS `describe-db-instances` gab nichts zurück
- **Was passiert ist:** Wir dachten es gibt eine RDS-Instanz, aber der Befehl war leer
- **Warum:** Es gab keine RDS — nur ein lokal installiertes PostgreSQL
- **Learning:** Unterschied verstehen: PostgreSQL auf EC2 ≠ RDS PostgreSQL. RDS ist ein AWS-managed Service

#### Problem: `--host 0.0.0.0` vergessen
- **Was passiert ist:** App war von außen nicht erreichbar
- **Warum:** Ohne `--host 0.0.0.0` hört FastAPI nur auf `127.0.0.1` (localhost) — nur vom Server selbst erreichbar
- **Learning:** Für Server-Deployment IMMER `--host 0.0.0.0` setzen

#### Problem: Route `/posts` gab "Not Found"
- **Was passiert ist:** 404 Error beim Aufrufen von /posts
- **Warum:** Kein Datenbank-Problem — die Route hieß anders oder war nicht korrekt eingebunden
- **Lösung:** `/docs` aufgerufen um alle registrierten Routen zu sehen
- **Learning:** Bei 404 immer zuerst `/docs` checken — zeigt alle verfügbaren Endpoints

---

## Phase 2: Docker

### Was wir gemacht haben

Die FastAPI-App containerisiert — lokal mit Docker Compose getestet, dann auf EC2 deployed.

### Konzepte gelernt

- **Dockerfile** = Liste von Befehlen die ein Image erzeugen (wie ein Installations-Skript)
- **Image** = Snapshot/Bauplan (Ergebnis des Dockerfiles)
- **Container** = Laufende Instanz eines Images
- **Docker Compose** = YAML-Datei die mehrere Container beschreibt und zusammen startet
- **Docker Hub** = "App Store" für fertige Images (postgres, redis, nginx, etc.)
- **YAML** = Deklarative Konfiguration ("so soll es aussehen"), kein Code ("tu dies")

### Schritte

1. **Dockerfile erstellt**
   ```dockerfile
   FROM python:3.14-slim    # Basis-Image mit Python
   WORKDIR /app             # Arbeitsverzeichnis
   COPY requirements.txt .  # Dependencies zuerst (Caching!)
   RUN pip install -r requirements.txt
   COPY . .                 # Code kopieren
   CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **.dockerignore erstellt**
   - Was: Dateien die NICHT ins Image kopiert werden
   - Warum: `.env` (Secrets!), `.venv` (unnötig groß), `.git`, `__pycache__`

3. **docker-compose.yml erstellt**
   - Zwei Services: `app` (unser Code) + `db` (PostgreSQL Container)
   - App verbindet sich mit DB über den Service-Namen `db`
   - Lokale Entwicklung ohne AWS-Abhängigkeit

4. **Lokal getestet mit `docker compose up --build`**

5. **Docker auf EC2 installiert**
   - `sudo yum install -y docker`
   - `sudo systemctl start docker` + `enable`
   - `sudo usermod -aG docker ec2-user` (Docker ohne sudo nutzen)
   - Ausloggen + neu einloggen (Gruppenänderung aktivieren)

6. **Code auf EC2 gepullt und Image gebaut**
   - `git pull` (Code war schon geklont)
   - `docker build -t fastapi-app .`

7. **Container auf EC2 gestartet**
   - `docker run -d -p 80:8000 --env-file .env fastapi-app`
   - `-d` = detached (Hintergrund)
   - `-p 80:8000` = Port 80 außen → Port 8000 im Container
   - `--env-file` = Umgebungsvariablen aus Datei laden

### Fehler und Probleme

#### Fehler: `docker build -t fastapi-app` ohne Punkt
- **Was passiert ist:** "requires 1 argument" Error
- **Warum:** Docker braucht den Build-Context — der `.` am Ende sagt "nutze das aktuelle Verzeichnis"
- **Lösung:** `docker build -t fastapi-app .` (mit Punkt!)
- **Learning:** Der `.` ist der Build-Context — Docker sucht dort nach dem Dockerfile und den Dateien zum Kopieren

#### Fehler: Port 5432 already in use (Docker Compose)
- **Was passiert ist:** `bind: address already in use` für Port 5432
- **Warum:** Lokales PostgreSQL lief bereits auf Port 5432 auf dem Mac
- **Lösung:** Port-Mapping geändert auf `5433:5432` — Container nutzt intern weiterhin 5432, aber von außen (Mac) ist es auf 5433 erreichbar
- **Learning:** Wenn ein Port belegt ist, einfach das externe Mapping ändern. Der Container intern bleibt gleich

#### Überlegung: Wo bauen — lokal oder auf dem Server?
- **Entscheidung:** Lokal entwickeln und testen, dann auf Server deployen
- **Warum:** Wenn lokal was kaputt geht, läuft die Produktion weiter. Nie auf dem Live-Server experimentieren

---

## Phase 3: CI/CD mit GitHub Actions + ECR

### Was wir gemacht haben

Eine automatische Pipeline gebaut: bei jedem `git push` wird das Image gebaut, zu ECR gepusht, und auf EC2 deployed.

### Konzepte gelernt

- **CI/CD** = Continuous Integration / Continuous Deployment — automatisches Bauen und Deployen
- **ECR** = Elastic Container Registry — privater "Docker Hub" in AWS
- **GitHub Actions** = Pipeline-Service von GitHub, reagiert auf Events (push, PR, etc.)
- **GitHub Secrets** = Verschlüsselte Variablen die nur in der Pipeline verfügbar sind
- **IAM Role für EC2** = EC2 bekommt Berechtigungen ohne Access Keys (Best Practice)

### Schritte

1. **ECR Repository erstellt**
   - Befehl: `aws ecr create-repository --repository-name fastapi-app`
   - Was: Privater Speicherort für unsere Docker Images
   - Ergebnis: `889749951196.dkr.ecr.eu-central-1.amazonaws.com/fastapi-app`

2. **IAM User für GitHub Actions erstellt**
   - `aws iam create-user --user-name github-actions`
   - Policy: `AmazonEC2ContainerRegistryPowerUser` (nur ECR, nichts anderes)
   - Access Key erstellt für diesen User
   - Warum separater User: Minimale Rechte — falls Keys leaken, kann niemand EC2/RDS löschen

3. **IAM Role für EC2 erstellt**
   - `aws iam create-role --role-name ec2-ecr-role`
   - Policy: `AmazonEC2ContainerRegistryReadOnly`
   - Instance Profile erstellt und an EC2 gehängt
   - Warum: EC2 braucht Berechtigung um Images von ECR zu pullen — aber ohne Access Keys (Best Practice)

4. **GitHub Secrets eingerichtet**
   - `AWS_ACCESS_KEY_ID` — vom github-actions IAM User
   - `AWS_SECRET_ACCESS_KEY` — vom github-actions IAM User
   - `EC2_HOST` — Public IP des EC2
   - `EC2_SSH_KEY` — Inhalt der .pem Datei (privater SSH Key)

5. **GitHub Actions Workflow erstellt** (`.github/workflows/deploy.yml`)
   - Trigger: Push auf `main` Branch
   - Steps: Checkout → ECR Login → Build & Push Image → SSH auf EC2 → Pull & Run

6. **Pipeline getestet und Fehler behoben** (siehe unten)

### Fehler und Probleme

#### Fehler: AWS Credentials auf EC2 nicht gefunden
- **Fehlermeldung:** `Unable to locate credentials. You can configure credentials by running "aws login"`
- **Was passiert ist:** Die Pipeline hat per SSH auf EC2 `aws ecr get-login-password` ausgeführt, aber EC2 hatte keine AWS Credentials
- **Warum:** EC2 nutzte SSO (interaktiv) — das funktioniert nicht in automatisierten Prozessen
- **Lösung:** IAM Role an EC2 gehängt (Instance Profile) — EC2 bekommt Credentials automatisch von AWS
- **Learning:** Für automatisierte Prozesse auf EC2 IMMER IAM Roles nutzen, nie Access Keys oder SSO

#### Fehler: `.env` Datei nicht gefunden
- **Fehlermeldung:** `docker: open /home/ec2-user/.env: no such file or directory`
- **Was passiert ist:** Pipeline suchte `.env` unter `/home/ec2-user/.env`, aber die Datei lag in `/home/ec2-user/example-fastapi/.env`
- **Warum:** Wir hatten den Pfad in der Pipeline falsch angenommen
- **Lösung:** Pfad in der Pipeline korrigiert zu `--env-file /home/ec2-user/example-fastapi/.env`
- **Learning:** Pfade auf dem Server immer verifizieren mit `find ~ -name ".env"`

#### Fehler: ECR URL Tippfehler in der Pipeline
- **Fehlermeldung:** `no such host` und `repository does not exist`
- **Was passiert ist:** Die ECR-URL war an zwei Stellen falsch:
  - `889749951196.dkr.eceu-central-1` statt `889749951196.dkr.ecr.eu-central-1` (fehlendes `r.`)
  - `amazonaws.cofastapi-app` statt `amazonaws.com/fastapi-app` (fehlendes `m/`)
- **Warum:** Zeilenumbruch-Probleme beim Kopieren in die YAML-Datei
- **Lösung:** URLs korrigiert
- **Learning:** Bei "no such host" Fehlern IMMER die URL zeichenweise prüfen. Copy-Paste in YAML kann Zeichen verschlucken

#### Fehler: Port 80 already allocated
- **Fehlermeldung:** `Bind for 0.0.0.0:80 failed: port is already allocated`
- **Was passiert ist:** Der alte Container (den wir manuell gestartet hatten) lief noch auf Port 80
- **Warum:** `docker stop fastapi-app` fand den Container nicht, weil er beim manuellen Start keinen Namen hatte (nur eine ID)
- **Lösung:** Manuell alle Container gestoppt: `docker stop $(docker ps -q)` + `docker rm $(docker ps -aq)`
- **Learning:** Container IMMER mit `--name` starten. Ab jetzt heißt er `fastapi-app` und die Pipeline kann ihn finden und stoppen

#### Problem: `git commit -m "!"` — Terminal hing
- **Was passiert ist:** Nach dem Commit-Befehl kam `dquote>` und nichts ging mehr
- **Warum:** `!` hat in Bash eine spezielle Bedeutung (History Expansion). Bash dachte der String ist nicht fertig
- **Lösung:** `Ctrl+C` zum Abbrechen, dann einfache Anführungszeichen nutzen: `git commit -m 'message'`
- **Learning:** Für Commit-Messages mit Sonderzeichen einfache Anführungszeichen `'...'` verwenden

---

## Git Best Practices (gelernt)

- `git add <datei>` statt `git add .` — gezielt auswählen was committet wird
- Commit-Messages auf Englisch, beschreiben WAS die Änderung tut
- Eine logische Änderung pro Commit
- `.env` NIEMALS committen (muss in `.gitignore` stehen)
- Reihenfolge: `git add` → `git commit` → `git push`
- `git pull` auf dem Server um neueste Änderungen zu holen

---

## Architektur — Was wir gebaut haben

```
Developer (Mac)
    │
    │ git push
    ▼
GitHub Actions (Pipeline)
    │
    │ 1. Baut Docker Image
    │ 2. Pusht zu ECR
    │ 3. SSH auf EC2
    ▼
┌──────────────────────────────────┐
│  EC2 Server                      │
│  - Docker installiert            │
│  - IAM Role für ECR-Zugriff     │
│  - .env mit Secrets             │
│                                  │
│  ┌────────────────────────┐      │
│  │  Docker Container      │      │
│  │  FastAPI App           │      │
│  │  Port 8000 intern      │      │
│  └──────────┬─────────────┘      │
│             │ Port 80 extern     │
└─────────────┼────────────────────┘
              │
              │ Port 5432 (Security Group erlaubt)
              ▼
┌──────────────────────────────────┐
│  RDS (PostgreSQL)                │
│  - Nicht öffentlich zugänglich   │
│  - Nur von EC2 erreichbar       │
│  - Managed by AWS               │
└──────────────────────────────────┘
```

---

## Wichtige Konzepte

| Konzept | Bedeutung |
|---|---|
| VPC | Dein privates Netzwerk in AWS |
| Subnet | Unterteilung des VPC in verschiedene Availability Zones |
| Security Group | Firewall-Regeln (wer darf wohin) |
| IAM Role | Berechtigungen für AWS-Services (ohne Passwörter) |
| IAM User | Berechtigungen für Menschen/Pipelines (mit Access Keys) |
| ECR | Private Docker Image Registry in AWS |
| Port Mapping | Externer Port → Interner Container-Port |
| Environment Variables | Konfiguration außerhalb des Codes (Secrets, URLs) |
| Docker Compose | Mehrere Container lokal zusammen starten |
| CI/CD | Automatisches Bauen und Deployen bei Code-Änderungen |

---

---

## Phase 4: Terraform / OpenTofu — Infrastruktur als Code

### Datum: 12. Mai 2026

### Was wir gemacht haben

Die gesamte Infrastruktur (die wir vorher manuell per CLI erstellt haben) als Code definiert. Ein `tofu apply` erstellt alles automatisch, ein `tofu destroy` löscht alles.

### Konzepte gelernt

- **Terraform / OpenTofu** = Tool das Infrastruktur aus Code-Dateien (`.tf`) erstellt
- **OpenTofu** = Open-Source Fork von Terraform (gleiche Syntax, community-geführt, bessere Lizenz)
- **Deklarativ** = Du beschreibst WAS du willst, nicht WIE es gemacht wird
- **State** = Terraform merkt sich was es erstellt hat (in `terraform.tfstate`)
- **Plan** = Vorschau was passieren wird (ohne es zu tun)
- **Apply** = Führt die Änderungen tatsächlich aus
- **Destroy** = Löscht alles was Terraform erstellt hat
- **Outputs** = Werte die nach dem Apply angezeigt werden (IPs, Endpoints, URLs)
- **Referenzen** = `aws_vpc.main.id` — Terraform versteht Abhängigkeiten automatisch

### Die richtige Reihenfolge (Abhängigkeiten)

```
1. VPC                          ← Alles lebt darin
2. Subnets (mind. 2 AZs)       ← Unterteilungen des VPC
3. Internet Gateway             ← Tür zum Internet
4. Route Table + Associations   ← Wegbeschreibung für Traffic
5. Security Groups              ← Firewall-Regeln
6. DB Subnet Group              ← Wo RDS leben darf
7. RDS                          ← Datenbank
8. IAM Role + Instance Profile  ← Berechtigungen für EC2
9. ECR Repository               ← Container Registry
10. EC2 Instanz                 ← Server
```

**Merksatz:** Netzwerk → Regeln → Ressourcen → Berechtigungen

### Schritte

1. **Provider konfiguriert**
   ```hcl
   provider "aws" {
     region = "eu-central-1"
   }
   ```
   - Was: Sagt OpenTofu "arbeite mit AWS in Frankfurt"
   - `tofu init` lädt das AWS-Plugin runter

2. **VPC erstellt**
   ```hcl
   resource "aws_vpc" "main" {
     cidr_block = "10.0.0.0/16"
   }
   ```
   - `/16` = 65.536 IP-Adressen (kostet nichts extra, gibt Spielraum)
   - Nachträglich vergrößern geht nicht → lieber zu groß als zu klein

3. **2 Subnets in verschiedenen AZs**
   ```hcl
   resource "aws_subnet" "a" {
     vpc_id            = aws_vpc.main.id    # ← Referenz!
     cidr_block        = "10.0.1.0/24"      # 256 Adressen
     availability_zone = "eu-central-1a"
   }
   ```
   - `/24` = 256 Adressen aus dem großen `/16` Pool
   - `10.0.1.x` für Subnet A, `10.0.2.x` für Subnet B (überlappen nicht)
   - RDS braucht mindestens 2 AZs für Ausfallsicherheit

4. **Internet Gateway + Route Table**
   - Internet Gateway = die "Autobahn-Auffahrt" zum Internet
   - Route Table = das "Navi" (`0.0.0.0/0` → Internet Gateway)
   - Route Table Association = verbindet Subnets mit dem Navi
   - Ohne diese drei Teile: EC2 ist komplett isoliert, niemand kommt rein oder raus

5. **Security Groups (2 Stück)**
   - EC2 SG: Port 80 (HTTP) + Port 22 (SSH) von überall, Egress alles erlaubt
   - RDS SG: Port 5432 NUR von der EC2 Security Group
   - `security_groups = [aws_security_group.ec2.id]` = gleich wie `--source-group` in CLI

6. **DB Subnet Group + RDS**
   - Subnet Group sagt RDS welche Subnets erlaubt sind
   - `publicly_accessible = false` = kein Internet-Zugang
   - `skip_final_snapshot = true` = beim Löschen keinen Backup machen (nur für Test!)

7. **ECR Repository**
   - Eine Zeile: `name = "fastapi-app"` — fertig
   - Gleich wie `aws ecr create-repository`

8. **IAM Role + Instance Profile**
   - Role = die Berechtigung selbst
   - `assume_role_policy` = WER darf die Rolle nutzen (nur EC2)
   - Policy Attachment = WELCHE Rechte (ECR ReadOnly)
   - Instance Profile = die "Hülle" die Role an EC2 bindet

9. **EC2 Instanz**
   - `user_data` = Befehle die beim ersten Start automatisch laufen (Docker installieren!)
   - `associate_public_ip_address = true` = öffentliche IP zuweisen
   - `key_name` = SSH Key für Zugang

10. **Outputs definiert**
    ```hcl
    output "ec2_public_ip" {
      value = aws_instance.main.public_ip
    }
    ```
    - Zeigt wichtige Werte nach `tofu apply` an
    - Statt manuell in AWS Console suchen

### Fehler und Probleme

#### Fehler: Syntax-Fehler — fehlendes Anführungszeichen
- **Was passiert ist:** `Invalid multi-line string` Error
- **Warum:** `"fastapi-vpc` statt `"fastapi-vpc"` — schließendes `"` vergessen
- **Learning:** Terraform/OpenTofu Syntax ist streng. Jeder String braucht öffnende UND schließende Anführungszeichen

#### Fehler: `No valid credential sources found`
- **Was passiert ist:** OpenTofu konnte sich nicht bei AWS anmelden
- **Warum:** `aws login` speichert Credentials an einem Ort den OpenTofu nicht automatisch findet
- **Lösung:** `eval "$(aws configure export-credentials --format env)"` — exportiert Credentials als Environment Variables
- **Learning:** OpenTofu braucht Credentials als Env Vars oder in `~/.aws/credentials`. SSO-Login allein reicht nicht immer

#### Fehler: Subnet ohne `cidr_block`
- **Was passiert ist:** `MissingParameter: The request must contain cidrBlock`
- **Warum:** Subnet braucht einen eigenen IP-Bereich — vergessen anzugeben
- **Learning:** Jedes Subnet braucht einen CIDR-Block der ein Teil des VPC-Bereichs ist

#### Fehler: `No configuration files` bei `tofu apply`
- **Was passiert ist:** OpenTofu fand keine `.tf` Dateien
- **Warum:** Wir waren im falschen Verzeichnis (`Twitter/` statt `Twitter/terraform/`)
- **Learning:** OpenTofu sucht `.tf` Dateien nur im aktuellen Verzeichnis. Immer `cd terraform` zuerst

#### Problem: Namenskonflikte mit alten Ressourcen
- **Was passiert ist:** RDS Subnet Group konnte nicht erstellt werden weil der Name schon existierte
- **Warum:** Die manuell erstellten Ressourcen (Phase 1) waren noch da
- **Lösung:** Alle alten Ressourcen manuell gelöscht (in der richtigen Reihenfolge!)
- **Learning:** Abhängigkeiten beim Löschen beachten: RDS weg → dann Subnet Group. EC2 weg → dann Security Group

### Aufräumen — Reihenfolge beim Löschen

Ressourcen die von anderen benutzt werden, können nicht gelöscht werden:
1. Container stoppen
2. RDS löschen (dauert ~5 min)
3. DB Subnet Group löschen (erst wenn RDS weg)
4. EC2 terminieren
5. Security Groups löschen (erst wenn EC2/RDS weg)
6. ECR löschen
7. IAM aufräumen (Policy abtrennen → Role aus Profile → Profile löschen → Role löschen)

**Mit Terraform:** `tofu destroy` macht das alles automatisch in der richtigen Reihenfolge!

### Was NICHT in Git gehört

| Datei | Warum nicht |
|---|---|
| `terraform.tfstate` | Enthält Zustand inkl. Passwörter, IPs, IDs |
| `terraform.tfstate.backup` | Backup davon |
| `.terraform/` | Heruntergeladene Plugins (wie node_modules) |
| `*.tfvars` | Variable-Werte (können Secrets enthalten) |

### Variablen für Secrets

```hcl
variable "db_password" {
  type      = string
  sensitive = true    # wird nicht in Logs angezeigt
}

# Nutzung:
password = var.db_password
```

OpenTofu fragt beim `tofu apply` nach dem Wert. So steht kein Passwort im Code.

---

## Gesamtarchitektur (finale Version)

```
Developer (Mac)
    │
    │ git push
    ▼
GitHub Actions (Pipeline)
    │
    │ 1. Baut Docker Image
    │ 2. Pusht zu ECR
    │ 3. SSH auf EC2
    ▼
┌──────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16)                               │
│                                                  │
│  ┌─────────────────┐    ┌─────────────────┐     │
│  │ Subnet A        │    │ Subnet B        │     │
│  │ eu-central-1a   │    │ eu-central-1b   │     │
│  │                 │    │                 │     │
│  │ ┌─────────────┐ │    │                 │     │
│  │ │ EC2         │ │    │                 │     │
│  │ │ Docker      │ │    │                 │     │
│  │ │ FastAPI     │ │    │                 │     │
│  │ │ Port 80→8000│ │    │                 │     │
│  │ └──────┬──────┘ │    │                 │     │
│  └────────┼─────────┘    └────────┬────────┘     │
│           │                       │              │
│           │ Port 5432             │              │
│           ▼                       │              │
│  ┌────────────────────────────────┘              │
│  │  RDS PostgreSQL                               │
│  │  (DB Subnet Group: Subnet A + B)             │
│  │  Nicht öffentlich zugänglich                  │
│  └───────────────────────────────────────────────│
│                                                  │
│  Internet Gateway ←→ Route Table                 │
└──────────────────────────────────────────────────┘
         ▲
         │ Port 80 (HTTP)
         │
    [Internet / Browser]
```

---

## Alle Konzepte zusammengefasst

| Konzept | Bedeutung | Analogie |
|---|---|---|
| VPC | Privates Netzwerk in AWS | Dein Grundstück |
| Subnet | Unterteilung in AZs | Stockwerke im Gebäude |
| Internet Gateway | Verbindung zum Internet | Autobahn-Auffahrt |
| Route Table | Wegbeschreibung für Traffic | Navi |
| Security Group | Firewall (wer darf wohin) | Türschloss |
| IAM Role | Berechtigungen für Services | Mitarbeiterausweis |
| IAM User | Berechtigungen für Menschen/Pipelines | Personalausweis |
| ECR | Private Container Registry | Privater App Store |
| RDS | Managed Datenbank | Datenbank-as-a-Service |
| Port Mapping | Extern → Intern | Hotel-Rezeption → Zimmer |
| Environment Variables | Config außerhalb des Codes | Einstellungen |
| Docker Image | Bauplan/Snapshot | ISO-Datei |
| Docker Container | Laufende Instanz | Installierte App |
| Docker Compose | Mehrere Container zusammen | Lokales Setup |
| CI/CD | Automatisches Deployment | Fließband |
| Terraform/OpenTofu | Infrastruktur als Code | Bauplan für alles |
| `tofu plan` | Vorschau | Kostenvoranschlag |
| `tofu apply` | Ausführen | Bauen |
| `tofu destroy` | Alles löschen | Abriss |

---

## Nächste Schritte

- [x] RDS PostgreSQL erstellen und verbinden
- [x] Docker — App containerisieren
- [x] CI/CD — Automatisches Deployment
- [x] Terraform/OpenTofu — Infrastruktur als Code
- [ ] Blue-Green Deployment — Zero-Downtime Deployments
- [ ] HTTPS/SSL — Verschlüsselte Verbindung
- [ ] Monitoring/Logging — Wissen wenn etwas kaputt geht
- [ ] ECS — Container-Orchestrierung (statt manuell auf EC2)
