# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.0.0] - 2026-02-13

### Erste Veröffentlichung

Initiales Release von CloudStash als eigenständiges Projekt.

#### Backup-Agent

- S3-kompatibler Backup-Agent für Home Assistants eingebautes Backup-System
- Funktioniert mit jedem S3-kompatiblen Speicher (AWS S3, MinIO, Wasabi, Backblaze B2, DigitalOcean Spaces, Cloudflare R2, Synology C2, Garage u.a.)
- Upload, Download, Auflisten und Löschen von Backups
- Multipart-Upload für große Backups (>20 MB), gleichgroße Parts für R2-Kompatibilität
- Backup-Listing-Cache mit 5-Minuten TTL (monotonic-basiert)
- Metadaten als `.metadata.json`-Sidecar-Dateien im selben Prefix

#### Architektur

- `ObjectStorageGateway` – dedizierter Worker-Thread mit eigenem Event-Loop, vermeidet Blockierung des HA-Event-Loops durch botocore-I/O
- `CloudStashAgent` – vollständige `BackupAgent`-Implementierung
- `CloudStashConfigFlow` – Setup, Re-Authentifizierung und Rekonfiguration
- Async/await-Architektur mit aiobotocore
- Robuste Fehlerbehandlung mit spezifischen Fehlermeldungen

#### Config Flow

- GUI-basierte Konfiguration (Access Key ID, Secret Access Key, Bucket, Endpoint URL, Region, Prefix)
- Verbindungsvalidierung beim Setup
- Re-Authentifizierung bei abgelaufenen Zugangsdaten (`ConfigEntryAuthFailed`)
- Rekonfiguration bestehender Einträge ohne Entfernen der Integration
- Duplikat-Erkennung für Bucket/Endpoint-Kombinationen

#### Übersetzungen

- Englisch (EN)
- Deutsch (DE)

#### Technisch

- Python 3.12+ (PEP 695 type-Statement)
- Home Assistant 2025.2.0+
- Abhängigkeit: `aiobotocore>=2.6.0,<3.0.0`
- HACS-kompatibel (Custom Repository)

---

## Links

- [README.md](README.md) - Projekt-Übersicht
