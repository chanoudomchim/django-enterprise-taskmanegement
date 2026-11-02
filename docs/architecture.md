# WorkFlow Enterprise — System Architecture & Technical Design Specification

**Product Version:** 2.0  
**Architecture:** Multi-Tenant Modular Monolith  
**Tech Stack:** Django 5.2 LTS, Python 3.12, PostgreSQL 16, Redis 7, Gunicorn, Bootstrap 5, HTMX, Alpine.js, Chart.js  

---

## 1. Executive Architecture Overview

WorkFlow Enterprise is an enterprise-grade work management and collaboration SaaS designed for mid-size to large organizations with complex hierarchy requirements. The system adopts a **Shared-Database, Shared-Schema Multi-Tenant Modular Monolith** architecture.

### Key Architectural Tenets
1. **Zero Celery / Zero Nginx Mandate**:
   - The application relies directly on Gunicorn for HTTP serving.
   - Redis 7 is used strictly for caching (`django-redis` / RedisCache) and session acceleration.
   - Asynchronous and periodic tasks are handled via lightweight database-backed job models and scheduled Django management commands triggered via host cron.
2. **Strict Multi-Tenant Isolation**:
   - Every tenant-owned record is bound to an `Organization`.
   - Isolation is enforced across five layers: Model/QuerySet (`TenantModel`), Service Layer, View Layer (`TenantContextMixin`), REST API (`TenantFilterBackend`), and File Storage (Protected file serving).
3. **Enterprise RBAC**:
   - Hierarchical and granular permission assignments per organization.
   - Built-in roles (Super Admin, Org Owner, Org Admin, Dept Manager, Project Manager, Team Leader, Employee, Guest) plus organization-defined custom roles.
4. **Resilient Seed & Verification Engine**:
   - Deterministic demo generator supporting 2,000+ interconnected realistic records with strict referential integrity.

---

## 2. Infrastructure & Docker Deployment Topology

The production and development environments operate with **exactly three core services**:

