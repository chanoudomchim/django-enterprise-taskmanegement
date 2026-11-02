# Production Deployment Guide — WorkFlow Enterprise

A comprehensive operational manual for deploying, configuring, securing, and maintaining **WorkFlow Enterprise** in production environments.

---

## 1. Architectural Principles & Constraints

WorkFlow Enterprise is architected as a **multi-tenant modular monolith** engineered for performance, operational simplicity, and strict data governance:

- **Direct Gunicorn Binding**: Zero Nginx container. Gunicorn binds directly to `0.0.0.0:8000 -> 8000`. Static files are served via WhiteNoise `CompressedManifestStaticFilesStorage` with aggressive HTTP caching and content hashing.
- **Zero Celery Infrastructure**: No Celery workers, RabbitMQ, or Celery Beat processes. Asynchronous background jobs and scheduled tasks run via standard host cron invoking Django management commands.
- **Dedicated Redis Caching**: Redis 7 is utilized strictly for application caching and rate limiting with tenant-isolated key prefixes (`get_tenant_cache`, `set_tenant_cache`).
- **Non-Root Application User**: The application process runs as `appuser` (UID 1000) inside containerized Linux namespaces.
- **Multi-Tenant Shared-Schema**: Enforced at the ORM layer via `TenantModel`, `TenantManager`, and `TenantMiddleware`.

```
 Internet / HTTPS Traffic (Cloudflare / Public Ingress)
                     │ (Port 443 -> Port 8000)
                     ▼
┌────────────────────────────────────────────────────────┐
│ workflow-enterprise-web                                │
│   - Gunicorn 23.0 WSGI Server (3 sync workers)         │
│   - Python 3.12-slim non-root user (appuser, UID 1000) │
│   - WhiteNoise CompressedManifestStaticFilesStorage    │
└────────────────┬───────────────────────┬───────────────┘
                 │                       │
                 ▼                       ▼
┌────────────────────────────────┐  ┌────────────────────────────────┐
│ workflow-enterprise-db         │  │ workflow-enterprise-redis      │
│   - PostgreSQL 16 Alpine       │  │   - Redis 7 Alpine             │
│   - Persistent named volume    │  │   - In-memory caching engine   │
│   - Internal network only      │  │   - Internal network only      │
└────────────────────────────────┘  └────────────────────────────────┘
```

---

## 2. System Requirements & Prerequisites

### Minimum Hardware Recommendations
| Tier | Users | vCPU | RAM | Storage |
|---|:---:|:---:|:---:|:---:|
| **Standard** | Up to 250 | 2 | 4 GB | 25 GB NVMe SSD |
| **High Capacity** | Up to 1,000 | 4 | 8 GB | 60 GB NVMe SSD |

### Software Prerequisites
- **Operating System**: Linux (Ubuntu 22.04 LTS, Debian 12, or RHEL 9 recommended)
- **Container Engine**: Docker Engine 24.0+
- **Compose Tool**: Docker Compose v2.20+ (`docker compose`)
- **System Utilities**: `curl`, `cron`, `git`

---

## 3. Production Environment Configuration (`.env`)

Create a production `.env` file on your server:

```bash
# ==============================================================================
# WorkFlow Enterprise — Production Environment Variables
# ==============================================================================

# Core Django Settings
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=generate-a-strong-64-character-cryptographic-random-key
DEBUG=False
ALLOWED_HOSTS=workflow.yourcompany.com,app.workflow.local

# Web Server Port
WEB_PORT=8000

# Security & SSL Configuration
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Database Configuration (PostgreSQL 16)
DB_ENGINE=postgresql
POSTGRES_DB=workflow_enterprise_prod
POSTGRES_USER=workflow_prod_user
POSTGRES_PASSWORD=use-a-strong-generated-database-password-2026
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis Cache Configuration (Strictly Caching, No Celery)
REDIS_URL=redis://redis:6379/1

# SMTP Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=postmaster@workflow.yourcompany.com
EMAIL_HOST_PASSWORD=your-smtp-api-password
DEFAULT_FROM_EMAIL=WorkFlow Enterprise <noreply@workflow.yourcompany.com>

# Telegram Bot Integration (Optional)
TELEGRAM_BOT_TOKEN=your-production-bot-token-from-botfather
TELEGRAM_BOT_USERNAME=WorkFlowEnterpriseBot
```

---

## 4. Step-by-Step Production Deployment Runbook

### Step 1: Clone Repository & Set Permissions
```bash
git clone https://github.com/your-org/django-enterprise-taskmanagement.git /opt/workflow-enterprise
cd /opt/workflow-enterprise
cp .env.example .env
chmod 600 .env
```

### Step 2: Build Application Image
Build the container image using the optimized Dockerfile:
```bash
docker compose build --pull
```

