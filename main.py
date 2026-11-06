import subprocess
from datetime import datetime
from pathlib import Path

# ================= CONFIGURATION =================
# Define your databases here:
DATABASES = [
    {
        "name": "sales-tracker-web-app",
        "container": "sales_traker",
        "remote_path": "/app/Database/sales_tracker.db",
    },
    {
        "name": "raw-material-stocktake",
        "container": "raw-material",
        "remote_path": "/data/app.db",
    },
]

BACKUP_ROOT_DIR = Path("./sqlite_backups")  # Where backups are saved
MAX_COPIES = 3  # How many backups to keep per database
# =================================================


def run_command(cmd: list[str]) -> None:
    """Helper to run shell commands and raise an error if they fail."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}"
        )


def rotate_backups(db_folder: Path, max_copies: int) -> None:
    """Keeps only the newest `max_copies` files, deleting the oldest."""
    # Find all backup files and sort by modification time (oldest first)
    backups = sorted(db_folder.glob("*.db"), key=lambda f: f.stat().st_mtime)

    while len(backups) > max_copies:
        oldest = backups.pop(0)
        oldest.unlink()
        print(f"  [+] Rotated: Deleted old backup -> {oldest.name}")


def backup_database(db_config: dict) -> None:
    db_name = db_config["name"]
    container = db_config["container"]
    remote_path = db_config["remote_path"]

    # 1. Create a dedicated folder for this database
    db_backup_dir = BACKUP_ROOT_DIR / db_name
    db_backup_dir.mkdir(parents=True, exist_ok=True)

    # 2. Generate a timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_file = db_backup_dir / f"{db_name}_{timestamp}.db"

    print(f"\n--- Backing up '{db_name}' from container '{container}' ---")

    # 3. Stop container, copy out file, and ALWAYS restart container
    try:
        print(f"  -> Stopping container '{container}'...")
        run_command(["docker", "stop", container])

        print(f"  -> Copying database to {local_file}...")
        run_command(["docker", "cp", f"{container}:{remote_path}", str(local_file)])

        print("  -> Backup copied successfully.")

        # 4. Prune backups older than 12 copies
        rotate_backups(db_backup_dir, MAX_COPIES)

    except Exception as e:
        print(f"  [!] ERROR during backup of '{db_name}': {e}")
    finally:
        # This block runs even if docker cp or anything else throws an error
        print(f"  -> Starting container '{container}'...")
        try:
            run_command(["docker", "start", container])
            print(f"  -> Container '{container}' is back up.")
        except Exception as e:
            print(f"  [!] CRITICAL: Failed to restart '{container}': {e}")


def main():
    print(f"Starting SQLite backup run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for db_config in DATABASES:
        backup_database(db_config)

    print("\nAll database backups completed.")


if __name__ == "__main__":
    main()