```
+-----------------------------------------------------------------------------------+
| Host System (Port Mapping 8000:8000)                                              |
|                                                                                   |
|  [Browser / API Client]                                                           |
|             |                                                                     |
|             v (Host Port 8000 -> Container Port 8000)                             |
|  +-----------------------------------------------------------------------------+  |
|  | web container (python:3.12-slim)                                            |  |
|  | - Non-root user: `appuser` (UID 1000)                                       |  |
|  | - Gunicorn: config.wsgi:application --bind 0.0.0.0:8000                     |  |
|  | - Django 5.2 LTS + Whitenoise (static files)                                |  |
|  | - Healthcheck: curl -f http://localhost:8000/health/ || exit 1               |  |
|  +-----------------------------------------------------------------------------+  |
|             |                                                  |                  |
|             | (Internal Docker Network: `workflow_network`)     |                  |
|             v                                                  v                  |
|  +------------------------------------+   +------------------------------------+  |
|  | db container (postgres:16-alpine)  |   | redis container (redis:7-alpine)   |  |
|  | - Port: 5432 (Internal only)       |   | - Port: 6379 (Internal only)       |  |
|  | - Healthcheck: pg_isready          |   | - Healthcheck: redis-cli ping      |  |
|  | - Volume: postgres_data            |   | - Volume: redis_data               |  |
|  +------------------------------------+   +------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Scheduled Management Commands (Replacing Celery)
Host-level crontab triggers Django commands inside the `web` container:
- `python manage.py send_due_reminders` (Every 15 minutes)
- `python manage.py process_recurring_tasks` (Daily at midnight)
- `python manage.py send_daily_summaries` (Daily at 08:00 AM)
- `python manage.py process_webhooks` (Every 5 minutes for retry delivery)
- `python manage.py process_ai_jobs` (Every 1 minute for queued AI generations)

---

## 3. Modular Monolith Directory Structure

```
django-enterprise-taskmanegement/
├── .dockerignore
├── .env.example
├── .gitignore
├── compose.yaml
├── Dockerfile
├── manage.py
├── README.md
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── cache.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── development.py
│       └── production.py
├── apps/
│   ├── accounts/          # User, UserProfile, UserSession, EmailVerification
│   ├── organizations/     # Organization, Membership, Invitation, Settings, Subscription
│   ├── rbac/              # OrganizationRole, PermissionAssignment, RolePermission
│   ├── departments/       # Department, DepartmentMembership, Team, TeamMembership
│   ├── projects/          # Project, ProjectMembership, ProjectTeam, Milestones, Templates
│   ├── tasks/             # Task, Assignment, Watcher, Category, Label, Dependency, Checklist
│   ├── collaboration/     # Comment, Mention, Attachment, Activity, SavedFilter
│   ├── approvals/         # ApprovalWorkflow, ApprovalStage, ApprovalRequest, Decision
│   ├── time_tracking/     # TimeEntry, ActiveTimer, Timesheet, TimesheetApproval
│   ├── notifications/     # Notification, NotificationPreference, TelegramIntegration
│   ├── automations/       # AutomationRule, AutomationAction, AutomationExecution
│   ├── reports/           # Analytics aggregators, Chart.js views, CSV/Excel/PDF exporters
│   ├── ai_assistant/      # Provider abstraction, UsageRecord, AIGenerationRequest
│   ├── integrations/      # APIClient, WebhookEndpoint, WebhookDelivery
│   └── audit/             # AuditLog (immutable security event ledger)
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── seed_demo.py
│       ├── clear_demo.py
│       ├── verify_demo.py
│       ├── send_due_reminders.py
│       ├── process_recurring_tasks.py
│       ├── send_daily_summaries.py
│       └── process_webhooks.py
├── templates/             # Django templates (Base layout, auth, dashboard, components)
├── static/                # CSS, JavaScript (HTMX, Alpine, Chart.js), Images
├── media/                 # Tenant media and protected uploads
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── tests/                 # Integration, security, and tenant-isolation test suites
```

---

## 4. Multi-Tenant Isolation Architecture

### 4.1 Tenancy Data Model Contract
Every tenant-scoped model inherits from `TenantModel`:
```python
class TenantModel(models.Model):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True
```

### 4.2 Five-Layer Defense Matrix
1. **QuerySet Layer (`TenantQuerySet`)**: Auto-filters queries by `request.tenant` when in tenant context.
2. **View Layer (`TenantContextMixin`)**: Injects current active organization into context and verifies the user has active membership.
3. **Service Layer**: All mutations require explicit `organization` parameter and cross-check object ownership before state transitions.
4. **REST API Layer (`TenantFilterBackend`)**: DRF queries automatically scoped to `request.user`'s active tenant header (`X-Organization-ID`) or default organization.
5. **Storage & Download Layer**: File downloads route through a view (`/media/secure/<uuid>/`) that validates user membership in the file's owning organization.

---

## 5. Seed Data Architecture & Verification Engine

To fulfill the Part 19 mandatory requirement (2,000+ interconnected records):
- **Deterministic Seeding (`seed_demo.py`)**: Uses Python's `random.seed(42)` and `Faker(seed=42)` for repeatable results.
- **Record Distribution**:
  - 10 Organizations
  - 100 Users (with standard credentials like `admin@workflow.local`, `owner@workflow.local`)
  - 30 Departments
  - 50 Teams
  - 100 Projects
  - 200 Project Memberships
  - 1,000 Tasks (Backlog, In Progress, Review, Completed, Overdue across 9 months)
  - 200 Comments
  - 100 Time Entries & Active Timers
  - 100 Notifications
  - 100 Audit Logs
  - 50 Approval Requests & Decisions
  - 20 Attachment Metadata records
  - 20 Task Categories
  - **Total**: ≥ 2,080 records.
- **Verification (`verify_demo.py`)**: Validates foreign key references, tenant boundaries, completion rates, and record count thresholds.
- **Safety Gate**: Rejects running if `DEBUG=False` unless `--force-production-seed` is provided.

---

## 6. Implementation Roadmap

| Phase | Title | Focus & Core Milestones |
|---|---|---|
| **Phase 0** | Architecture & Planning | Specifications, ER Diagram, Requirements Analysis, Master Plan. |
| **Phase 1** | Django Foundation & Docker | Dockerfile, compose.yaml, settings, base templates, health check, Gunicorn setup. |
| **Phase 2** | Authentication & Multi-Tenancy | Custom User model, email login, Organization, Membership, Invitations, Tenant Switcher. |
| **Phase 3** | RBAC, Departments & Teams | Permission matrix, custom roles, Department/Team hierarchy, Employee directory. |
| **Phase 4** | Projects & Task Management | Project lifecycle, Task model, Checklists, Dependencies, Categories, Recurrence. |
| **Phase 5** | Enterprise Frontend & Dashboards | Base layout, Dark/Light mode, Kanban board, Gantt, Calendar, List views (HTMX/Alpine). |
| **Phase 6** | Collaboration & Approvals | Comments, mentions, activity log, multi-stage approval workflows, file attachments. |
| **Phase 7** | Time Tracking & Timesheets | Active timers, manual time logs, weekly/monthly timesheets, manager approval flow. |
| **Phase 8** | Redis Caching & Notifications | Redis cache service, in-app notifications, Telegram Bot integration, host cron reminders. |
| **Phase 9** | REST API & Automations | Versioned DRF endpoints, signed HMAC webhooks, automation rules engine. |
| **Phase 10** | AI Project Assistant | Provider abstraction (OpenAI/Gemini/Anthropic/Mock), task breakdown, risk analysis. |
| **Phase 11** | Analytics, Reports & Audit | Chart.js dashboards, CSV/PDF/Excel exports, immutable security audit logs. |
| **Phase 12** | Seed Data & Production Hardening | 2,080+ seed data generator, verify command, test coverage, security audits. |

