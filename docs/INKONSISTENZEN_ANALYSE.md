# Inkonsistenzen-Analyse: claude-agent-sdk Plugin

> Ergebnis der manuellen Prozessanalyse vom 2025-12-11
> Ziel: Identifikation aller Inkonsistenzen zwischen Plugin-Dokumentation, Troubleshooting-Doc und tatsächlichem Verhalten

---

## Zusammenfassung

**12 Inkonsistenzen gefunden**, davon:
- 6 kritisch (führen zu Fehlern)
- 4 mittel (führen zu Verwirrung/Mehraufwand)
- 2 niedrig (dokumentationsrelevant)

### ✅ LÖSUNG GEFUNDEN (2025-12-11 16:06)

**Root Cause:** OrbStack mappt Mac-User auf hohe UIDs (zimmermannb → 1792997461), aber Container verwenden UID 1000.

**Lösung:** Dedizierter `kodosumi` User mit UID 1000 + systemd Services

| Komponente | Vorher | Nachher |
|------------|--------|---------|
| VM User | zimmermannb (UID 1792997461) | kodosumi (UID 1000) |
| Container User | ray (UID 1000) | ray (UID 1000) |
| Workaround | `chmod -R 777 /tmp/ray/` | **Nicht mehr nötig!** |

→ Siehe "✅ LÖSUNG VERIFIZIERT" am Ende dieses Dokuments

---

## Inkonsistenz #1: Docker vs Podman

| Priorität | MITTEL |
|-----------|--------|
| **Quelle A** | `setup-vm.sh` (Plugin) - Zeile 85 |
| **Quelle B** | `MARKUS_TROUBLESHOOTING.md` - Zeilen 181-190 |

### Problem
- **Plugin-Script** installiert **Docker** (`docker.io`)
- **Troubleshooting-Doc** verwendet ausschließlich **Podman**-Befehle

### Betroffene Befehle
```bash
# Plugin sagt:
sudo apt install -y docker.io

# Troubleshooting-Doc verwendet:
podman login ghcr.io
podman pull ghcr.io/...
podman run --rm ...
podman ps -a
```

### Auswirkung
Anwender wissen nicht, welche Container-Runtime sie verwenden sollen.

### Empfehlung
Entscheiden: Docker ODER Podman. Beide Dokumentationen vereinheitlichen.

---

## Inkonsistenz #2: Ray fehlt im VM-Setup

| Priorität | KRITISCH |
|-----------|----------|
| **Quelle A** | `setup-vm.sh` (Plugin) |
| **Quelle B** | `MARKUS_TROUBLESHOOTING.md` - Zeilen 91-110 |

### Problem
- **Plugin-Script** installiert Ray NICHT in der VM
- **Troubleshooting-Doc** setzt Ray als installiert voraus und prüft Versionen

### Details
```bash
# setup-vm.sh installiert:
- Docker
- Python 3.12
- Node.js 18
- Claude CLI
- rsync, git

# ABER NICHT:
- Ray (wird erwartet via pip install -e .)
```

### Auswirkung
Anwender müssen wissen, dass Ray durch `pip install -e .` nachinstalliert wird.

### Empfehlung
Explizit dokumentieren, WANN Ray installiert wird.

---

## Inkonsistenz #3: venv Pfad

| Priorität | MITTEL |
|-----------|--------|
| **Quelle A** | `setup-vm.sh` (Plugin) - Zeile 181 |
| **Quelle B** | `MARKUS_TROUBLESHOOTING.md` |

### Problem
```bash
# Plugin sagt:
cd ~/dev/cc-hitl-template && python3.12 -m venv .venv
# → ~/dev/cc-hitl-template/.venv

# Troubleshooting-Doc verwendet:
source ~/.venv/bin/activate
# → ~/.venv
```

### Auswirkung
Verwirrung über korrekten venv-Pfad.

### Empfehlung
Einheitlichen Pfad festlegen: `~/dev/cc-hitl-template/.venv`

---

## Inkonsistenz #4: Justfile-Befehlsname

