<div align="center">

# 🗄️ Docker SQLite Backup Utility

**Automated, consistent, and rotated SQLite backups extracted directly from running Docker containers.**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square&logo=python&logoColor=white)](#)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat-square&logo=docker&logoColor=white)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](#)
[![Maintenance](https://img.shields.io/badge/status-active-brightgreen.svg?style=flat-square)](#)

</div>

---

## 📖 Overview

Backing up SQLite databases while applications actively write to them risks database corruption and lock errors. 

This utility ensures **100% data integrity** by orchestrating a safe backup sequence:
1. Temporarily stops the target Docker container.
2. Extracts the `.db` file via `docker cp`.
3. Automatically restarts the container (even if the extraction fails).
4. Rotates old backups to prevent disk bloat.

---

## ✨ Features

- 🛡️ **Zero-Corruption Guarantee:** Containers are cleanly stopped before copy, avoiding half-written SQLite transactions or WAL-mode desyncs.
- 🔁 **Fail-Safe Container Recovery:** Wrapped in a `try...finally` block to ensure your services always come back online, even if a backup step errors out.
- 🧹 **Automatic Retention & Rotation:** Keeps only the $N$ most recent copies per database (configurable).
- 📜 **Self-Managing Logs:** Dual logging to console (`stdout`) and a rotating log file capped at 10 MB to prevent unbounded log growth.
- 🗂️ **Organized Storage:** Creates neat subdirectories for each application automatically.

---

## 📁 Directory Structure

When running, the script creates and manages the following file hierarchy:

```text
.
├── main.py
└── docker_sqlite_backups/
    ├── backup.log
    ├── raw-material-stocktake/
    │   ├── raw-material-stocktake_20261106_120000.db
    │   ├── raw-material-stocktake_20261106_130000.db
    │   └── raw-material-stocktake_20261106_140000.db
    ├── sales-tracker-web-app/
    │   └── ...
    └── ...
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python `3.9+` (standard library only, **no `pip install` required**)
- Docker installed and running on the host
- The current user must have permission to run `docker` commands (e.g., added to the `docker` user group or run as root)

### 2. Configuration

Edit the configuration block inside `main.py` to match your containers:

```python
# ================= CONFIGURATION =================
DATABASES = [
    {
        "name": "sales-tracker-web-app",        # Identifier & directory name
        "container": "sales_traker",             # Target Docker container name
        "remote_path": "/app/Database/sales.db", # Path to SQLite inside the container
    },
    # Add more databases here...
]

BACKUP_ROOT_DIR = Path("./docker_sqlite_backups")  # Destination path
MAX_COPIES = 3                                    # Snapshots to keep per database
# =================================================
```

### 3. Manual Run

```bash
python3 main.py
```

---

## ⏰ Automated Scheduling (Cron)

To run this backup pipeline automatically on a Linux host (e.g., every night at 2:00 AM):

1. Open your crontab editor:
   ```bash
   crontab -e
   ```

2. Add a line pointing to your script and Python binary:
   ```cron
   0 2 * * * /usr/bin/python3 /path/to/project/main.py >> /dev/null 2>&1
   ```

> **Note:** Logs are handled internally and written to `docker_sqlite_backups/backup.log`, so discarding cron's default stdout/stderr with `>> /dev/null 2>&1` is safe.

---

## 📋 Execution Flow

```text
  [Start Run]
       │
       ▼
  [Select Database Config]
       │
       ├──► 1. Stop Container (docker stop)
       ├──► 2. Copy Database (docker cp)
       ├──► 3. Restart Container (docker start) ── (Always executed)
       └──► 4. Prune Backups (> MAX_COPIES)
       │
       ▼
  [Next Database or Exit]
```

---

## ⚠️ Notes & Tips

- **Relative Paths:** If running via cron, consider changing `BACKUP_ROOT_DIR` to an absolute path (e.g., `Path("/var/backups/sqlite")`) so you don't depend on the working directory where cron executes.
- **Downtime:** The container will be down for the few seconds it takes to copy the `.db` file. For high-availability services, run backups during off-peak hours.

---

## 📄 License

Distributed under the [MIT License](LICENSE). Feel free to adapt it to your workflow.