# VM Setup Protokoll

> Dokumentation der manuellen VM-Einrichtung mit Quellenangaben
> Erstellt: 2025-12-11

---

## Übersicht

| Aspekt | Wert |
|--------|------|
| VM Name | `ray-cluster` |
| OS | Ubuntu 24.04 (Noble Numbat) |
| Architektur | arm64 |
| IP | 192.168.139.129 |
| Projekt-Verzeichnis | `~/dev/cc-hitl-template` |

---

## Installierte Software

| Software | Version | Quelle |
|----------|---------|--------|
| Docker | 28.2.2 | setup-vm.sh (Zeile 85) |
| Podman | 4.9.3 | MARKUS_TROUBLESHOOTING.md (Zeilen 181-190) |
| Python | 3.12.3 | setup-vm.sh (Zeile 99) |
| Node.js | v18.20.8 | setup-vm.sh (Zeilen 111-123) |
| Claude CLI | 2.0.65 | setup-vm.sh (Zeile 128) |
| Git | 2.43.0 | setup-vm.sh (Zeile 138) |
| rsync | 3.2.7 | setup-vm.sh (Zeile 138) |

---

## Ausgeführte Schritte (mit Quellenangaben)

### Schritt 1-2: VM Erstellung
```
QUELLE: setup-vm.sh (Zeilen 45-80)
BEFEHL: orb create ubuntu:noble ray-cluster
```

### Schritt 3a: System Update
```
QUELLE: setup-vm.sh (Zeile 85)
BEFEHL: sudo apt-get update -qq
```

### Schritt 3b: Docker Installation
```
QUELLE: setup-vm.sh (Zeile 85)
PFAD:   ~/.claude/plugins/cache/cc-marketplace-developers/
        claude-agent-sdk/2.1.1/skills/vm-setup/scripts/setup-vm.sh
BEFEHL: sudo apt-get install -y docker.io
        sudo usermod -aG docker $USER
```

### Schritt 3c: Podman Installation (ZUSÄTZLICH)
```
QUELLE: MARKUS_TROUBLESHOOTING.md (Zeilen 181-190)
PFAD:   ~/Downloads/MARKUS_TROUBLESHOOTING.md
ZITAT:  'orb -m ray-cluster bash -c "podman login ghcr.io..."'
        'orb -m ray-cluster bash -c "podman pull ghcr.io/..."'
BEFEHL: sudo apt-get install -y podman

⚠️  INKONSISTENZ: Plugin-Script installiert Docker, aber
    Troubleshooting-Doc verwendet Podman-Befehle!
```

### Schritt 4: Python 3.12 + Tools
```
QUELLE: setup-vm.sh (Zeile 99)
BEFEHL: sudo apt-get install -y python3.12-venv python3-pip
HINWEIS: Python 3.12.3 war bereits vorinstalliert (Ubuntu 24.04 default)
```

### Schritt 5: Node.js 18
```
QUELLE: setup-vm.sh (Zeilen 111-123)
BEFEHL: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
```

### Schritt 6: Claude CLI
```
QUELLE: setup-vm.sh (Zeile 128)
BEFEHL: sudo npm install -g @anthropic-ai/claude-code
HINWEIS: Als "non-critical" markiert (Zeile 132)
```

### Schritt 6.5: Utilities
```
QUELLE: setup-vm.sh (Zeile 138)
BEFEHL: sudo apt-get install -y rsync git
HINWEIS: Git wurde bereits als docker.io Dependency installiert
```

### Schritt 7: Projekt-Verzeichnis
```
QUELLE: setup-vm.sh (Zeile 144)
VARIABLE: PROJECT_DIR='~/dev/cc-hitl-template' (Zeile 26)
BEFEHL: mkdir -p ~/dev/cc-hitl-template
```

---

## Gefundene Inkonsistenzen

### INKONSISTENZ #1: Docker vs Podman

| Quelle | Container Runtime |
|--------|-------------------|
| `setup-vm.sh` (Plugin) | Docker (`docker.io`) |
| `MARKUS_TROUBLESHOOTING.md` | Podman |
| Ray Serve Container | ??? (unklar) |

**Details:**
- Das Plugin-Script (`setup-vm.sh`) installiert ausschließlich Docker
- Das Troubleshooting-Dokument verwendet ausschließlich Podman-Befehle:
  - `podman login ghcr.io`
  - `podman pull ghcr.io/...`
  - `podman run --rm ...`
  - `podman ps -a`
  - `podman images`

**Fragen:**
1. Welche Runtime verwendet Ray Serve tatsächlich für Container?
2. Ist Docker-Podman-Kompatibilität gewährleistet?
3. Warum unterscheiden sich Plugin und Troubleshooting-Doc?

**Entscheidung:** Beide installiert für maximale Kompatibilität.

---

### INKONSISTENZ #2: Fehlende Ray Installation in VM-Setup

| Quelle | Ray Installation |
|--------|------------------|
| `setup-vm.sh` (Plugin) | ❌ Nicht erwähnt! |
| `MARKUS_TROUBLESHOOTING.md` | ✅ Ray 2.51.1 erwartet |

**Details:**
- Das `setup-vm.sh` Script installiert Ray NICHT in der VM
- Das Troubleshooting-Doc prüft Ray-Versionen:
  ```bash
  orb -m ray-cluster bash -c "source ~/.venv/bin/activate && python -c 'import ray; print(ray.__version__)'"
  ```
- Es wird erwartet, dass Ray in `.venv` installiert ist

**Frage:** Wo wird Ray in der VM installiert? Vermutlich später via `pip install -e .`?

---

### INKONSISTENZ #3: venv Erstellung

| Quelle | venv Pfad |
|--------|-----------|
| `setup-vm.sh` (Zeile 181) | `~/dev/cc-hitl-template/.venv` (im Projekt) |
| `MARKUS_TROUBLESHOOTING.md` | `~/.venv` (im Home-Verzeichnis) |

**Details:**
- Plugin-Script schlägt vor:
  ```bash
  cd ~/dev/cc-hitl-template && python3.12 -m venv .venv
  ```
- Troubleshooting-Doc verwendet:
  ```bash
  source ~/.venv/bin/activate
  ```

**Frage:** Welcher Pfad ist korrekt? Hat Auswirkungen auf Ray-Installation.

---

## Nächste Schritte (laut setup-vm.sh Zeilen 173-185)

1. **Code zur VM synchronisieren:**
   ```bash
   rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
     ./ ray-cluster@orb:~/dev/cc-hitl-template/
   ```

2. **.env zur VM kopieren:**
   ```bash
   scp .env ray-cluster@orb:~/dev/cc-hitl-template/.env
   ```

3. **Python venv in VM einrichten:**
   ```bash
   orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && python3.12 -m venv .venv"
   orb -m ray-cluster bash -c "cd ~/dev/cc-hitl-template && source .venv/bin/activate && pip install -e ."
   ```

4. **Ray Cluster starten:**
   ```bash
   just orb-start
   ```

---

## Offene Fragen für weitere Analyse

1. [ ] Welche Container Runtime (Docker/Podman) wird tatsächlich von Ray verwendet?
2. [ ] Warum ist Ray nicht im VM-Setup Script enthalten?
3. [ ] Welcher venv-Pfad ist der richtige (`~/.venv` vs `~/dev/cc-hitl-template/.venv`)?
4. [ ] Wird der justfile-Befehl `orb-start` die fehlende Ray-Installation nachholen?
5. [ ] Wie werden Docker/Podman Registry-Authentifizierungen persistiert?
