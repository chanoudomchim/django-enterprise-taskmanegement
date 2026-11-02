# WorkFlow Enterprise (SaaS Work Management Platform)

A production-grade, multi-tenant enterprise work management and task coordination platform built with **Python 3.12**, **Django 5.2 LTS**, **PostgreSQL 16**, and **Redis 7**.

---

## Architectural Principles & Strict Constraints

- **Multi-Tenant Modular Monolith**: Shared-database, shared-schema architecture enforced strictly via tenant foreign keys (`TenantModel`, `TenantManager`, `TenantMiddleware`).
- **Direct Gunicorn Binding**: Zero Nginx container. Gunicorn binds directly to `0.0.0.0:8000 -> 8000`.
- **Zero Celery / Zero Celery Beat**: Asynchronous background jobs and cron executions run via standard host cron invoking explicit Django management commands.
- **Dedicated Redis Caching**: Redis 7 is used exclusively for application caching and rate limiting with tenant-isolated key prefixes (`get_tenant_cache`, `set_tenant_cache`).
- **Deterministic Seed Engine**: Idempotent generator delivering **$\ge 2,080$** realistic, interconnected database records across 14 models with automatic verification and safe reset.

---

## Tech Stack

| Layer | Component | Description |
|---|---|---|
| **Runtime** | Python 3.12-slim | Non-root containerized application user (`appuser`, UID 1000) |
| **Framework** | Django 5.2 LTS | Multi-tenant modular monolith with Custom UUID User model |
| **Application Server**| Gunicorn 23.0 | WSGI server with 4 worker processes |
| **Database** | PostgreSQL 16 (Alpine) | Persistent volume, indexed tenant FKs, connection pooling |
| **Cache Engine** | Redis 7 (Alpine) | Key-value store for Django view & object caching |
| **Static Delivery**| WhiteNoise 6.8 | Compressed manifest static files storage |
| **Frontend** | Bootstrap 5.3 + HTMX 2.0 | Dynamic responsive UI, dark/light theme, Chart.js analytics |

---

## Quickstart with Docker Compose

### 1. Clone & Configure Environment
```bash
git clone <repository-url>
cd django-enterprise-taskmanegement
cp .env.example .env
```

### 2. Build & Launch Containers
```bash
docker compose up -d --build
```
Verify container health:
```bash
docker compose ps
```
The three core services (`web`, `db`, `redis`) should all report status `healthy`.

### 3. Apply Migrations & Collect Static Files
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

### 4. Seed Demo Dataset ($\ge 2,080$ Records)
```bash
docker compose exec web python manage.py seed_demo --reset
```

### 5. Verify Database Integrity & Demo Counts
```bash
docker compose exec web python manage.py verify_demo
```

### 6. Access Application
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Default Demo Accounts

All demo accounts share the password: **`WorkflowDemo2026!`** (configurable via `DEMO_PASSWORD` in `.env`).

| Role | Email | Superuser | Staff | Workspace Access |
|---|---|:---:|:---:|---|
| **Platform Administrator** | `admin@workflow.local` | Yes | Yes | All Workspaces & Django Admin |
| **Organization Owner** | `owner@workflow.local` | No | Yes | Full Org Administration |
| **Workspace Manager** | `manager@workflow.local` | No | Yes | Projects, Teams & Approvals |
| **Project Manager** | `projectmanager@workflow.local` | No | No | Assigned Projects & Tasks |
| **Employee** | `employee@workflow.local` | No | No | Task Execution & Time Tracking |

*Plus 95 additional simulated employee accounts (`user001@workflow.local` through `user095@workflow.local`) distributed across 10 organizations.*

---

## Automated Test Suite

Run the full automated test suite (85 unit tests across all 15 applications):
```bash
docker compose exec web python manage.py test
```

---

## Scheduled Background Jobs (Host Cron)

In compliance with the Zero-Celery constraint, background operations execute via standard cron:

```cron
# Process recurring task schedules every hour
0 * * * * docker compose -f /path/to/compose.yaml exec -T web python manage.py process_recurring_tasks

# Send task due reminders daily at 08:00 UTC
0 8 * * * docker compose -f /path/to/compose.yaml exec -T web python manage.py send_due_reminders

# Dispatch daily activity summaries at 18:00 UTC
0 18 * * * docker compose -f /path/to/compose.yaml exec -T web python manage.py send_daily_summaries

# Retry failed outgoing webhook deliveries every 5 minutes
*/5 * * * * docker compose -f /path/to/compose.yaml exec -T web python manage.py process_webhooks
```

---

## Documentation

Detailed architectural and operational documentation is located in the `docs/` directory:
- [Architecture & Planning](docs/architecture.md)
- [Entity-Relationship Diagram (ERD)](docs/er-diagram.md)
- [Production Deployment Guide](docs/deployment.md)
- [Seed Data & Demo Dataset Guide](docs/seed-data.md)
- [Backup & Disaster Recovery](docs/backup-restore.md)
- [REST API & Webhooks Documentation](docs/api.md)
- [Application Security Architecture](docs/security.md)