### Step 3: Initialize Database & Cache Services
Start the database and cache in the background and verify health:
```bash
docker compose up -d db redis
docker compose ps
```
Wait until both `db` and `redis` report status `healthy`.

### Step 4: Execute Database Migrations
Run all database schema migrations against PostgreSQL:
```bash
docker compose run --rm web python manage.py migrate --noinput
```

### Step 5: Collect and Compress Static Assets
Compile and post-process static files into `/app/staticfiles`:
```bash
docker compose run --rm web python manage.py collectstatic --noinput
```

### Step 6: Create Platform Superuser
Provision the root administrator account:
```bash
docker compose run --rm web python manage.py createsuperuser
```

### Step 7: Launch Application
Bring up the entire stack with direct Gunicorn binding:
```bash
docker compose up -d web
```

### Step 8: Verify System Health
Check container status and HTTP health endpoint:
```bash
docker compose ps
curl -I http://localhost:8000/health/
```
Expected response:
```http
HTTP/1.1 200 OK
Server: gunicorn
Content-Type: application/json
```

---

## 5. Host Cron Configuration for Background Operations

In compliance with the Zero-Celery architecture, scheduled and recurring operations run via standard Linux cron.

Create `/etc/cron.d/workflow-enterprise`:

```cron
# /etc/cron.d/workflow-enterprise
# Scheduled background jobs for WorkFlow Enterprise
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
PROJECT_DIR=/opt/workflow-enterprise

# Process recurring tasks every hour at minute 0
0 * * * * root cd $PROJECT_DIR && docker compose exec -T web python manage.py process_recurring_tasks >> /var/log/workflow_cron.log 2>&1

# Send task due reminders daily at 08:00 UTC
0 8 * * * root cd $PROJECT_DIR && docker compose exec -T web python manage.py send_due_reminders >> /var/log/workflow_cron.log 2>&1

# Send daily task summaries to subscribed users at 18:00 UTC
0 18 * * * root cd $PROJECT_DIR && docker compose exec -T web python manage.py send_daily_summaries >> /var/log/workflow_cron.log 2>&1

# Retry failed outgoing webhook deliveries every 5 minutes
*/5 * * * * root cd $PROJECT_DIR && docker compose exec -T web python manage.py process_webhooks >> /var/log/workflow_cron.log 2>&1

# Retry unconfirmed Telegram/Email notifications every 10 minutes
*/10 * * * * root cd $PROJECT_DIR && docker compose exec -T web python manage.py retry_notifications >> /var/log/workflow_cron.log 2>&1
```

Apply permissions:
```bash
chmod 644 /etc/cron.d/workflow-enterprise
```

---

## 6. SSL/TLS Termination & Public Ingress

While Gunicorn directly binds `0.0.0.0:8000`, public HTTPS termination can be achieved effortlessly via any of the following options:

### Option A: Cloudflare Tunnel (Zero Port Forwarding — Recommended)
```yaml
# /etc/cloudflared/config.yml
tunnel: <TUNNEL_UUID>
credentials-file: /etc/cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: workflow.yourcompany.com
    service: http://localhost:8000
  - service: http_status:404
```

### Option B: Host Caddy Server (Automated Let's Encrypt)
```caddy
# /etc/caddy/Caddyfile
workflow.yourcompany.com {
    reverse_proxy localhost:8000
}
```

---

## 7. Zero-Downtime Rolling Update Runbook

When deploying updates or bug fixes to production:

```bash
cd /opt/workflow-enterprise

# 1. Pull latest code
git pull origin main

# 2. Rebuild the application image
docker compose build web

# 3. Apply schema migrations
docker compose run --rm web python manage.py migrate --noinput

# 4. Collect static assets
docker compose run --rm web python manage.py collectstatic --noinput

# 5. Restart web container
docker compose up -d --no-deps web

# 6. Verify health
curl -f http://localhost:8000/health/
```

---

## 8. Troubleshooting & Operational Runbooks

### 1. Database Connection Failure
- Check PostgreSQL container logs: `docker compose logs db`
- Verify credentials in `.env` match `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD`.
- Confirm container health: `docker compose exec db pg_isready -U workflow_prod_user -d workflow_enterprise_prod`.

### 2. Static Assets Not Loading (404s)
- Verify `collectstatic` was run: `docker compose exec web python manage.py collectstatic --noinput`.
- Ensure `static_volume` is mounted correctly in `compose.yaml`.

### 3. Permission Errors on Media Uploads
- Fix directory ownership inside the persistent volume:
  ```bash
  docker compose exec -u 0 web chown -R appuser:appuser /app/media /app/staticfiles
  ```

### 4. Container Won't Start (Entrypoint Failure)
- Check web container logs: `docker compose logs web`.
- Verify `entrypoint.sh` is executable (`chmod +x entrypoint.sh`).
