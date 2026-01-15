# VM Setup Briefing: Kodosumi + Ray + Container

> Getestete Anleitung zur Einrichtung einer OrbStack VM für containerisierten HITL-Betrieb
> Stand: 2025-12-17 (aktualisiert: kodosumi feature/candidate)

---

## ⚠️ WICHTIG: Container Image Herkunft

**Für lokale Entwicklung** muss das Container Image in **deinem eigenen** GitHub Container Registry liegen!

**Workflow:**
1. **Lokal bauen**: `/cc-deploy` → `build.sh` → `Dockerfile`
2. **Push zu deinem Registry**: `ghcr.io/<DEIN_GITHUB_USERNAME>/claude-hitl-worker:latest`
3. **VM pullt von deinem Registry**: Nicht von `plan-net`!

**Warum?**
- Du baust dein eigenes Image mit deiner Konfiguration
- Du hast Kontrolle über Versionen und Änderungen
- `plan-net` Images sind nur für Produktions-/Team-Deployments

**Voraussetzung**: `GITHUB_USERNAME` und `GITHUB_TOKEN` in `.env` korrekt gesetzt.

---

## Voraussetzungen (Host/Mac)

- OrbStack installiert
- Zugang zu ghcr.io (GitHub Token)
- Projekt-Repository geklont: `~/git/cc-hitl-template`

---

## Phase 1: VM erstellen

```bash
# VM erstellen (Ubuntu 24.04, ARM64)
orb create ubuntu:noble ray-cluster

# Verifizieren
orb list
```

---

## Phase 2: Basis-Software installieren

```bash
# System Update
orb -m ray-cluster bash -c "sudo apt-get update -qq"

# Python 3.12 Tools
orb -m ray-cluster bash -c "sudo apt-get install -y python3.12-venv python3-pip"

# Podman (Container Runtime - wird von Ray verwendet)
orb -m ray-cluster bash -c "sudo apt-get install -y podman"

# Node.js 18 (für Claude CLI)
orb -m ray-cluster bash -c "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"

# rsync + git
orb -m ray-cluster bash -c "sudo apt-get install -y rsync git"
```

---

## Phase 3: kodosumi Service-User anlegen (UID 1000)

**KRITISCH:** Der User muss UID 1000 haben, damit Container-Permissions funktionieren!

```bash
# User anlegen mit UID 1000
orb -m ray-cluster bash -c "sudo useradd -u 1000 -m -s /bin/bash kodosumi"

# Gruppen hinzufügen
orb -m ray-cluster bash -c "sudo usermod -aG sudo kodosumi"

# Verifizieren
orb -m ray-cluster bash -c "id kodosumi"
# Erwartete Ausgabe: uid=1000(kodosumi) gid=1000(kodosumi) groups=1000(kodosumi),27(sudo)
```

---

## Phase 4: Podman für kodosumi konfigurieren

```bash
# subuid/subgid für Rootless Podman
orb -m ray-cluster bash -c "sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 kodosumi"

# Lingering aktivieren (für systemd cgroups)
orb -m ray-cluster bash -c "sudo loginctl enable-linger kodosumi"
```

---

## Phase 5: Projekt-Verzeichnis einrichten

```bash
# Verzeichnis erstellen
orb -m ray-cluster bash -c "sudo mkdir -p /home/kodosumi/dev"

# Projekt vom Host synchronisieren
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.pyc' \
  ~/git/cc-hitl-template/ ray-cluster@orb:/home/kodosumi/dev/cc-hitl-template/

# Ownership setzen
orb -m ray-cluster bash -c "sudo chown -R kodosumi:kodosumi /home/kodosumi"
```

---

## Phase 6: Python venv erstellen + serve Symlink

**WICHTIG:** Kodosumi erwartet `serve` im PATH. Symlink erstellen:

