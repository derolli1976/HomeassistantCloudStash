# CloudStash – S3 Compatible Backup for Home Assistant

*[Deutsche Version](README_DE.md)*

<p align="center">
  <img src="logo.svg" alt="CloudStash Logo" width="200">
</p>

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-blue?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/derolli1976/HomeassistantS3CompatibleBackup?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/derolli1976/HomeassistantS3CompatibleBackup?style=for-the-badge)](https://github.com/derolli1976/HomeassistantS3CompatibleBackup/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/derolli1976/HomeassistantS3CompatibleBackup?style=for-the-badge)](https://github.com/derolli1976/HomeassistantS3CompatibleBackup/issues)

CloudStash extends Home Assistant's built-in backup functionality to support **any S3-compatible storage** – not just AWS S3. It works with AWS S3, MinIO, Wasabi, Backblaze B2, DigitalOcean Spaces, Cloudflare R2, Synology C2, Garage and any other S3-compatible provider.

---

## Quick Start

1. Install via HACS or manually (see [Installation](#installation))
2. Restart Home Assistant
3. Go to **Settings** > **Devices & Services** > **Add Integration**
4. Search for **"CloudStash"**
5. Enter your S3 credentials (Access Key ID, Secret Access Key, Bucket Name, Endpoint URL, Region)
6. Go to **Settings** > **System** > **Backups** and select your S3 storage as backup location

---

## Features

- **Full backup support** – Upload, download, list and delete backups
- **Multipart upload** – Handles large backups (>20 MB) efficiently
- **Region support** – Any S3 region
- **Custom endpoints** – Works with any S3-compatible API
- **Secure** – Access Key ID + Secret Access Key authentication
- **Async** – Non-blocking I/O via aiobotocore
- **Caching** – Backup listing cached for 5 minutes
- **Re-authentication** – Prompts automatically when credentials expire
- **Reconfigure** – Change settings without removing the integration

---

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=derolli1976&repository=HomeassistantS3CompatibleBackup&category=integration)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the menu > **Custom repositories**
4. Add repository URL `https://github.com/derolli1976/HomeassistantS3CompatibleBackup` with category **Integration**
5. Click **Install**
6. Restart Home Assistant

### Manual Installation

```bash
cd /config/custom_components
git clone https://github.com/derolli1976/HomeassistantS3CompatibleBackup.git cloudstash
```

Then restart Home Assistant.

---

## Configuration

Go to **Settings** > **Devices & Services** > **Add Integration** and search for **"CloudStash"**.

| Field | Description | Example |
|-------|-------------|---------|
| Access Key ID | Your S3 access key | `AKIAIOSFODNN7EXAMPLE` |
| Secret Access Key | Your S3 secret key | `wJalrXUtnFEMI/K7MDENG/...` |
| Bucket Name | Target bucket (must exist) | `my-ha-backups` |
| Endpoint URL | S3-compatible endpoint | `https://s3.eu-central-1.amazonaws.com` |
| Region | Storage region | `eu-central-1` |
| Storage Prefix | Root folder for backups (optional) | `homeassistant` |

---

## Usage

Once configured, the integration appears as a backup location in Home Assistant. Go to **Settings** > **System** > **Backups**, create a new backup and select your S3 storage.

### Backup Structure

```
my-bucket/
└── homeassistant/           # Storage Prefix (configurable)
    └── backups/
        ├── backup-abc123.tar
        ├── backup-abc123.metadata.json
        └── ...
```

Each backup consists of two files: the `.tar` archive and a `.metadata.json` file with metadata for Home Assistant. The storage prefix lets you share a bucket across multiple HA instances or other applications.

---

## Provider Endpoint Reference

The table below shows the endpoint URL and region you need to enter for each provider. Refer to your provider's documentation for bucket and credential setup.

| Provider | Endpoint URL | Region | Notes |
|----------|-------------|--------|-------|
| **AWS S3** | `https://s3.<region>.amazonaws.com` | e.g. `eu-central-1` | [Full endpoint list](https://docs.aws.amazon.com/general/latest/gr/s3.html) |
| **MinIO** | `http://<your-server>:9000` | `us-east-1` | Default region for MinIO |
| **Wasabi** | `https://s3.<region>.wasabisys.com` | e.g. `eu-central-1` | [Region list](https://docs.wasabi.com/docs/what-are-the-service-urls-for-wasabis-different-storage-regions) |
| **Backblaze B2** | `https://s3.<region>.backblazeb2.com` | Extract from URL, e.g. `us-west-004` | Region must match endpoint |
| **DigitalOcean Spaces** | `https://<region>.digitaloceanspaces.com` | e.g. `fra1` | |
| **Cloudflare R2** | `https://<account-id>.r2.cloudflarestorage.com` | `auto` | |
| **Synology C2** | `https://eu-002.s3.synologyc2.net` | e.g. `eu-002` | Also `us-001`, `tw-001` |
| **Garage** | `http://<your-server>:3900` | `garage` | Region **must** match `garage.toml`; using `us-east-1` causes auth errors |

### Required S3 Permissions

Your credentials need these permissions (applies to all providers):

| Permission | Purpose |
|------------|---------|
| `s3:PutObject` | Upload backup files |
| `s3:GetObject` | Download/restore backups |
| `s3:DeleteObject` | Delete old backups |
| `s3:ListBucket` | List available backups |
| `s3:AbortMultipartUpload` | Cancel failed uploads |
| `s3:ListMultipartUploadParts` | Resume multipart uploads |

**AWS IAM Policy example** (replace `YOUR-BUCKET-NAME`):

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
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ]
    }
  ]
}
```

---

## Troubleshooting

### "Invalid credentials"

- Verify Access Key ID and Secret Access Key
- Ensure the credentials have the required permissions and are not expired

### "Cannot connect"

- Check the Endpoint URL and your network/firewall rules
- For self-hosted solutions, make sure the server is running

### "Invalid bucket name"

- Bucket names must be lowercase, 3-63 characters, only letters, numbers and hyphens
- The bucket must already exist (CloudStash does not create buckets)

### "Invalid endpoint URL"

- The URL must start with `http://` or `https://`
- Verify the region matches the endpoint

### Backups not appearing

- The backup list is cached for up to 5 minutes
- Check the Home Assistant logs for errors
- Verify the bucket contains `.metadata.json` files

### Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.cloudstash: debug
```

---

## Storage Comparison

| Provider | Free Tier | Egress Fees | Min. Storage Fee | S3 Compatible |
|----------|-----------|-------------|------------------|---------------|
| AWS S3 | 5 GB (12 months) | Yes | No | Native |
| Backblaze B2 | 10 GB | Free up to 3x storage | No | Yes |
| Wasabi | No | No | Yes (1 TB min) | Yes |
| Cloudflare R2 | 10 GB | No | No | Yes |
| DigitalOcean Spaces | No | Yes | $5/month | Yes |
| MinIO | Self-hosted | N/A | N/A | Yes |
| Garage | Self-hosted | N/A | N/A | Yes |

---

## License

MIT License – see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. Please open an issue or pull request.
