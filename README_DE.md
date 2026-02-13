# CloudStash – S3-kompatibles Backup für Home Assistant

*[English Version](README.md)*

<p align="center">
  <img src="logo.svg" alt="CloudStash Logo" width="200">
</p>

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Kompatibel-blue?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Lizenz](https://img.shields.io/github/license/derolli1976/HomeassistantS3CompatibleBackup?style=for-the-badge)](LICENSE)
[![GitHub Sterne](https://img.shields.io/github/stars/derolli1976/HomeassistantS3CompatibleBackup?style=for-the-badge)](https://github.com/derolli1976/HomeassistantS3CompatibleBackup/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/derolli1976/HomeassistantS3CompatibleBackup?style=for-the-badge)](https://github.com/derolli1976/HomeassistantS3CompatibleBackup/issues)

CloudStash erweitert die eingebaute Backup-Funktion von Home Assistant um Unterstützung für **jeden S3-kompatiblen Speicher** – nicht nur AWS S3. Es funktioniert mit AWS S3, MinIO, Wasabi, Backblaze B2, DigitalOcean Spaces, Cloudflare R2, Synology C2, Garage und jedem anderen S3-kompatiblen Anbieter.

---

## Schnellstart

1. Installation über HACS oder manuell (siehe [Installation](#installation))
2. Home Assistant neustarten
3. **Einstellungen** > **Geräte & Dienste** > **Integration hinzufügen**
4. Nach **"CloudStash"** suchen
5. Zugangsdaten eingeben (Access Key ID, Secret Access Key, Bucket-Name, Endpoint URL, Region)
6. **Einstellungen** > **System** > **Backups** > S3-Speicher als Backup-Ziel auswählen

---

## Funktionen

- **Vollständige Backup-Unterstützung** – Hochladen, Herunterladen, Auflisten und Löschen
- **Multipart-Upload** – Effiziente Verarbeitung großer Backups (>20 MB)
- **Region-Unterstützung** – Jede S3-Region konfigurierbar
- **Benutzerdefinierte Endpunkte** – Funktioniert mit jeder S3-kompatiblen API
- **Sicher** – Authentifizierung über Access Key ID + Secret Access Key
- **Asynchron** – Nicht-blockierende Operationen mit aiobotocore
- **Caching** – Backup-Auflistung wird 5 Minuten gecacht
- **Re-Authentifizierung** – Automatische Aufforderung bei abgelaufenen Zugangsdaten
- **Rekonfiguration** – Einstellungen ändern ohne die Integration zu entfernen

---

## Installation

### HACS (Empfohlen)

[![Öffne deine Home Assistant Instanz und öffne ein Repository im Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=derolli1976&repository=HomeassistantS3CompatibleBackup&category=integration)

1. Öffne **HACS** in Home Assistant
2. Gehe zu **Integrationen**
3. Klicke auf das Menü > **Benutzerdefinierte Repositories**
4. Repository-URL `https://github.com/derolli1976/HomeassistantS3CompatibleBackup` mit Kategorie **Integration** hinzufügen
5. Klicke **Installieren**
6. Home Assistant neustarten

### Manuelle Installation

```bash
cd /config/custom_components
git clone https://github.com/derolli1976/HomeassistantS3CompatibleBackup.git cloudstash
```

Dann Home Assistant neustarten.

---

## Konfiguration

Gehe zu **Einstellungen** > **Geräte & Dienste** > **Integration hinzufügen** und suche nach **"CloudStash"**.

| Feld | Beschreibung | Beispiel |
|------|--------------|----------|
| Access Key ID | Dein S3 Access Key | `AKIAIOSFODNN7EXAMPLE` |
| Secret Access Key | Dein S3 Secret Key | `wJalrXUtnFEMI/K7MDENG/...` |
| Bucket-Name | Ziel-Bucket (muss existieren) | `meine-ha-backups` |
| Endpoint URL | S3-kompatibler Endpunkt | `https://s3.eu-central-1.amazonaws.com` |
| Region | Speicher-Region | `eu-central-1` |
| Speicher-Präfix | Stammordner für Backups (optional) | `homeassistant` |

---

## Nutzung

Nach der Konfiguration erscheint die Integration als Backup-Speicherort in Home Assistant. Gehe zu **Einstellungen** > **System** > **Backups**, erstelle ein neues Backup und wähle deinen S3-Speicher.

### Backup-Struktur

```
mein-bucket/
└── homeassistant/           # Speicher-Präfix (konfigurierbar)
    └── backups/
        ├── backup-abc123.tar
        ├── backup-abc123.metadata.json
        └── ...
```

Jedes Backup besteht aus zwei Dateien: dem `.tar`-Archiv und einer `.metadata.json`-Datei mit Metadaten für Home Assistant. Der Speicher-Präfix ermöglicht es, einen Bucket für mehrere HA-Instanzen oder andere Anwendungen gemeinsam zu nutzen.

---

## Anbieter-Endpunkt-Referenz

Die folgende Tabelle zeigt die Endpoint URL und Region, die du für jeden Anbieter eingeben musst. Die Einrichtung von Bucket und Zugangsdaten entnimmst du der Dokumentation deines Anbieters.

| Anbieter | Endpoint URL | Region | Hinweise |
|----------|-------------|--------|----------|
| **AWS S3** | `https://s3.<region>.amazonaws.com` | z.B. `eu-central-1` | [Vollständige Endpunktliste](https://docs.aws.amazon.com/general/latest/gr/s3.html) |
| **MinIO** | `http://<dein-server>:9000` | `us-east-1` | Standard-Region für MinIO |
| **Wasabi** | `https://s3.<region>.wasabisys.com` | z.B. `eu-central-1` | [Regionsliste](https://docs.wasabi.com/docs/what-are-the-service-urls-for-wasabis-different-storage-regions) |
| **Backblaze B2** | `https://s3.<region>.backblazeb2.com` | Aus URL extrahieren, z.B. `us-west-004` | Region muss zum Endpunkt passen |
| **DigitalOcean Spaces** | `https://<region>.digitaloceanspaces.com` | z.B. `fra1` | |
| **Cloudflare R2** | `https://<account-id>.r2.cloudflarestorage.com` | `auto` | |
| **Synology C2** | `https://eu-002.s3.synologyc2.net` | z.B. `eu-002` | Auch `us-001`, `tw-001` |
| **Garage** | `http://<dein-server>:3900` | `garage` | Region **muss** mit `garage.toml` übereinstimmen; `us-east-1` führt zu Auth-Fehlern |

### Erforderliche S3-Berechtigungen

Deine Zugangsdaten benötigen diese Berechtigungen (gilt für alle Anbieter):

| Berechtigung | Zweck |
|--------------|-------|
| `s3:PutObject` | Backup-Dateien hochladen |
| `s3:GetObject` | Backups herunterladen/wiederherstellen |
| `s3:DeleteObject` | Alte Backups löschen |
| `s3:ListBucket` | Verfügbare Backups auflisten |
| `s3:AbortMultipartUpload` | Fehlgeschlagene Uploads abbrechen |
| `s3:ListMultipartUploadParts` | Multipart-Uploads fortsetzen |

**AWS IAM Policy Beispiel** (`DEIN-BUCKET-NAME` ersetzen):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "arn:aws:s3:::DEIN-BUCKET-NAME",
        "arn:aws:s3:::DEIN-BUCKET-NAME/*"
      ]
    }
  ]
}
```

---

## Fehlerbehebung

### "Ungültige Zugangsdaten"

- Prüfe Access Key ID und Secret Access Key
- Stelle sicher, dass die Zugangsdaten die erforderlichen Berechtigungen haben und nicht abgelaufen sind

### "Verbindung nicht möglich"

- Prüfe die Endpoint-URL und deine Netzwerk-/Firewall-Regeln
- Bei selbst gehosteten Lösungen stelle sicher, dass der Server läuft

### "Ungültiger Bucket-Name"

- Bucket-Namen müssen kleingeschrieben sein, 3-63 Zeichen, nur Buchstaben, Zahlen und Bindestriche
- Der Bucket muss bereits existieren (CloudStash erstellt keine Buckets)

### "Ungültige Endpoint-URL"

- Die URL muss mit `http://` oder `https://` beginnen
- Prüfe, ob die Region zum Endpunkt passt

### Backups werden nicht angezeigt

- Die Backup-Liste wird bis zu 5 Minuten gecacht
- Prüfe die Home Assistant Logs auf Fehler
- Stelle sicher, dass der Bucket `.metadata.json`-Dateien enthält

### Debug-Logging

In `configuration.yaml` eintragen:

```yaml
logger:
  default: info
  logs:
    custom_components.cloudstash: debug
```

---

## Speicheranbieter-Vergleich

| Anbieter | Kostenlose Stufe | Egress-Gebühren | Min. Speichergebühr | S3-kompatibel |
|----------|------------------|-----------------|---------------------|---------------|
| AWS S3 | 5 GB (12 Monate) | Ja | Nein | Nativ |
| Backblaze B2 | 10 GB | Kostenlos bis 3x Speicher | Nein | Ja |
| Wasabi | Nein | Nein | Ja (1 TB min) | Ja |
| Cloudflare R2 | 10 GB | Nein | Nein | Ja |
| DigitalOcean Spaces | Nein | Ja | 5$/Monat | Ja |
| MinIO | Selbst gehostet | N/A | N/A | Ja |
| Garage | Selbst gehostet | N/A | N/A | Ja |

---

## Lizenz

MIT-Lizenz – siehe [LICENSE](LICENSE) für Details.

## Mitwirken

Beiträge sind willkommen. Bitte öffne ein Issue oder einen Pull Request.
