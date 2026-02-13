# CloudStash – Entwicklungsstatus & Übergabedokumentation

Dieses Dokument fasst den aktuellen Stand des Projekts zusammen, damit die Arbeit in einem neuen, eigenständigen Repository nahtlos fortgesetzt werden kann.

---

## 1. Projektübersicht

**Name:** CloudStash – S3 Compatible Backup for Home Assistant
**Domain:** `cloudstash`
**Version:** 0.1.5
**Mindestversion HA:** 2025.2.0
**Abhängigkeit:** `aiobotocore>=2.6.0,<3.0.0`
**Codeowner:** `@derolli1976`
**Lizenz:** bestehende LICENSE-Datei (unverändert)

### Was macht die Integration?

CloudStash ist ein Home Assistant `BackupAgent`, der Backups in jedem S3-kompatiblen Objektspeicher ablegt (AWS S3, MinIO, Wasabi, Backblaze B2, DigitalOcean Spaces, Cloudflare R2, Synology C2, Garage, etc.). Die Integration erscheint unter **Einstellungen → System → Backups** als Backup-Ziel.

---

## 2. Dateistruktur

```
├── .github/
│   └── workflows/
│       ├── hacs.yml              # HACS-Validierung
│       └── hassfest.yml          # HA hassfest-Validierung
├── custom_components/
│   └── cloudstash/
│       ├── __init__.py           # Entry setup, ObjectStorageGateway (Worker-Thread-Proxy)
│       ├── backup.py             # CloudStashAgent (BackupAgent-Implementierung)
│       ├── config_flow.py        # CloudStashConfigFlow (Setup/Reauth/Reconfigure)
│       ├── const.py              # Konstanten (DOMAIN, Config-Keys, Defaults)
│       ├── manifest.json         # Integration-Manifest
│       ├── strings.json          # Englische UI-Texte (Quelle)
│       └── translations/
│           ├── de.json           # Deutsche Übersetzung
│           └── en.json           # Englische Übersetzung
├── hacs.json                     # HACS-Konfiguration
├── icon.svg                      # CloudStash-Icon (ohne Text)
├── logo.svg                      # CloudStash-Logo (mit Text)
├── CHANGELOG.md                  # Bisheriger Changelog (deutsch)
├── README.md                     # Englische Doku
├── README_DE.md                  # Deutsche Doku
├── RELEASE.md                    # Release-Prozess-Doku
├── release.py                    # Release-Automatisierung (Version bump, Tag, Push, GH Release)
├── LICENSE
├── .gitignore
└── .gitattributes
```

---

## 3. Architektur

### 3.1 ObjectStorageGateway (`__init__.py`)

- Startet einen **dedizierten Worker-Thread** mit eigenem `asyncio`-Event-Loop
- Alle S3-Aufrufe werden per `asyncio.run_coroutine_threadsafe()` dorthin dispatched
- **Grund:** botocore führt beim Client-Setup blockierende Dateisystem-Operationen aus (CA-Bundle laden, Data-Model-Dateien lesen), die den HA-Event-Loop blockieren würden
- Lifecycle: `launch()` (blocking, via Executor) → `shutdown()` (blocking, via Executor)
- Keyword-only `__init__` mit: `endpoint`, `key_id`, `secret`, `region`, `bucket`
- Interne Methode `_run()` bridged Coroutines zum Worker-Loop

### 3.2 CloudStashAgent (`backup.py`)

- Implementiert `BackupAgent` (upload, download, list, get, delete)
- **Upload-Strategie:**
  - < 20 MiB → `_put_single()` (einfacher PutObject)
  - ≥ 20 MiB → `_put_chunked()` (Multipart-Upload, gleichgroße Parts für R2-Kompatibilität)
- **Listing-Cache:** `_fetch_listing()` mit `monotonic()`-basiertem TTL (300s)
- Metadaten werden als `.metadata.json`-Sidecar-Dateien im selben Prefix gespeichert
- Decorator `_wrap_storage_errors` übersetzt `BotoCoreError` → `BackupAgentError`

### 3.3 CloudStashConfigFlow (`config_flow.py`)

- **3 Steps:** `user` (Setup), `reauth_confirm` (Re-Authentifizierung), `reconfigure`
- Validierung via `_probe_connection()` – HeadBucket in wegwerf-Event-Loop, läuft im Executor
- Validierungslogik zentralisiert in `_try_connect()` (gibt Error-Dict zurück)
- Duplikat-Erkennung per Bucket+Endpoint-Kombination
- 3 Schema-Konstanten: `SCHEMA_SETUP`, `SCHEMA_CREDENTIALS`, `SCHEMA_FULL_EDIT`

### 3.4 Konstanten (`const.py`)

