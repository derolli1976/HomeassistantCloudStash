# CloudStash

*[Deutsche Version](README_DE.md)*

<p align="center">
  <img src="logo.svg" alt="CloudStash Logo" width="200">
</p>

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-blue?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/derolli1976/HomeassistantCloudStash?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/derolli1976/HomeassistantCloudStash?style=for-the-badge)](https://github.com/derolli1976/HomeassistantCloudStash/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/derolli1976/HomeassistantCloudStash?style=for-the-badge)](https://github.com/derolli1976/HomeassistantCloudStash/issues)

Store your Home Assistant backups in the cloud. CloudStash connects Home Assistant's backup system to any object storage that speaks the S3 protocol, giving you a reliable off-site destination for your data.

---

## What it does

CloudStash registers itself as a **backup agent** in Home Assistant. After setup you will find it as an additional backup location under **Settings > System > Backups**. From there, every backup you create can be sent directly to your object storage.

The integration supports all common operations: uploading new backups, downloading existing ones, browsing the backup list, and removing old archives. Large files are transferred in chunks so memory usage stays low even for multi-gigabyte backups.

---

## Supported providers

CloudStash works with any service or software that implements the S3 API:

| Provider | Endpoint pattern | Typical region |
|----------|-----------------|----------------|
| AWS S3 | `https://s3.<region>.amazonaws.com` | `eu-central-1` |
| MinIO | `http://<host>:9000` | `us-east-1` |
| Wasabi | `https://s3.<region>.wasabisys.com` | `eu-central-1` |
| Backblaze B2 | `https://s3.<region>.backblazeb2.com` | from URL, e.g. `us-west-004` |
| Cloudflare R2 | `https://<account>.r2.cloudflarestorage.com` | `auto` |
| DigitalOcean Spaces | `https://<region>.digitaloceanspaces.com` | `fra1` |
| Synology C2 | `https://eu-002.s3.synologyc2.net` | `eu-002` |
| Garage | `http://<host>:3900` | must match `garage.toml` |

Other S3-compatible services should work the same way using *endpoint URL + region + credentials*.

---

## Installation

### Via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=derolli1976&repository=HomeassistantCloudStash&category=integration)

1. In Home Assistant open **HACS > Integrations**
2. Open the three-dot menu and choose **Custom repositories**
3. Paste `https://github.com/derolli1976/HomeassistantCloudStash`, select category **Integration**, and confirm
4. Install **CloudStash** and restart Home Assistant

### Manually

Copy the `custom_components/cloudstash` folder into your Home Assistant `config/custom_components/` directory and restart.

---

## Setup

After installation, add the integration through **Settings > Devices & Services > Add Integration** and search for **CloudStash**.

You will need:

| Parameter | What to enter |
|-----------|--------------|
| **Access Key ID** | Provided by your storage provider or self-hosted server |
| **Secret Access Key** | The corresponding secret for the key above |
| **Bucket** | Name of an existing bucket where backups will be stored |
| **Endpoint URL** | Full URL to the S3-compatible API (see table above) |
| **Region** | Region identifier, e.g. `eu-central-1` (default: `us-east-1`) |
| **Prefix** | Optional folder prefix inside the bucket (default: `homeassistant`) |

CloudStash verifies the connection during setup. If the credentials or endpoint are wrong, you will see a clear error message.

After the first setup you can update credentials via **Reconfigure** or respond to automatic **Re-authentication** prompts if your keys expire.

---

## How backups are stored

```
<bucket>/
  <prefix>/
    backups/
      <backup-id>.tar
      <backup-id>.metadata.json
```

Each backup produces two objects: the archive itself and a small JSON sidecar with metadata that Home Assistant needs for listing and restoring. The configurable prefix keeps CloudStash data separated from anything else in the bucket.

---

## Required permissions

The credentials you provide need read and write access to the bucket. For AWS the minimum IAM policy looks like this (replace `BUCKET`):

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

Other providers use their own permission systems, but the required operations are the same: list, read, write, and delete objects in the bucket.

---

## Troubleshooting

**Connection fails** -- Double-check the endpoint URL and make sure Home Assistant can reach the host. For self-hosted services, verify the server is running and reachable on the configured port.

**Credentials rejected** -- Confirm that the Access Key and Secret match, that the key is active, and that the permissions above are granted.

**Bucket not found** -- CloudStash does not create buckets. The bucket must exist before you set up the integration.

**Backups take a while to appear** -- The backup list is cached for up to five minutes. Wait or check the Home Assistant log for errors.

**Debug logging** -- Add the following to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.cloudstash: debug
```

---

## License

MIT -- see [LICENSE](LICENSE).

## Contributing

Bug reports and pull requests are welcome via GitHub.