```bash
# venv erstellen (als kodosumi)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && python3.12 -m venv .venv'"

# Dependencies installieren (inkl. Ray 2.51.1)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install -e . sniffio ray==2.51.1 -q'"

# Kodosumi feature/candidate Branch installieren (WICHTIG!)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install git+https://github.com/masumi-network/kodosumi.git@feature/candidate -q'"

# Ray Version zurücksetzen (kodosumi zieht evtl. neuere Ray-Version!)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install ray==2.51.1 -q'"

# Verifizieren
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'source /home/kodosumi/dev/cc-hitl-template/.venv/bin/activate && ray --version && pip show kodosumi | grep Version'"
# Erwartete Ausgabe:
# ray, version 2.51.1
# Version: 1.1.0

# serve Symlink erstellen (Kodosumi Bug-Workaround)
orb -m ray-cluster bash -c "sudo chmod o+x /home/kodosumi && sudo chmod -R o+rX /home/kodosumi/dev"
orb -m ray-cluster bash -c "sudo ln -sf /home/kodosumi/dev/cc-hitl-template/.venv/bin/serve /usr/local/bin/serve"

# Symlink verifizieren
orb -m ray-cluster bash -c "serve --help | head -1"
# Erwartete Ausgabe: Usage: serve [OPTIONS] COMMAND [ARGS]...
```

---

## Phase 7: Container-Image pullen (als kodosumi)

**WICHTIG**: Ersetze `<GITHUB_USERNAME>` und `<GITHUB_TOKEN>` mit deinen Werten aus `.env`!

```bash
# Podman Login (GITHUB_TOKEN und GITHUB_USERNAME aus .env)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'echo <GITHUB_TOKEN> | podman login ghcr.io -u <GITHUB_USERNAME> --password-stdin'"

# Image pullen (DEIN eigenes Image, nicht plan-net!)
orb -m ray-cluster bash -c "sudo -u kodosumi podman pull ghcr.io/<GITHUB_USERNAME>/claude-hitl-worker:latest"

# Verifizieren
orb -m ray-cluster bash -c "sudo -u kodosumi podman images"
```

**Beispiel** (wenn GITHUB_USERNAME=zimmermannb):
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi podman pull ghcr.io/zimmermannb/claude-hitl-worker:latest"
```

---

## Phase 8: systemd Services erstellen

### 8.1 Ray Service

```bash
orb -m ray-cluster bash -c 'cat > /tmp/kodosumi-ray.service << EOF
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
EOF
sudo mv /tmp/kodosumi-ray.service /etc/systemd/system/'
```

### 8.2 Koco Spool Service

```bash
orb -m ray-cluster bash -c 'cat > /tmp/kodosumi-koco-spool.service << EOF
[Unit]
Description=Kodosumi Spooler Service
After=kodosumi-ray.service
Requires=kodosumi-ray.service

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
EOF
sudo mv /tmp/kodosumi-koco-spool.service /etc/systemd/system/'
```

### 8.3 Koco Serve Service

```bash
orb -m ray-cluster bash -c 'cat > /tmp/kodosumi-koco-serve.service << EOF
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
EOF
sudo mv /tmp/kodosumi-koco-serve.service /etc/systemd/system/'
```

### 8.4 Services aktivieren

```bash
orb -m ray-cluster bash -c "sudo systemctl daemon-reload && sudo systemctl enable kodosumi-ray kodosumi-koco-spool kodosumi-koco-serve"
```

---

## Phase 9: Services starten

```bash
# 1. Ray starten
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-ray"

# 2. Warten bis Ray bereit ist (5 Sekunden)
sleep 5

# 3. Application deployen (MANUELL - nicht als Service)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"

# 4. Koco Services starten
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-koco-spool kodosumi-koco-serve"

# 5. Status prüfen
orb -m ray-cluster bash -c "sudo systemctl status kodosumi-ray kodosumi-koco-spool kodosumi-koco-serve --no-pager | grep -E '(●|○|Active)'"
```

**Erwartete Ausgabe:**
```
● kodosumi-ray.service - Ray Head Node Service
     Active: active (running)
● kodosumi-koco-spool.service - Kodosumi Spooler Service
     Active: active (running)
● kodosumi-koco-serve.service - Kodosumi Serve Service
     Active: active (running)
