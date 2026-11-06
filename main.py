import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import subprocess

# ================= CONFIGURATION =================
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
    {
        "name": "waste-management-online-form",
        "container": "waste-management",
        "remote_path": "/data/waste_form.db",
    },
    {
        "name": "weekly-stock-takes-web",
        "container": "weekly-stocktake-app",
        "remote_path": "app/Database/stocktakes.db",
    },
]

BACKUP_ROOT_DIR = Path("./docker_sqlite_backups")  # Where backups are saved
MAX_COPIES = 3  # How many backups to keep per database

# Logging settings
LOG_FILE = BACKUP_ROOT_DIR / "backup.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
# =================================================


def setup_logger() -> logging.Logger:
    """Configures a logger with a single-file rotating handler (max 10MB) and console output."""
    BACKUP_ROOT_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("sqlite_backup")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # backupCount=0 ensures only a single log file exists (it truncates/resets when it reaches 10MB)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=0,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Output to console as well
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()


def run_command(cmd: list[str]) -> None:
    """Helper to run shell commands and raise an error if they fail."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}"
        )


def rotate_backups(db_folder: Path, max_copies: int) -> None:
    """Keeps only the newest `max_copies` files, deleting the oldest."""
    backups = sorted(db_folder.glob("*.db"), key=lambda f: f.stat().st_mtime)

    while len(backups) > max_copies:
        oldest = backups.pop(0)
        oldest.unlink()
        logger.info(f"Rotated: Deleted old backup -> {oldest.name}")


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

    logger.info(f"Starting backup for '{db_name}' from container '{container}'")

    # 3. Stop container, copy out file, and ALWAYS restart container
    try:
        logger.info(f"Stopping container '{container}'...")
        run_command(["docker", "stop", container])

        logger.info(f"Copying database to {local_file}...")
        run_command(["docker", "cp", f"{container}:{remote_path}", str(local_file)])

        logger.info("Backup copied successfully.")

        # 4. Prune older backups
        rotate_backups(db_backup_dir, MAX_COPIES)

    except Exception as e:
        logger.error(f"Error during backup of '{db_name}': {e}")
    finally:
        logger.info(f"Starting container '{container}'...")
        try:
            run_command(["docker", "start", container])
            logger.info(f"Container '{container}' is back up.")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to restart container '{container}': {e}")


def main():
    logger.info("Starting SQLite backup run.")

    for db_config in DATABASES:
        backup_database(db_config)

    logger.info("All database backups completed.")


if __name__ == "__main__":
    main()