| Priorität | NIEDRIG |
|-----------|---------|
| **Quelle A** | `setup-vm.sh` (Plugin) - Zeile 185 |
| **Quelle B** | `justfile` |

### Problem
```bash
# Plugin sagt:
just orb-start

# Justfile hat:
just start
```

### Auswirkung
`just orb-start` existiert nicht, Befehl schlägt fehl.

### Empfehlung
Plugin-Dokumentation aktualisieren auf `just start`.

---

## Inkonsistenz #5: Fehlende Dependency `sniffio`

| Priorität | KRITISCH |
|-----------|----------|
| **Quelle** | `pip install -e .` installiert nicht alle Dependencies |

### Problem
```
ModuleNotFoundError: No module named 'sniffio'
```

`litestar` (via `kodosumi`) benötigt `sniffio`, aber es wird nicht installiert.

### Betroffene Stelle
`kodosumi/litestar` Package-Definition fehlt `sniffio` als Dependency.

### Fix angewendet
```bash
pip install sniffio
```

### Empfehlung
`sniffio` zu den Dependencies in `kodosumi` oder `pyproject.toml` hinzufügen.

---

## Inkonsistenz #6: Veraltete all_apps.yaml

| Priorität | KRITISCH |
|-----------|----------|
| **Quelle** | `data/config/all_apps.yaml` |

### Problem
```yaml
# all_apps.yaml referenziert:
import_path: customer_journey_agent.query:fast_app

# Aber dieses Modul existiert NICHT im Projekt!
```

### Auswirkung
`koco deploy` schlägt fehl mit ValidationError.

### Fix angewendet
```bash
mv all_apps.yaml all_apps.yaml.DISABLED
```

### Empfehlung
`all_apps.yaml` aus dem Repository entfernen oder aktualisieren.

---

## Inkonsistenz #7: koco deploy vs serve deploy

| Priorität | MITTEL |
|-----------|--------|
| **Beobachtung** | Unterschiedliches Verhalten |

### Problem
```bash
# Schlägt fehl:
koco deploy -r

# Funktioniert:
serve deploy data/config/claude_hitl_template.yaml
```

### Auswirkung
Anwender müssen `serve deploy` direkt verwenden statt `koco deploy`.

### Empfehlung
`koco deploy` Logik untersuchen und fixen.

---

## Inkonsistenz #8: Deployment-Name Mismatch

| Priorität | KRITISCH |
|-----------|----------|
| **Quelle A** | `claude_hitl_template.yaml` - Zeile 28 |
| **Quelle B** | `claude_hitl_template/query.py` - Zeile 686 |

### Problem
```yaml
# YAML sagt:
deployments:
  - name: ClaudeHitlTemplateService

# Code hat:
@serve.deployment
class ClaudeHitlTemplate:
```

### Fehlermeldung
```
ValueError: Deployment 'ClaudeHitlTemplateService' does not exist.
Available: ['ClaudeHitlTemplate']
```

### Fix angewendet
YAML geändert: `ClaudeHitlTemplateService` → `ClaudeHitlTemplate`

### Empfehlung
YAML-Template mit korrektem Namen im Repository aktualisieren.

---

## Inkonsistenz #9: Falscher Ray Serve Port

| Priorität | MITTEL |
|-----------|--------|
| **Quelle A** | `justfile` - Zeile 19 |
| **Quelle B** | Ray Serve Default |

### Problem
```bash
# Justfile verwendet:
koco serve --register http://localhost:8001/-/routes

# Ray Serve läuft auf:
Port 8000 (default)
```

### Fehlermeldung
```
CRITICAL failed to connect http://localhost:8001/-/routes
```

### Auswirkung
Kodosumi kann sich nicht bei Ray Serve registrieren.

### Empfehlung
Justfile ändern: `8001` → `8000`

---

## Weitere Beobachtungen

### Host vs VM Architektur

Die aktuelle Architektur hat eine "leaky abstraction":

| Komponente | Aktuell | Empfohlen |
|------------|---------|-----------|
| Konfiguration (.env, YAML) | HOST + VM (manuell sync) | Nur VM |
| Python venv | HOST + VM (unterschiedlich) | Nur VM |
| koco spool/serve | Je nach Version HOST oder VM | Nur VM |
| Ray Cluster | VM | VM |
| Container Runtime | VM | VM |