```

---

## Phase 10: Verifizierung

### 10.1 Ray Dashboard
```bash
curl -s http://192.168.139.129:8265 | head -5
# Sollte HTML zurückgeben
```

### 10.2 Ray Serve Routes
```bash
orb -m ray-cluster bash -c "curl -s http://localhost:8000/-/routes"
# Erwartete Ausgabe: {"/feeling-check":"claude_hitl_template"}
```

### 10.3 Kodosumi Panel
```bash
orb -m ray-cluster bash -c "curl -s http://localhost:3370/-/routes"
# Erwartete Ausgabe: {"error":"NotAuthorizedException"...} (401 = OK, Service läuft)
```

---

## Phase 11: HITL Test (Container-Modus)

```bash
# Test-Request starten (vom Host)
curl -X POST "http://192.168.139.129:8000/feeling-check" \
  -H "Content-Type: application/json" \
  -d '{"name":"VM-Test","question":"Funktioniert alles?"}'
```

### Container prüfen (während Test läuft)
```bash
orb -m ray-cluster bash -c "sudo -u kodosumi podman ps"
```

**Erwartete Ausgabe:**
```
CONTAINER ID  IMAGE                                              STATUS        NAMES
xxxxxxxx      ghcr.io/<GITHUB_USERNAME>/claude-hitl-worker:latest  Up X minutes  some_name
```

---

## Troubleshooting

### Service-Logs prüfen
```bash
orb -m ray-cluster bash -c "sudo journalctl -u kodosumi-ray -n 50 --no-pager"
orb -m ray-cluster bash -c "sudo journalctl -u kodosumi-koco-spool -n 50 --no-pager"
orb -m ray-cluster bash -c "sudo journalctl -u kodosumi-koco-serve -n 50 --no-pager"
```

### Ray Logs prüfen
```bash
orb -m ray-cluster bash -c "tail -50 /tmp/ray/session_latest/logs/serve/controller*.log"
```

### Alle Services neustarten
```bash
orb -m ray-cluster bash -c "sudo systemctl stop kodosumi-koco-serve kodosumi-koco-spool kodosumi-ray"
orb -m ray-cluster bash -c "sudo rm -rf /tmp/ray"
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-ray"
sleep 5
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && serve deploy data/config/claude_hitl_template.yaml'"
orb -m ray-cluster bash -c "sudo systemctl start kodosumi-koco-spool kodosumi-koco-serve"
```

---

## Wichtige Erkenntnisse

1. **UID 1000 ist kritisch** - Container laufen als `ray` (UID 1000), VM-Services müssen auch UID 1000 haben
2. **`--block` Flag** - Ray und koco spool brauchen `--block` für systemd Type=simple
3. **Podman Rootless** - Storage ist pro User isoliert, kodosumi braucht eigenen Image-Pull
4. **RAY_CONTAINER_RUNTIME wird ignoriert** - Ray verwendet immer Podman (auf diesem System)
5. **Application-Deployment** - Muss manuell nach Ray-Start erfolgen (nicht als Service)
6. **Kodosumi feature/candidate** - Verwende `git+https://github.com/masumi-network/kodosumi.git@feature/candidate` für die aktuelle Version (1.1.0)
7. **Ray Version pinnen** - Nach kodosumi-Install immer `pip install ray==2.51.1` ausführen (kodosumi überschreibt sonst Ray-Version!)
8. **serve Symlink** - Kodosumi erwartet `serve` im PATH → Symlink nach `/usr/local/bin/serve` erstellen

---

## Kodosumi Update (ohne Ray-Neustart)

Falls nur Kodosumi aktualisiert werden soll:

```bash
# Kodosumi updaten
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install --force-reinstall git+https://github.com/masumi-network/kodosumi.git@feature/candidate -q'"

# WICHTIG: Ray Version zurücksetzen (kodosumi überschreibt evtl. Ray!)
orb -m ray-cluster bash -c "sudo -u kodosumi bash -c 'cd /home/kodosumi/dev/cc-hitl-template && source .venv/bin/activate && pip install ray==2.51.1 -q'"

# Koco Services neustarten (Ray bleibt laufen)
orb -m ray-cluster bash -c "sudo systemctl restart kodosumi-koco-spool kodosumi-koco-serve"

# Verifizieren
orb -m ray-cluster bash -c "sudo systemctl status kodosumi-koco-spool kodosumi-koco-serve --no-pager | grep Active"
```