| Konstante | Wert | Zweck |
|---|---|---|
| `DOMAIN` | `"cloudstash"` | Integration Domain |
| `OPT_KEY_ID` | `"access_key_id"` | Config-Entry-Key |
| `OPT_SECRET` | `"secret_access_key"` | Config-Entry-Key |
| `OPT_ENDPOINT` | `"endpoint_url"` | Config-Entry-Key |
| `OPT_BUCKET` | `"bucket"` | Config-Entry-Key |
| `OPT_REGION` | `"region"` | Config-Entry-Key |
| `OPT_OBJECT_PREFIX` | `"prefix"` | Config-Entry-Key |
| `FALLBACK_REGION` | `"us-east-1"` | Standard-Region |
| `FALLBACK_PREFIX` | `"homeassistant"` | Standard-Prefix |
| `STORAGE_DIR` | `"backups"` | Unterordner im Bucket |
| `AGENT_LISTENER_KEY` | HassKey | Interne Listener-Registry |

---

## 4. Was wurde gemacht (chronologisch)

### Phase 1 – Code-Review & Best-Practices
- HACS-Workflows (`hacs.yml`, `hassfest.yml`) aktiviert
- `manifest.json` bereinigt (`quality_scale` entfernt, da nicht in Custom Integrations unterstützt)
- Busy-Wait (`while self._loop is None: pass`) durch `threading.Event` ersetzt
- `ConnectionError`-Import-Shadowing behoben (→ `BotoConnectionError` Alias)
- Cache-Invalidierung in eigene Methode extrahiert
- Config-Flow modernisiert (`_get_reauth_entry()` statt gespeicherter Instanzvariable)
- Übersetzungen vervollständigt (en + de, inkl. `data_description`)

### Phase 2 – Rebranding
- Domain: `bauergroup_s3compatiblebackup` → `cloudstash`
- Verzeichnis: `custom_components/bauergroup_s3compatiblebackup/` → `custom_components/cloudstash/`
- Alle Dateien aktualisiert (manifest.json, hacs.json, const.py, etc.)

### Phase 3 – Repository-Links
- Alle Links von `bauer-group/IP-HomeassistantS3CompatibleBackup` auf `derolli1976/HomeassistantS3CompatibleBackup` umgestellt
- Interne Bauer-Group-Workflows gelöscht (`teams-notifications.yml`, `ai-issue-summary.yml`)
- Altes Verzeichnis `bauergroup_s3compatiblebackup` gelöscht

### Phase 4 – Dokumentation
- README.md und README_DE.md komplett neu geschrieben
- Keine Emojis, kein KI-typisches Format
- Provider-Anleitungen durch kompakte Endpoint-Referenztabelle ersetzt
- HACS-Badge und my.home-assistant.io-Button integriert

### Phase 5 – Branding
- `logo.svg` erstellt (Wolke + Upload-Pfeil + Häkchen + "CloudStash"-Text)
- `icon.svg` erstellt (gleich, ohne Text)

### Phase 6 – Code-Differenzierung
Komplette Umstrukturierung aller 4 Python-Dateien, damit der Code nicht mehr als Fork des Originals erkennbar ist:

| Bereich | Vorher (Original) | Nachher (CloudStash) |
|---|---|---|
| Hauptklasse | `S3ClientWrapper` | `ObjectStorageGateway` |
| Config-Entry-Typ | `S3CompatibleConfigEntry` | `CloudStashEntry` |
| Backup-Agent | `S3CompatibleBackupAgent` | `CloudStashAgent` |
| Config-Flow | `S3CompatibleConfigFlow` | `CloudStashConfigFlow` |
| Worker-Start/Stop | `start()` / `stop()` | `launch()` / `shutdown()` |
| Worker-Thread | `_run_worker_loop()` | `_thread_main()` |
| Client erstellen/schließen | `_create_client()` / `_close_client()` | `_open()` / `_close()` |
| Dispatch | `_dispatch()` | `_run()` |
| Client-Handle | `_client` | `_handle` |
| Event-Flag | `_loop_ready` | `_ready` |
| Status-Flag | `_started` | `_running` |
| Logger | `_LOGGER` | `_LOG` |
| Error-Decorator | `handle_boto_errors` | `_wrap_storage_errors` |
| Dateinamen-Helper | `suggested_filenames()` | `_derive_object_names()` |
| Backup suchen | `_find_backup_by_id()` | `_resolve()` |
| Prefix bauen | `_build_prefix()` | `_resolve_root()` (staticmethod) |
| Key bauen | `_get_key()` | `_key()` |
| Upload klein | `_upload_simple()` | `_put_single()` |
| Upload groß | `_upload_multipart()` | `_put_chunked()` |
| Listing | `_list_backups()` | `_fetch_listing()` |
| Cache invalidieren | `_invalidate_cache()` | `_drop_cache()` |
| Cache-Variablen | `_backup_cache` / `_cache_expiration` | `_listing` / `_listing_valid_until` |
| S3-Gateway-Ref | `_client` | `_gw` |
| Prefix-Ref | `_prefix` | `_root` |
| TTL-Konstante | `CACHE_TTL` | `LISTING_CACHE_SECONDS` |
| Part-Size-Konstante | `MULTIPART_MIN_PART_SIZE_BYTES` | `CHUNK_THRESHOLD_BYTES` |
| Validierung | `_validate_s3_credentials()` | `_probe_connection()` |
| Schema-Namen | `STEP_USER_DATA_SCHEMA` etc. | `SCHEMA_SETUP` etc. |
| Config-Konstanten | `CONF_ACCESS_KEY_ID` etc. | `OPT_KEY_ID` etc. |
| Default-Konstanten | `DEFAULT_REGION` etc. | `FALLBACK_REGION` etc. |
| Listener-Key | `DATA_BACKUP_AGENT_LISTENERS` | `AGENT_LISTENER_KEY` |
| Zeit-Quelle (Cache) | `time()` | `monotonic()` |
| `__init__` Argumente | positional | keyword-only (`*`) |
| Validierungs-Pattern | try/except in jedem Step dupliziert | zentralisiert in `_try_connect()` |
| TextSelector | inline in jedem Schema | vordefinierte `_PASSWORD` / `_URL` Konstanten |

