# CloudStash

*[English Version](README.md)*

<p align="center">
  <img src="logo.svg" alt="CloudStash Logo" width="200">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/derolli1976/HomeassistantCloudStash.svg)](https://github.com/derolli1976/HomeassistantCloudStash/releases)
[![Pytest](https://github.com/derolli1976/HomeassistantCloudStash/actions/workflows/tests.yml/badge.svg)](https://github.com/derolli1976/HomeassistantCloudStash/actions/workflows/tests.yml)
[![Hassfest](https://github.com/derolli1976/HomeassistantCloudStash/actions/workflows/hassfest.yml/badge.svg)](https://github.com/derolli1976/HomeassistantCloudStash/actions/workflows/hassfest.yml)
[![HACS Validation](https://github.com/derolli1976/HomeassistantCloudStash/actions/workflows/hacs.yml/badge.svg)](https://github.com/derolli1976/HomeassistantCloudStash/actions/workflows/hacs.yml)

Sichere deine Home Assistant Backups in der Cloud. CloudStash verbindet das Backup-System von Home Assistant mit jedem Objektspeicher, der das S3-Protokoll versteht, und gibt dir damit ein zuverlässiges externes Ziel für deine Daten.

---

## Was CloudStash macht

CloudStash meldet sich als **Backup-Agent** in Home Assistant an. Nach der Einrichtung taucht es als zusätzlicher Speicherort unter **Einstellungen > System > Backups** auf. Jedes Backup, das du erstellst, kann von dort direkt in deinen Objektspeicher geschickt werden.

Die Integration beherrscht alle gängigen Aktionen: neue Backups hochladen, vorhandene herunterladen, die Liste durchsuchen und alte Archive löschen. Große Dateien werden in Blöcken übertragen, damit der Speicherverbrauch auch bei Backups im Gigabyte-Bereich niedrig bleibt.

---

## Unterstützte Anbieter

CloudStash arbeitet mit jedem Dienst oder jeder Software zusammen, die das S3-API implementiert:

| Anbieter | Endpunkt-Schema | Typische Region |
|----------|----------------|-----------------|
| AWS S3 | `https://s3.<region>.amazonaws.com` | `eu-central-1` |
| MinIO | `http://<host>:9000` | `us-east-1` |
| Wasabi | `https://s3.<region>.wasabisys.com` | `eu-central-1` |
| Backblaze B2 | `https://s3.<region>.backblazeb2.com` | aus URL, z.B. `us-west-004` |
| Cloudflare R2 | `https://<account>.r2.cloudflarestorage.com` | `auto` |
| DigitalOcean Spaces | `https://<region>.digitaloceanspaces.com` | `fra1` |
| Synology C2 | `https://eu-002.s3.synologyc2.net` | `eu-002` |
| Garage | `http://<host>:3900` | muss zu `garage.toml` passen |

Andere S3-kompatible Dienste sollten genauso funktionieren -- *Endpunkt-URL + Region + Zugangsdaten* reichen aus.

---

## Installation

### Über HACS

[![Öffne deine Home Assistant Instanz und öffne ein Repository im Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=derolli1976&repository=HomeassistantCloudStash&category=integration)

1. In Home Assistant **HACS > Integrationen** öffnen
2. Über das Drei-Punkte-Menü **Benutzerdefinierte Repositories** wählen
3. `https://github.com/derolli1976/HomeassistantCloudStash` einfügen, Kategorie **Integration** auswählen und bestätigen
4. **CloudStash** installieren und Home Assistant neu starten

### Manuell

Den Ordner `custom_components/cloudstash` in dein Home Assistant `config/custom_components/`-Verzeichnis kopieren und neu starten.

---

## Einrichtung

Nach der Installation die Integration über **Einstellungen > Geräte & Dienste > Integration hinzufügen** hinzufügen und nach **CloudStash** suchen.

Folgende Angaben werden benötigt:

| Parameter | Was eintragen |
|-----------|--------------|
| **Access Key ID** | Wird vom Speicheranbieter oder selbst gehosteten Server bereitgestellt |
| **Secret Access Key** | Das zugehörige Geheimnis zum Key |
| **Bucket** | Name eines bestehenden Buckets, in dem Backups abgelegt werden |
| **Endpunkt-URL** | Vollständige URL zum S3-kompatiblen API (siehe Tabelle oben) |
| **Region** | Regions-Kennung, z.B. `eu-central-1` (Standard: `us-east-1`) |
| **Präfix** | Optionaler Ordnerpräfix im Bucket (Standard: `homeassistant`) |

CloudStash prüft die Verbindung während der Einrichtung. Wenn Zugangsdaten oder Endpunkt nicht stimmen, erscheint eine klare Fehlermeldung.

Nach der Ersteinrichtung lassen sich Zugangsdaten über **Neu konfigurieren** ändern oder über automatische **Re-Authentifizierung** aktualisieren, wenn Schlüssel ablaufen.

---

## Wie Backups gespeichert werden

```
<bucket>/
  <prefix>/
    backups/
      <backup-id>.tar
      <backup-id>.metadata.json
```

Jedes Backup erzeugt zwei Objekte: das Archiv selbst und eine kleine JSON-Sidecar-Datei mit Metadaten, die Home Assistant zum Auflisten und Wiederherstellen braucht. Der konfigurierbare Präfix hält die CloudStash-Daten von allem anderen im Bucket getrennt.

---

## Benötigte Berechtigungen

Die verwendeten Zugangsdaten brauchen Lese- und Schreibzugriff auf den Bucket. Für AWS sieht die minimale IAM-Policy so aus (`BUCKET` ersetzen):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
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
      "arn:aws:s3:::BUCKET",
      "arn:aws:s3:::BUCKET/*"
    ]
  }]
}
```

Andere Anbieter haben eigene Berechtigungssysteme, aber die nötigen Operationen sind dieselben: Objekte im Bucket auflisten, lesen, schreiben und löschen.

---

## Fehlerbehebung

**Verbindung schlägt fehl** -- Endpunkt-URL prüfen und sicherstellen, dass Home Assistant den Host erreichen kann. Bei selbst gehosteten Diensten kontrollieren, ob der Server läuft und auf dem konfigurierten Port erreichbar ist.

**Zugangsdaten abgelehnt** -- Access Key und Secret auf Richtigkeit prüfen. Sicherstellen, dass der Schlüssel aktiv ist und die nötigen Berechtigungen hat.

**Bucket nicht gefunden** -- CloudStash legt keine Buckets an. Der Bucket muss vor der Einrichtung bereits existieren.

**Backups erscheinen nicht sofort** -- Die Backup-Liste wird bis zu fünf Minuten gecacht. Entweder warten oder im Home Assistant Log nach Fehlern schauen.

**Debug-Logging** -- Folgendes in `configuration.yaml` eintragen:

```yaml
logger:
  default: info
  logs:
    custom_components.cloudstash: debug
```

---

## Lizenz

MIT -- siehe [LICENSE](LICENSE).

## Mitwirken

Fehlermeldungen und Pull Requests sind über GitHub willkommen.
