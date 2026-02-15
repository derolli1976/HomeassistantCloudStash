# Release Notes – v1.0.0

## 🎉 Initial Release

CloudStash is a Home Assistant custom integration for storing backups in S3-compatible object storage. The integration registers itself as a **backup agent** and appears directly under **Settings → System → Backups** as an additional storage location.

---

## ✨ Features

### ☁️ S3-Compatible Backup Agent

CloudStash connects the Home Assistant backup system to any object storage that supports the S3 protocol:

- **Upload backups** – automatically or manually from the HA UI
- **Download backups** – restore directly from the cloud
- **List backups** – browse all stored backups including metadata
- **Delete backups** – remove old archives you no longer need

### 📦 Multipart Upload

Large backups are automatically transferred in chunks. This keeps memory usage low – even for multi-gigabyte backups.

### 🔧 Comfortable Config Flow

- **Initial setup** with connection test (credentials + bucket are verified immediately)
- **Re-authentication** when credentials expire or change
- **Reconfiguration** – update settings anytime through the HA UI
- **Endpoint normalization** – missing `https://` prefixes are added automatically

### 🌍 Supported Providers

| Provider | Endpoint pattern |
|----------|-----------------|
| AWS S3 | `https://s3.<region>.amazonaws.com` |
| MinIO | `http://<host>:9000` |
| Wasabi | `https://s3.<region>.wasabisys.com` |
| Backblaze B2 | `https://s3.<region>.backblazeb2.com` |
| Cloudflare R2 | `https://<account>.r2.cloudflarestorage.com` |
| DigitalOcean Spaces | `https://<region>.digitaloceanspaces.com` |
| Synology C2 | `https://eu-002.s3.synologyc2.net` |
| Garage | `http://<host>:3900` |

Any other S3-compatible service should work as well.

### 🗂️ Structured Storage Layout

```
<bucket>/
  <prefix>/
    backups/
      <backup-id>.tar
      <backup-id>.metadata.json
```

Each backup produces two objects: the archive itself and a small JSON metadata sidecar. The configurable prefix keeps CloudStash data separated from other content in the bucket.

---

## 🧪 Quality Assurance

- **57 unit tests** with pytest (config flow, init, backup agent)
- **CI/CD pipeline** with GitHub Actions:
  - Pytest (Python 3.13 + 3.14)
  - Hassfest Validation
  - HACS Validation
  - CodeQL Security Analysis

---

## 🌐 Localization

- English and German translations for config flow and error messages
- Full README documentation in English and German

---

## 📋 Installation

### Via HACS (recommended)

1. Open **HACS** → **Integrations**
2. Three-dot menu → **Custom repositories**
3. Paste `https://github.com/derolli1976/HomeassistantCloudStash`, select category **Integration**
4. Install **CloudStash** and restart Home Assistant

### Manually

Copy the `custom_components/cloudstash` folder into your Home Assistant `config/custom_components/` directory and restart.

### Setup

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for **CloudStash**
3. Enter Access Key, Secret Key, Bucket, Endpoint URL, and Region
4. The connection is verified automatically

---

## ℹ️ Requirements

- Home Assistant **2025.2.0** or higher
- An existing S3-compatible bucket (not created automatically)
- Credentials with read/write access to the bucket

---

## 🙏 Feedback

Bug reports, feature requests, and feedback are welcome on [GitHub Issues](https://github.com/derolli1976/HomeassistantCloudStash/issues).

Pull requests are welcome!