---

## 5. Offene Punkte / Nächste Schritte

### Beim Umzug ins neue Repository

1. **Neues GitHub-Repo erstellen** (z.B. `derolli1976/cloudstash` o.ä.)
2. **Ohne Fork-Beziehung** – frisches `git init`, Dateien kopieren, initialen Commit machen
3. **Links in folgenden Dateien anpassen** (falls Repo-Name sich ändert):
   - `custom_components/cloudstash/manifest.json` → `documentation` und `issue_tracker`
   - `README.md` und `README_DE.md` → alle GitHub-Links, Badges, HACS-Button
   - `RELEASE.md` → GitHub-Links
   - `release.py` → GitHub-Links (Repo-Name ist dort hardcoded)
4. **GitHub Topics setzen:** `home-assistant`, `hacs`, `s3`, `backup`, `home-assistant-custom-component`
5. **CHANGELOG.md** – ggf. bereinigen/neu starten für das neue Repo

### Inhaltliche Weiterentwicklung

- **Tests:** Aktuell gibt es keine Unit-/Integrationstests. pytest + `pytest-homeassistant-custom-component` wäre der nächste logische Schritt.
- **Version bump:** Nächstes Release sollte die umfangreichen Refactoring-Änderungen widerspiegeln (z.B. 0.2.0).
- **Translations:** Weitere Sprachen bei Bedarf.
- **HACS Default-Repository:** Nach ausreichender Nutzung und Stabilität kann ein PR ans HACS-Default-Repo gestellt werden.

---

## 6. Build & Release

Das `release.py`-Skript automatisiert den Release-Prozess:

```bash
python release.py 0.2.0
```

Es aktualisiert die Version in `manifest.json`, erstellt Commit + Tag, pushed und erstellt ein GitHub Release (benötigt `gh` CLI).

---

## 7. Technische Anforderungen

- **Python:** 3.12+ (nutzt PEP 695 `type`-Statement)
- **Home Assistant:** 2025.2.0+
- **HACS:** Custom Repository, `render_readme: true`
- **aiobotocore:** >=2.6.0, <3.0.0

---

## 8. Schritte zum Umzug in ein neues Repository

```bash
# 1. Neuen Ordner vorbereiten
mkdir cloudstash && cd cloudstash
git init

# 2. Alle Dateien aus dem aktuellen Projekt kopieren (OHNE .git/)
#    Am besten: alles außer .git/ kopieren
robocopy "E:\Github\HomeassistantS3CompatibleBackup" . /E /XD .git

# 3. Diese Übergabedokumentation entfernen (wird nicht mehr gebraucht)
del DEVELOPMENT_STATUS.md

# 4. Links anpassen falls Repo-Name anders ist (Suchen+Ersetzen)
#    "derolli1976/HomeassistantS3CompatibleBackup" → "derolli1976/NEUER_NAME"

# 5. Initialer Commit
git add .
git commit -m "Initial commit – CloudStash v0.2.0"

# 6. Remote setzen und pushen
git remote add origin https://github.com/derolli1976/NEUER_NAME.git
git branch -M main
git push -u origin main

# 7. GitHub Topics setzen (im Browser oder via gh CLI)
gh repo edit --add-topic home-assistant,hacs,s3,backup,home-assistant-custom-component
```

---

*Erstellt am 13. Februar 2026*
