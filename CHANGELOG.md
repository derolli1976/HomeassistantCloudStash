# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-15

### 🎉 Initial Release

First official release of CloudStash as a standalone project.

#### Backup Agent

- S3-compatible backup agent for Home Assistant's built-in backup system
- Works with any S3-compatible storage (AWS S3, MinIO, Wasabi, Backblaze B2, DigitalOcean Spaces, Cloudflare R2, Synology C2, Garage, and more)
- Upload, download, list, and delete backups
- Multipart upload for large backups (>20 MB) with equal-sized parts for R2 compatibility
- Backup listing cache with 5-minute TTL (monotonic-based)
- Metadata stored as `.metadata.json` sidecar files in the same prefix

#### Architecture

- `ObjectStorageGateway` – dedicated worker thread with its own event loop, avoids blocking the HA event loop with botocore I/O
- `CloudStashAgent` – full `BackupAgent` implementation
- `CloudStashConfigFlow` – setup, re-authentication, and reconfiguration
- Async/await architecture with aiobotocore
- Robust error handling with specific error messages

#### Config Flow

- GUI-based configuration (Access Key ID, Secret Access Key, Bucket, Endpoint URL, Region, Prefix)
- Connection validation during setup
- Re-authentication for expired credentials (`ConfigEntryAuthFailed`)
- Reconfiguration of existing entries without removing the integration
- Duplicate detection for bucket/endpoint combinations
- Endpoint normalization (automatic `https://` prefix)

#### Quality Assurance

- 57 unit tests with pytest (config flow, init, backup agent)
- CI/CD pipeline with GitHub Actions (Pytest, Hassfest, HACS Validation, CodeQL)

#### Localization

- English (EN)
- German (DE)

#### Technical

- Python 3.13+
- Home Assistant 2025.2.0+
- Dependency: `aiobotocore>=2.6.0,<3.0.0`
- HACS-compatible (Custom Repository)

---

## Links

- [README.md](README.md) - Projekt-Übersicht
