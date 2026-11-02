# Seed Data & Demo Dataset Documentation — WorkFlow Enterprise

This document provides a comprehensive guide to the **Deterministic Seed Data Engine**, automated verification suite, and safe data cleanup procedures for WorkFlow Enterprise.

---

## 1. Overview & Architectural Goals

The seeding engine generates a realistic, interconnected dataset of **at least 2,080 database records** across 14 core domain models. 

### Core Requirements Satisfied:
- **Reproducibility**: Uses deterministic pseudorandom generation (`random.seed(42)`), guaranteeing identical data across developer machines, staging clusters, and automated CI pipelines.
- **Relational Integrity**: Enforces strict foreign key consistency across organizations, departments, teams, projects, tasks, comments, time entries, notifications, approvals, and attachments.
- **Multi-Tenant Isolation**: Zero cross-tenant leakage; every child entity strictly inherits or validates against its parent organization's primary key.
- **Production Guardrails**: The seeder and reset commands strictly refuse execution when `DEBUG=False` unless the explicit `--force-production` flag is provided.
- **Zero-Celery Native**: Executes within standard Django atomic database transactions (`transaction.atomic()`) without external worker dependencies.

---

## 2. Seed Dataset Breakdown ($\ge 2,080$ Records)

The seed engine creates or ensures at least the following record volumes:

| Model / Entity | App | Target Minimum | Typical Seed Count | Description |
|---|---|:---:|:---:|---|
| **Organizations** | `organizations` | 10 | 10 | 10 multi-tenant enterprise companies with custom branding and settings |
| **Users** | `accounts` | 100 | 100 | 5 primary demo role accounts + 95 distributed employee accounts |
| **Departments** | `departments` | 30 | 30 | 3 functional departments per organization (Engineering, Product, Operations) |
| **Teams** | `departments` | 50 | 50 | 5 teams per organization mapped to departments with assigned team leads |
| **Projects** | `projects` | 100 | 100 | 10 projects per organization with realistic budgets, timelines, and statuses |
| **Project Memberships**| `projects` | 200 | 200 | 2 members assigned per project (Project Manager and Member) |
| **Tasks** | `tasks` | 1,000 | 1,000 | 10 tasks per project with varied statuses, priorities, and assignments |
| **Comments** | `collaboration` | 200 | 200 | Realistic task discussion notes, mentions, and threaded responses |
| **Time Entries** | `time_tracking` | 100 | 100 | Logged work hours (0.5h to 4h) with billing rates and duration seconds |
| **Notifications** | `notifications` | 100 | 100 | In-app notification alerts across 5 operational event types |
| **Audit Logs** | `audit` | 100 | 100 | Immutable compliance audit logs with IP addresses and JSON deltas |
| **Approval Requests** | `approvals` | 50 | 50 | Multi-stage managerial sign-off requests linked to workflows |
| **Attachment Metadata**| `collaboration` | 20 | 20 | Secure attachments (`.pdf`, `.png`, `.docx`, `.xlsx`) with valid file sizes |
| **Task Categories** | `tasks` | 20 | 20 | Standard organizational categories (Feature, Bug, Security, etc.) |
| **TOTAL CORE RECORDS** | | **2,080** | **2,080+** | **Fully interconnected relational graph** |

*Note: Additional relational records (e.g., `TaskAssignment`, `OrganizationSettings`, `Subscription`, `RolePermission`, `TeamMembership`) are automatically generated to maintain rich business relationships.*

---

## 3. Demo User Accounts

All demo accounts share the uniform default password: **`WorkflowDemo2026!`** (configurable via the `DEMO_PASSWORD` environment variable).

| Role | Email | Superuser | Staff | Workspace Description |
|---|---|:---:|:---:|---|
| **Platform Administrator** | `admin@workflow.local` | Yes | Yes | Superuser with administrative bypass across all tenants and Django Admin. |
| **Organization Owner** | `owner@workflow.local` | No | Yes | Primary owner of Acme Corporation with full workspace billing & settings control. |
| **Workspace Manager** | `manager@workflow.local` | No | Yes | Operational manager overseeing projects, departments, and approval workflows. |
| **Project Manager** | `projectmanager@workflow.local` | No | No | Manages assigned projects, sprint planning, and task allocations. |
| **Employee** | `employee@workflow.local` | No | No | Standard employee logging time, executing tasks, and participating in comments. |

