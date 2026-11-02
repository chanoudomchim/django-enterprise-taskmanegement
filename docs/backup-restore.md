# Backup and Disaster Recovery — WorkFlow Enterprise

This document describes automated backup procedures, media asset archiving, and verified restore runbooks.

---

## 1. Automated PostgreSQL Backups

PostgreSQL database backups should run daily via host cron or external backup orchestrator.

### Logical Backup (`pg_dump`)
```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/workflow"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/workflow_db_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# Execute pg_dump inside the db container
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-workflow_user}" -d "${POSTGRES_DB:-workflow_db}" --clean --if-exists | gzip > "${BACKUP_FILE}"

echo "Database backup completed: ${BACKUP_FILE}"
```

### Media Storage Backup (`tar` / `rsync`)
```bash
BACKUP_DIR="/var/backups/workflow"
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf "${BACKUP_DIR}/workflow_media_${DATE}.tar.gz" -C ./media .
```

---

## 2. Disaster Recovery & Restoration Runbook

### Step 1: Stop Application Traffic
```bash
docker compose stop web
```

### Step 2: Restore Database from Archive
```bash
# Decompress and feed SQL dump into PostgreSQL container
gunzip -c /var/backups/workflow/workflow_db_20261102.sql.gz | docker compose exec -T db psql -U workflow_user -d workflow_db
```

### Step 3: Restore Media Files
```bash
tar -xzf /var/backups/workflow/workflow_media_20261102.tar.gz -C ./media/
```

### Step 4: Run Migrations Check
```bash
docker compose run --rm web python manage.py migrate --noinput
```

### Step 5: Resume Web Service & Verify Health
```bash
docker compose start web
curl -f http://localhost:8000/health/
```