**Empfehlung:** Alle Komponenten in die VM verlagern, Host nur für Entwicklung.

### Ray Version

| Installiert | Troubleshooting-Doc |
|-------------|---------------------|
| 2.52.1 | 2.51.1 erwartet |

**Risiko:** Version Mismatch mit Container-Images.

---

## Prioritäten für Fixes

### Sofort (P0) - ROOT CAUSE ✅ GELÖST
1. [x] **#12: Dedizierter `kodosumi` User (UID 1000) in VM anlegen**
   - ✅ User angelegt mit UID 1000
   - ✅ systemd Services konfiguriert
   - ✅ chmod-Workaround nicht mehr nötig
   - ✅ Container laufen ohne Permission-Fehler

### Sofort (P0) - Gefixt ✅
2. [x] ~~Dependency `sniffio` zu kodosumi hinzufügen~~ (manuell installiert)
3. [x] ~~YAML-Template mit korrektem Deployment-Namen~~ (#8 gefixt)
4. [x] ~~`all_apps.yaml` entfernen~~ (#6 gefixt: .DISABLED)
5. [x] ~~Podman Rootless subuid/subgid~~ (#10 gefixt)
6. [x] ~~Ray Version VM/Container angleichen~~ (2.51.1)

### Kurzfristig (P1)
7. [ ] Justfile Port 8001 → 8000 ändern (#9)
8. [ ] Plugin-Dokumentation: `orb-start` → `start` (#4)
9. [ ] venv-Pfad vereinheitlichen (#3)
10. [x] ~~`setup-vm.sh` um kodosumi-User erweitern~~ (manuell implementiert + dokumentiert)

### Mittelfristig (P2)
11. [x] ~~Docker vs Podman Entscheidung~~ → **Podman** (Ray ignoriert RAY_CONTAINER_RUNTIME)
12. [ ] Host/VM Architektur klar trennen
13. [ ] Ray Version-Pinning in Container + VM
14. [ ] `koco deploy` vs `serve deploy` untersuchen (#7)

---

## Test-Ergebnis nach Fixes

| Service | Status | Port |
|---------|--------|------|
| Ray Dashboard | ✅ 200 OK | 8265 |
| Ray Serve HTTP | ✅ Läuft | 8000 |
| Kodosumi Admin | ✅ 401 (Login) | 3370 |
| koco spool | ✅ Läuft | - |
| koco serve | ✅ Läuft | 3370 |

**Deployment Status:** RUNNING, HEALTHY

---

## WICHTIG: Non-Containerized Deployment

### Aktueller Zustand

```yaml
# In data/config/claude_hitl_template.yaml:
runtime_env:
  env_vars:
    CONTAINER_IMAGE_URI: ""   # <-- LEER!
```

### Bedeutung

| CONTAINER_IMAGE_URI | Modus | Beschreibung |
|---------------------|-------|--------------|
| `""` (leer) | **Non-Containerized** | Agent läuft direkt auf VM-Filesystem |
| `ghcr.io/...@sha256:...` | **Containerized** | Agent läuft in Podman/Docker Container |

### Aktueller Test-Lauf

Der erfolgreiche Test-Lauf vom 2025-12-11 lief **NICHT** in einem Container:

```
✓ Actor created
✓ Connected
Agent Configuration
  CPUs: 1
  Memory: 1.0 GB
  Loaded Plugins: No plugins loaded  # <-- Keine Plugins = kein Container-Image
```

### Noch zu verifizieren

- [ ] Läuft der Agent wirklich containerisiert wenn `CONTAINER_IMAGE_URI` gesetzt ist?
- [ ] Welche Container-Runtime wird verwendet (Docker oder Podman)?
- [ ] Funktioniert das Container-Image mit der aktuellen Ray-Version (2.52.1)?

### Wie man Container-Modus verifiziert

Während einer HITL-Session:
```bash
# Container prüfen (in VM)
orb -m ray-cluster bash -c "podman ps"
orb -m ray-cluster bash -c "docker ps"

# Ray Actors prüfen
orb -m ray-cluster bash -c "ray list actors"
```

---

## Inkonsistenz #10: Podman Rootless nicht konfiguriert

| Priorität | KRITISCH |
|-----------|----------|
| **Kontext** | Container-Modus Test vom 2025-12-11 |

### Problem

Beim ersten Versuch, das Container-Image zu pullen:

```bash
orb -m ray-cluster bash -c "podman pull ghcr.io/plan-net/claude-hitl-worker:latest"
```

### Fehlermeldung

```
Error: copying system image from manifest list: writing blob: adding layer with blob "sha256:...":
unlinkat /var/tmp/storage-run-1000/containers/storage/overlay/.../diff/...:
invalid argument
```

### Root Cause

Podman Rootless benötigt konfigurierte `subuid`/`subgid` für UID-Mapping.

### Fix angewendet

```bash
# Auf dem Mac (Host):
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 zimmermannb
podman system migrate
```

### Empfehlung

`setup-vm.sh` sollte automatisch Podman Rootless konfigurieren.

---

## Inkonsistenz #11: Container UID Mismatch

| Priorität | KRITISCH |
|-----------|----------|
| **Kontext** | Container-Modus Test vom 2025-12-11 |

### Problem

Container starten, aber crashen sofort mit Exit Code 1.

### Fehlermeldung

```
PermissionError: [Errno 13] Permission denied:
'/tmp/ray/session_2025-12-11_14-01-48_061713_22003/ports_by_node.json.lock'
```

### Root Cause

| Kontext | UID | User |
|---------|-----|------|
| VM (Ray Head) | 1792997461 | zimmermannb |
| Container (Ray Worker) | 1000 | ray |

Die Lock-Dateien im Ray Session-Verzeichnis haben Permission `644` (nur Owner kann schreiben).
Der Container-User `ray` (UID 1000) hat keine Schreibrechte.

### Container-Details

```bash
# Volume Mount:
/tmp/ray:/tmp/ray:rw,rprivate,nosuid,nodev,rbind

# Container User:
uid=1000(ray) gid=100(users)

# VM User:
uid=1792997461(zimmermannb)
```

### Quick-Fix angewendet

```bash
# Alle Lock- und JSON-Dateien world-writable machen:
chmod -R a+rw /tmp/ray/session_*/*.lock /tmp/ray/session_*/*.json
```

### Empfehlung

1. **Option A**: Container mit `--userns=keep-id` starten (Podman-spezifisch)
2. **Option B**: Ray Session-Verzeichnis mit korrekten Permissions erstellen
3. **Option C**: Container-Image mit dynamischem UID-Mapping bauen

### Betroffene Komponente

Der Code, der Container startet (vermutlich in `kodosumi` oder `cc-hitl-template`)
muss UID-Handling implementieren.

### Status: GELÖST (Workaround)

Nach dem chmod 777 auf das Ray Session-Verzeichnis funktioniert der Container-Modus:

```bash
# Funktionierende Container (2025-12-11 15:00):
NAMES              IMAGE                                       STATUS
lucid_clarke       ghcr.io/plan-net/claude-hitl-worker:latest  Up 5 minutes
charming_shockley  ghcr.io/plan-net/claude-hitl-worker:latest  Up 5 minutes
```

**Workaround (temporär):**
```bash
chmod -R 777 /tmp/ray/session_*
```

**Permanente Lösung erforderlich:** Siehe "Root Cause Analyse" unten.

---

## Root Cause Analyse: OrbStack UID-Mapping

### Das eigentliche Problem

OrbStack mappt Mac-Benutzer auf sehr hohe UIDs in der VM:

| Kontext | User | UID | Quelle |
|---------|------|-----|--------|
| Mac (Host) | zimmermannb | (Mac UID) | macOS |
| OrbStack VM | zimmermannb | **1792997461** | OrbStack Auto-Mapping |
| Container | ray | **1000** | Container-Image |

Alle Services (Ray, koco) laufen als `zimmermannb` (UID 1792997461).
Container laufen als `ray` (UID 1000).
**→ UID Mismatch → Permission Denied**

### Empfohlene Lösung: Dedizierter `kodosumi` User

Einen Service-User mit UID 1000 in der VM anlegen:

```bash
# In der VM:
sudo useradd -u 1000 -m -s /bin/bash kodosumi
sudo usermod -aG docker kodosumi
sudo usermod -aG sudo kodosumi
```

Dann alle Services als `kodosumi` ausführen:

```bash
# Statt:
ray start --head ...

# Besser:
sudo -u kodosumi ray start --head ...
```

### Erwartetes Ergebnis nach User-Änderung

| Kontext | User | UID |
|---------|------|-----|
| VM (Services) | kodosumi | **1000** |
| Container | ray | **1000** |

**→ UIDs matchen! Keine chmod-Workarounds mehr nötig.**

### Implementierungsschritte

1. [ ] User `kodosumi` mit UID 1000 in VM anlegen
2. [ ] Projekt-Verzeichnis Ownership ändern: `chown -R kodosumi:kodosumi ~/dev/cc-hitl-template`
3. [ ] Services als `kodosumi` starten (justfile anpassen)
4. [ ] Ray Session-Verzeichnis wird dann mit UID 1000 erstellt
5. [ ] Container (UID 1000) haben automatisch Schreibrechte

---

## Inkonsistenz #12: OrbStack UID-Mapping (ROOT CAUSE)

| Priorität | KRITISCH - ROOT CAUSE |
|-----------|----------------------|
| **Kontext** | Container-Modus Test vom 2025-12-11 |

### Problem

OrbStack mappt Mac-Benutzer automatisch auf sehr hohe UIDs in Linux VMs.
Diese UIDs sind inkompatibel mit Standard-Container-Images (UID 1000).

### Technische Details

```bash
# Mac User wird in OrbStack VM zu:
uid=1792997461(zimmermannb)

# Container-Image verwendet:
uid=1000(ray)

# Ergebnis: Alle shared Volumes haben falschen Owner
```

### Warum das passiert

1. OrbStack verwendet UID-Mapping für nahtlose Mac-VM Integration
2. `setup-vm.sh` erstellt keinen dedizierten Service-User
3. Alle Services laufen als gemappter Mac-User
4. Container laufen als `ray` (UID 1000)
5. Shared `/tmp/ray` Verzeichnis: Owner-Mismatch

### Auswirkung

- Container können Lock-Dateien nicht erstellen/schreiben
- Permanenter Workaround `chmod -R 777 /tmp/ray/` erforderlich
- Sicherheitsrisiko durch world-writable Verzeichnisse

### Empfohlene Lösung

**Dedizierter `kodosumi` Service-User mit UID 1000:**

```bash
# 1. User anlegen (in VM)
sudo useradd -u 1000 -m -s /bin/bash kodosumi
sudo usermod -aG docker,sudo kodosumi

# 2. Projekt-Verzeichnis übertragen
sudo chown -R kodosumi:kodosumi /home/kodosumi/dev/cc-hitl-template

# 3. Services als kodosumi starten
sudo -u kodosumi bash -c "source .venv/bin/activate && ray start --head ..."
```

### Betroffene Komponenten

- `setup-vm.sh` - muss kodosumi-User anlegen
- `justfile` - muss Services als kodosumi ausführen
- Dokumentation - muss Host/VM User-Trennung erklären

---

## Container-Modus Test: ERFOLGREICH

| Datum | Zeit | Status |
|-------|------|--------|
| 2025-12-11 | 15:00 UTC | ✅ Container laufen |

### Durchgeführte Schritte für Container-Modus

1. **Podman Rootless konfiguriert:**
   ```bash
   sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 zimmermannb
   podman system migrate
   ```

2. **Image gepullt:**
   ```bash
   podman login ghcr.io -u basteiz
   podman pull ghcr.io/plan-net/claude-hitl-worker:latest
   ```

3. **Ray Version angepasst (VM → Container-kompatibel):**
   ```bash
   pip install ray==2.51.1  # Muss Container-Version matchen
   ```

4. **YAML mit CONTAINER_IMAGE_URI aktualisiert:**
   ```yaml
   CONTAINER_IMAGE_URI: "ghcr.io/plan-net/claude-hitl-worker:latest"
   ```

5. **Permissions gefixt (Workaround):**
   ```bash
   chmod -R 777 /tmp/ray/
   ```
   **WICHTIG:** Muss nach JEDEM Ray-Neustart ausgeführt werden!

6. **HITL Session gestartet → Container läuft!**

### Temporärer Workaround für Justfile

Bis der `kodosumi` User implementiert ist, kann dieser Workaround ins Justfile:

```just
# Ray starten mit Permission-Fix
start-ray:
    ray start --head --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265
    sleep 2
    chmod -R 777 /tmp/ray/
    echo "Ray gestartet + Permissions gefixt"
```

**Permanente Lösung:** Dedizierter `kodosumi` User mit UID 1000 (siehe Inkonsistenz #12)

---

## Test: kodosumi User + Docker Runtime (2025-12-11 15:39)

### Schritt 1: User anlegen
```bash
orb -m ray-cluster bash -c "sudo useradd -u 1000 -m -s /bin/bash kodosumi"
orb -m ray-cluster bash -c "sudo usermod -aG docker,sudo kodosumi"
```
**Ergebnis:** `uid=1000(kodosumi) gid=1000(kodosumi) groups=1000(kodosumi),27(sudo),104(docker)`

### Schritt 2: Projekt kopieren
```bash
orb -m ray-cluster bash -c "sudo bash -c 'mkdir -p /home/kodosumi/dev && cp -r /home/zimmermannb/dev/cc-hitl-template /home/kodosumi/dev/ && chown -R kodosumi:kodosumi /home/kodosumi'"
```

### Schritt 3: Frisches venv erstellen (WICHTIG: nicht kopieren!)
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && rm -rf .venv && python3.12 -m venv .venv'"
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install -e . sniffio ray==2.51.1 -q'"
```

### Schritt 4: Ray mit Docker-Runtime starten
```bash
# WICHTIG: RAY_CONTAINER_RUNTIME=docker setzen!
orb -m ray-cluster bash -c "sudo rm -rf /tmp/ray"
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'export RAY_CONTAINER_RUNTIME=docker && cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && ray start --head --port=6379 --dashboard-host=0.0.0.0 --dashboard-port=8265'"
```

### Schritt 5: Anwendung deployen
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'export RAY_CONTAINER_RUNTIME=docker && cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"
```

### Schritt 6: koco Services starten
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && .venv/bin/koco spool &'"
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && .venv/bin/koco serve --register http://localhost:8000/-/routes &'"
```

### Warum Docker statt Podman?

| Aspekt | Podman Rootless | Docker Daemon |
|--------|-----------------|---------------|
| Image-Storage | Pro User isoliert | Shared zwischen Usern |
| UID-Mapping | Kompliziert (subuid/subgid) | Root-basiert, einfacher |
| kodosumi Zugriff | Braucht eigenen Image-Pull | Nutzt existierendes Image |

**Fazit:** Docker ist für Multi-User-Setups einfacher als Podman Rootless.

### Zusätzliche Schritte (gefunden während Test)

**Problem:** Ray verwendet trotz `RAY_CONTAINER_RUNTIME=docker` weiterhin Podman!

**Schritt 7: Podman Login für kodosumi**
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'echo ghp_TOKEN | podman login ghcr.io -u USERNAME --password-stdin'"
```

**Schritt 8: Image als kodosumi pullen**
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi podman pull ghcr.io/plan-net/claude-hitl-worker:latest"
```

**Schritt 9: Lingering aktivieren (für systemd cgroups)**
```bash
orb -m ray-cluster bash -c "sudo loginctl enable-linger 1000"
```

### Erkenntnis: RAY_CONTAINER_RUNTIME wird ignoriert

Ray's Runtime-Env-Agent verwendet **immer** den Default Container-Runtime (Podman auf diesem System).
Die Umgebungsvariable `RAY_CONTAINER_RUNTIME=docker` wird nicht berücksichtigt.

**→ kodosumi muss Zugriff auf Podman-Images haben!**

---

## ✅ LÖSUNG VERIFIZIERT: systemd Services + kodosumi User (2025-12-11 16:06)

### Erfolgreicher Test

Container läuft als `kodosumi` User **OHNE chmod Workarounds!**

```bash
$ sudo -u kodosumi podman ps -a
CONTAINER ID  IMAGE                                       STATUS        NAMES
efe09de80311  ghcr.io/plan-net/claude-hitl-worker:latest  Up 2 minutes  wizardly_spence
```

### Root Cause bestätigt

| Vorher | Nachher |
|--------|---------|
| VM User: zimmermannb (UID 1792997461) | VM User: kodosumi (UID 1000) |
| Container User: ray (UID 1000) | Container User: ray (UID 1000) |
| **UID Mismatch → chmod 777 nötig** | **UIDs matchen → keine Workarounds** |

### Implementierte systemd Services

**1. kodosumi-ray.service**
```ini
[Unit]
Description=Ray Head Node Service
After=network.target

[Service]
User=kodosumi
WorkingDirectory=/home/kodosumi/dev/cc-hitl-template
Type=simple
Environment=RAY_LOG_TO_DRIVER=0
Environment=RAY_BACKEND_LOG_LEVEL=warning
ExecStart=/home/kodosumi/dev/cc-hitl-template/.venv/bin/ray start --head --port=6379 --dashboard-host=0.0.0.0 --block
ExecStop=/home/kodosumi/dev/cc-hitl-template/.venv/bin/ray stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**2. kodosumi-koco-spool.service**
```ini
[Unit]
Description=Kodosumi Spooler Service
After=network.target

[Service]
User=kodosumi
WorkingDirectory=/home/kodosumi/dev/cc-hitl-template
Type=simple
ExecStart=/home/kodosumi/dev/cc-hitl-template/.venv/bin/koco spool --block
ExecStop=/home/kodosumi/dev/cc-hitl-template/.venv/bin/koco spool --stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. kodosumi-koco-serve.service**
```ini
[Unit]
Description=Kodosumi Serve Service
After=kodosumi-ray.service
Requires=kodosumi-ray.service

[Service]
User=kodosumi
WorkingDirectory=/home/kodosumi/dev/cc-hitl-template
Type=simple
ExecStart=/home/kodosumi/dev/cc-hitl-template/.venv/bin/koco serve --register http://localhost:8000/-/routes
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Wichtige Erkenntnisse

1. **`--block` Flag ist kritisch** für Ray und koco spool:
   - Ohne `--block`: Service forkt sich und systemd verliert Tracking
   - Mit `--block`: Service bleibt im Vordergrund, systemd kann korrekt verwalten

2. **Application muss manuell deployed werden** nach Ray-Start:
   ```bash
   sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'
   ```

3. **Podman Rootless Storage ist pro User isoliert:**
   - zimmermannb's Images: `~/.local/share/containers/storage/`
   - kodosumi's Images: `/home/kodosumi/.local/share/containers/storage/`
   - **→ kodosumi muss eigenes `podman pull` ausführen!**

### Service-Management Befehle

```bash
# Status prüfen
sudo systemctl status kodosumi-ray kodosumi-koco-spool kodosumi-koco-serve

# Alle stoppen
sudo systemctl stop kodosumi-koco-serve kodosumi-koco-spool kodosumi-ray

# Alle starten (Reihenfolge wichtig!)
sudo systemctl start kodosumi-ray
sleep 5
# App deployen (manuell)
sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'
sudo systemctl start kodosumi-koco-spool kodosumi-koco-serve

# Logs prüfen
sudo journalctl -u kodosumi-ray -f
sudo journalctl -u kodosumi-koco-spool -f
```

### Offene Verbesserungen

1. [ ] Application-Deployment als eigenen Service oder in ray-Service integrieren
2. [ ] setup-vm.sh um kodosumi-User und systemd-Services erweitern
3. [ ] Dokumentation für Production-Deployment erstellen