### Additional Employee Accounts
- 95 accounts: `user001@workflow.local` through `user095@workflow.local`.
- Distributed evenly across the 10 seeded enterprise organizations.
- Each user has verified email status, active account flag, and realistic names.

---

## 4. Seeded Organizations

The seeder provisions 10 realistic enterprise organizations with custom primary colors, active subscriptions, and settings:

1. **Acme Corporation** (`acme-corp`) — Primary demo organization containing all 5 key demo role accounts.
2. **Globex Corporation** (`globex-corp`)
3. **Initech Technologies** (`initech-tech`)
4. **Umbrella Enterprise** (`umbrella-enterprise`)
5. **Stark Industries** (`stark-industries`)
6. **Wayne Enterprises** (`wayne-enterprises`)
7. **Cyberdyne Systems** (`cyberdyne-systems`)
8. **Soylent Corporation** (`soylent-corp`)
9. **Massive Dynamic** (`massive-dynamic`)
10. **Hooli Cloud** (`hooli-cloud`)

---

## 5. Execution Commands & Workflows

### 5.1 Standard Seeding
Populate the database with the full 2,080-record dataset:
```bash
docker compose exec web python manage.py seed_demo
```

### 5.2 Clean Reset & Fresh Seeding (Recommended)
Purge previous demo records before generating a fresh dataset:
```bash
docker compose exec web python manage.py seed_demo --reset
```

### 5.3 Custom Scaled Seeding
Override default entity quotas for stress testing or custom benchmarks:
```bash
docker compose exec web python manage.py seed_demo \
  --organizations 10 \
  --users 150 \
  --projects 120 \
  --tasks 1500 \
  --comments 300 \
  --time-entries 200
```

### 5.4 Command Line Options Reference

| Flag | Type | Default | Description |
|---|:---:|:---:|---|
| `--organizations` | `int` | 10 | Total demo organizations to generate. |
| `--users` | `int` | 100 | Total demo user accounts to generate. |
| `--departments` | `int` | 30 | Total department records to generate. |
| `--teams` | `int` | 50 | Total working team records to generate. |
| `--projects` | `int` | 100 | Total project records to generate. |
| `--tasks` | `int` | 1000 | Total task entities to generate. |
| `--comments` | `int` | 200 | Total task comment records to generate. |
| `--time-entries` | `int` | 100 | Total logged time entries to generate. |
| `--notifications`| `int` | 100 | Total in-app notification records. |
| `--audit-logs` | `int` | 100 | Total compliance audit log events. |
| `--approval-requests`| `int`| 50 | Total workflow approval instances. |
| `--attachments` | `int` | 20 | Total attachment metadata entries. |
| `--categories` | `int` | 20 | Total task categorization tags. |
| `--reset` | `bool` | `False` | Purges existing demo records before running. |
| `--force-production`| `bool` | `False` | Bypasses the production `DEBUG=False` safety lock. |
| `--password` | `str` | `None` | Overrides the default demo password. |

---

## 6. Automated Verification Engine (`verify_demo`)

Run the automated verification suite to audit database integrity and record counts:
```bash
docker compose exec web python manage.py verify_demo
```

### Verification Checks Performed:
1. **Quantity Thresholds**: Validates that all 14 models meet or exceed minimum record targets.
2. **Account Authentication**: Verifies that `admin@workflow.local`, `owner@workflow.local`, `manager@workflow.local`, `projectmanager@workflow.local`, and `employee@workflow.local` exist and authenticate with the expected password.
3. **Cross-Tenant Isolation Checks**:
   - $\text{Tasks with } \text{Task.org} \ne \text{Project.org} = 0$.
   - $\text{Time entries with } \text{TimeEntry.org} \ne \text{Project.org} = 0$.
   - $\text{Comments with } \text{Comment.org} \ne \text{Task.org} = 0$.
   - $\text{Approval requests with } \text{Request.org} \ne \text{Workflow.org} = 0$.
4. **Exit Codes**: Returns `0` if all checks pass; returns `1` if any check fails (enabling easy CI/CD assertions).

---

## 7. Safe Cleanup Command (`clear_demo`)

To delete all seeded demo records without modifying migrations, database schema, or production users:
```bash
docker compose exec web python manage.py clear_demo --no-input
```

### Safety Logic:
- Identifies demo records by `is_demo=True` and demo email domains (`@workflow.local`).
- Cascading deletion cleans related tasks, comments, time entries, notifications, and approvals within atomic transactions.
- Does not affect non-demo organizations or real user accounts.
- Refuses execution if `DEBUG=False` unless `--force-production` is supplied.

