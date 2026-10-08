"""Add the local migration target without changing existing application credentials."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
SETTINGS = {"MONGODB_URI": "mongodb://localhost:27017/?replicaSet=learnova-rs",
            "MONGODB_DB": "learnova_migration_dev", "MONGODB_TIMEOUT_MS": "5000"}


def main():
    path = ROOT / ".env"
    original = path.read_text(encoding="utf-8-sig")
    current = dict(line.split("=", 1) for line in original.splitlines()
                   if "=" in line and not line.strip().startswith("#"))
    for key, value in SETTINGS.items():
        if key in current and current[key].strip() != value:
            raise RuntimeError(f"Existing {key} differs; review before changing it.")
    backup = ROOT / ".local/migration-baseline/phase2-application.original.env"
    if not backup.exists():
        shutil.copy2(path, backup)
    missing = [f"{key}={value}" for key, value in SETTINGS.items() if key not in current]
    if missing:
        path.write_text(original.rstrip() + "\n\n# Local MongoDB migration target\n" + "\n".join(missing) + "\n", encoding="utf-8")
    print("MongoDB migration settings are present; existing application settings retained.")


if __name__ == "__main__":
    main()
