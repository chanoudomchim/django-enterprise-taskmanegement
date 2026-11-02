# WORKFLOW ENTERPRISE
## Updated Product Specification & Implementation Master Prompt

Version: 2.0

Product: WorkFlow Enterprise

Architecture: Multi-Tenant Modular Monolith

Deployment: Docker Compose

Database: PostgreSQL 16

Caching: Redis 7

---

# PART 1 — ROLE AND OBJECTIVE

Act as a Principal Software Architect, Senior Django Developer, PostgreSQL Database Architect, DevOps Engineer, Security Engineer, and UI/UX Designer.

Build a complete enterprise work management SaaS platform named WorkFlow Enterprise.

The platform must support multiple organizations, departments, teams, projects, employees, managers, administrators, and external collaborators.

It must provide:

- Multi-tenant organization management.
- Authentication and authorization.
- Role-based access control.
- Project management.
- Advanced task management.
- Collaboration.
- Approval workflows.
- Time tracking.
- Notifications.
- Telegram integration.
- REST API.
- AI project assistant.
- Analytics and reporting.
- Audit logs.
- Comprehensive demo data.

Build a maintainable, secure, modular Django application.

Do not build a simple CRUD demonstration.

# PART 2 — TECHNOLOGY STACK

## Backend

- Python 3.12.
- Django 5.2 LTS.
- Django ORM.
- Django Authentication.
- Django REST Framework.
- Gunicorn.
- Django Forms and ModelForms.

## Frontend

- Bootstrap 5.
- HTMX.
- Alpine.js.
- Bootstrap Icons.
- Chart.js.
- HTML5.
- CSS3.
- JavaScript.

Use server-rendered Django templates.

Do not use React, Vue, or Node.js.

## Database

- PostgreSQL 16.

## Cache

- Redis 7.

Use Redis only for caching and other explicitly implemented non-Celery use cases.

Do not configure Redis as a Celery broker or result backend.

## Infrastructure

- Docker.
- Docker Compose.
- Python slim base image.
- Gunicorn.
- Docker named volumes.
- Docker internal networks.

## External integrations

- Telegram Bot API.
- SMTP email.
- AI provider abstraction.
- REST API.
- Webhooks.

# PART 3 — INFRASTRUCTURE RESTRICTIONS

The following infrastructure components are explicitly excluded.

DO NOT INSTALL, CREATE, CONFIGURE, OR USE:

- Nginx.
- Celery.
- Celery Worker.
- Celery Beat.
- Celery broker.
- Celery result backend.
- Reverse proxy containers.
- Separate background worker containers.

The application must run directly through Gunicorn.

Expose Django through Docker Compose port mapping.

Example:

Host port 8000 → Container port 8000.

PostgreSQL and Redis must remain internal and must not be publicly exposed by default.

All application functionality must operate without Celery.

# PART 4 — MULTI-TENANT SAAS

Implement shared-database, shared-schema multi-tenancy.

Use organization-scoped records.

Users may belong to multiple organizations.

Implement:

- Organization creation.
- Organization membership.
- Organization invitations.
- Organization switching.
- Organization settings.
- Organization branding.
- Organization status.
- Organization-specific roles.
- Organization-specific permissions.

Every tenant-owned record must be scoped to its organization.

Prevent cross-organization access at the queryset, service, view, API, and file-access layers.

Never trust organization IDs supplied by the frontend without checking membership and permissions.

Add automated tenant-isolation tests.

# PART 5 — AUTHENTICATION

Use a custom Django User model created before the first migration.

Use email as the primary login identifier.

Features:

- Registration.
- Login.
- Logout.
- Email verification.
- Password reset.
- Password change.
- User profile.
- Profile image.
- Account activation.
- Account deactivation.
- Login history.
- Session management.
- Organization invitations.

Use Django's built-in authentication and secure password hashing.

# PART 6 — RBAC

Implement granular, organization-scoped Role-Based Access Control.

Initial roles:

- Platform Super Admin.
- Organization Owner.
- Organization Administrator.
- Department Manager.
- Project Manager.
- Team Leader.
- Employee.
- Guest.

Support custom organization roles and permissions.

Permission categories:

- Organization management.
- Department management.
- Team management.
- Project management.
- Task management.
- Approvals.
- Timesheets.
- Reports.
- Integrations.
- Administration.

Implement backend permission enforcement.

Never depend on frontend navigation visibility as the security mechanism.

# PART 7 — ORGANIZATION AND TEAM MANAGEMENT

Implement:

- Organizations.
- Departments.
- Teams.
- Employee directory.
- Team memberships.
- Department memberships.
- Department managers.
- Team leaders.
- Organization invitations.
- Workspace settings.
- Organization branding.

Users can belong to multiple teams when authorized.

# PART 8 — PROJECT MANAGEMENT

Implement:

- Project creation.
- Project editing.
- Project deletion with safeguards.
- Project members.
- Project teams.
- Project manager.
- Project owner.
- Project milestones.
- Project templates.
- Project budget.
- Project progress.
- Project attachments.
- Project discussions.
- Project activity history.

Project statuses:

- Planning.
- Active.
- On Hold.
- Completed.
- Cancelled.
- Archived.

# PART 9 — TASK MANAGEMENT

Create a comprehensive Task model.

Fields:

- UUID.
- Organization.
- Project.
- Title.
- Description.
- Task key.
- Status.
- Priority.
- Category.
- Created by.
- Assignees.
- Watchers.
- Start date.
- Due date.
- Estimated hours.
- Actual hours.
- Progress.
- Parent task.
- Position.
- Completed date.
- Created date.
- Updated date.

Features:

- Task CRUD.
- Multiple assignees.
- Task categories.
- Labels.
- Priorities.
- Subtasks.
- Checklists.
- Dependencies.
- Recurring tasks.
- Task attachments.
- Comments.
- Mentions.
- Task history.
- Approval requests.
- Task templates.
- Bulk operations.
- Search.
- Filtering.
- Sorting.
- Pagination.
- Saved filters.
- CSV export.

Task statuses:

- Backlog.
- To Do.
- In Progress.
- In Review.
- Blocked.
- Completed.
- Cancelled.

Support configurable organization workflows.

# PART 10 — TASK VIEWS

Implement:

1. Kanban board.
2. List view.
3. Calendar view.
4. Gantt timeline.
5. My Tasks.
6. Assigned by Me.
7. Watching.
8. Due Today.
9. Upcoming.
10. Overdue.
11. Recently Updated.

Use HTMX and Alpine.js for interactions.

Validate all important updates on the backend.

# PART 11 — COLLABORATION

Implement:

- Comments.
- Threaded discussions.
- @mentions.
- Task watchers.
- Attachments.
- Activity feed.
- Internal notes.
- Comment editing.
- Comment deletion.
- Project discussions.

Enforce file upload validation and tenant-aware download permissions.

# PART 12 — APPROVAL MANAGEMENT

Implement:

- Approval requests.
- Approval workflows.
- Multiple approval stages.
- Assigned approvers.
- Approval decisions.
- Rejection reasons.
- Request changes.
- Delegated approval.
- Approval history.
- Approval notifications.

Approval statuses:

- Pending.
- Approved.
- Rejected.
- Cancelled.

Use Django database transactions for critical approval transitions.

Enforce separation of duties where configured.

# PART 13 — TIME TRACKING

Implement:

- Start timer.
- Stop timer.
- Manual time entry.
- Task-based time tracking.
- Project-based reporting.
- Employee timesheets.
- Weekly timesheets.
- Monthly timesheets.
- Estimated versus actual hours.
- Billable and non-billable hours.
- Timesheet approval.
- Timesheet rejection.

Prevent overlapping active timers for the same user.

Use database constraints where appropriate.

# PART 14 — NOTIFICATIONS AND TELEGRAM

Implement:

- In-app notifications.
- Email notifications.
- Telegram notifications.
- Notification preferences.
- Unread notification counter.
- Mark as read.
- Daily notification summaries.
- Weekly notification summaries.

Telegram features:

- Organization Telegram bot configuration.
- Secure Telegram token storage.
- User-to-Telegram account linking.
- Chat ID verification.
- Task assignment notifications.
- Deadline reminders.
- Approval notifications.
- Project notifications.

Support commands:

/start
/help
/mytasks
/overdue
/today

Authenticate Telegram users before returning private information.

## Background processing restrictions

Do not use Celery or any separate background worker.

Implement notifications through:

1. Synchronous delivery for appropriate user-triggered actions.
2. Explicit Django management commands for scheduled processing.
3. Host-level cron jobs to execute scheduled management commands.
4. Database records to track notification delivery attempts.
5. Retry commands for failed notifications.

Example scheduled command:

python manage.py send_due_reminders

Another example:

python manage.py process_recurring_tasks

Another example:

python manage.py send_daily_summaries

Ensure notification delivery is idempotent and duplicate reminders are prevented.

Do not block normal page requests with long-running report generation or AI operations. Provide explicit user-triggered processing with request status tracking and polling where necessary.

# PART 15 — AI PROJECT ASSISTANT

Implement a provider-independent AI module.

Features:

- Generate tasks from project descriptions.
- Generate subtasks.
- Generate project milestones.
- Summarize project progress.
- Summarize discussions.
- Generate meeting action items.
- Identify potential project risks.
- Suggest priorities.
- Answer questions about authorized project information.

Security:

- Enforce organization isolation before retrieving AI context.
- Enforce RBAC.
- Require confirmation before modifying business records.
- Apply rate limits.
- Record AI usage.
- Keep provider credentials in environment variables.
- Allow organizations to disable AI.
- Never execute arbitrary AI-generated SQL or code.

AI operations must be handled synchronously only when execution is predictably short.

For long operations, implement an asynchronous request lifecycle using a database-backed job record and a dedicated management command that can be triggered by host cron or an administrator.

# PART 16 — REST API AND WEBHOOKS

Use Django REST Framework.

Create versioned endpoints:

/api/v1/auth/
/api/v1/organizations/
/api/v1/departments/
/api/v1/teams/
/api/v1/projects/
/api/v1/tasks/
/api/v1/comments/
/api/v1/approvals/
/api/v1/timesheets/
/api/v1/notifications/
/api/v1/reports/

Implement:

- Authentication.
- Organization-aware permissions.
- Pagination.
- Filtering.
- Search.
- Sorting.
- Validation.
- Rate limiting.
- API documentation.

Support signed outgoing webhooks with HMAC, retry history, and delivery records.

Use explicit management commands to retry failed webhook deliveries when necessary.

# PART 17 — ANALYTICS AND REPORTING

Implement:

Organization analytics:
- Total employees.
- Total departments.
- Active projects.
- Completed projects.
- Delayed projects.
- Total tasks.
- Completed tasks.
- Overdue tasks.

Department analytics:
- Assigned tasks.
- Completed tasks.
- Overdue tasks.
- Team workload.
- Logged hours.

Project analytics:
- Project progress.
- Task distribution.
- Milestone completion.
- Deadline performance.
- Budget tracking.
- Estimated versus actual hours.

Employee workload:
- Assigned tasks.
- Active tasks.
- Overdue tasks.
- Upcoming tasks.
- Logged hours.

Use Chart.js.

Support CSV, Excel, and PDF exports.

Apply RBAC and tenant filtering to every report.

# PART 18 — DATABASE MODEL DESIGN

Create separate Django applications.

Accounts:
- User.
- UserProfile.
- UserSession.
- EmailVerification.

Organizations:
- Organization.
- OrganizationMembership.
- OrganizationInvitation.
- OrganizationSettings.
- SubscriptionPlan.
- Subscription.

RBAC:
- OrganizationRole.
- PermissionAssignment.
- RolePermission.
- UserRoleAssignment.

Departments:
- Department.
- DepartmentMembership.
- Team.
- TeamMembership.

Projects:
- Project.
- ProjectMembership.
- ProjectTeam.
- ProjectMilestone.
- ProjectTemplate.

Tasks:
- Task.
- TaskAssignment.
- TaskWatcher.
- TaskCategory.
- TaskLabel.
- TaskDependency.
- TaskChecklist.
- TaskChecklistItem.
- TaskRecurrence.
- TaskCustomField.
- TaskCustomFieldValue.

Collaboration:
- Comment.
- CommentMention.
- Attachment.
- Activity.
- SavedFilter.

Approvals:
- ApprovalWorkflow.
- ApprovalStage.
- ApprovalRequest.
- ApprovalDecision.

Time Tracking:
- TimeEntry.
- ActiveTimer.
- Timesheet.
- TimesheetEntry.
- TimesheetApproval.

Notifications:
- Notification.
- NotificationPreference.
- NotificationDelivery.
- TelegramAccount.
- TelegramIntegration.

Automation:
- AutomationRule.
- AutomationExecution.
- AutomationAction.

AI:
- AIProviderConfiguration.
- AIUsageRecord.
- AIGenerationRequest.

Integrations:
- APIClient.
- WebhookEndpoint.
- WebhookDelivery.

Audit:
- AuditLog.

Additional requirements:

- Use UUID primary keys for externally exposed business records.
- Use organization-scoped uniqueness constraints.
- Add indexes for common filtering and reporting queries.
- Use transactions for important state changes.
- Avoid N+1 queries.
- Use select_related and prefetch_related.
- Use timezone-aware timestamps.
- Use DecimalField for monetary amounts.
- Use JSONField only for appropriate flexible configuration.
- Document important database relationships.
- Create a complete ER diagram.

Create the custom User model before initial migrations.

# PART 19 — SEED DATA SYSTEM

This is a mandatory requirement.

Create a complete and repeatable database seeding system.

The seed system must generate at least 2,000 interconnected database records.

Create:

management/
  __init__.py
  commands/
    __init__.py
    seed_demo.py
    clear_demo.py
    verify_demo.py

Use Django management commands.

## Minimum seed dataset

Generate at least the following records:

| Model | Target |
|---|---:|
| Organizations | 10 |
| Users | 100 |
| Departments | 30 |
| Teams | 50 |
| Projects | 100 |
| Project memberships | 200 |
| Tasks | 1,000 |
| Comments | 200 |
| Time entries | 100 |
| Notifications | 100 |
| Audit logs | 100 |
| Approval requests | 50 |
| Attachment metadata | 20 |
| Task categories | 20 |
| TOTAL | 2,080 |

Additional relationship records are encouraged.

These are minimum target counts, not maximum limits.

## Seed data quality

Seed records must be realistic and interconnected.

Examples:

- Every organization has a valid owner.
- Every department belongs to an organization.
- Every team belongs to an organization and department.
- Every project belongs to an organization.
- Every project has valid members.
- Every task belongs to the correct organization.
- Every task references a valid project.
- Every task has a valid creator.
- Tasks can have multiple assignees.
- Comments belong to real tasks.
- Time entries reference real users and tasks.
- Approval requests reference valid business objects.
- Notifications belong to valid users.
- Audit records reference appropriate actors and resources.

Generate varied values:

Task statuses:
- Backlog.
- To Do.
- In Progress.
- In Review.
- Blocked.
- Completed.
- Cancelled.

Priorities:
- Low.
- Medium.
- High.
- Urgent.

Project statuses:
- Planning.
- Active.
- On Hold.
- Completed.
- Cancelled.

Generate realistic dates distributed across the previous six months and the upcoming three months.

Generate different task completion rates, workloads, and project progress.

Use deterministic random seeds for reproducibility.

## Seed command requirements

Support:

python manage.py seed_demo

python manage.py seed_demo --organizations 10 --users 100 --projects 100 --tasks 1000

python manage.py seed_demo --reset

python manage.py verify_demo

python manage.py clear_demo

Important behavior:

- Use transaction.atomic().
- Use bulk_create where appropriate.
- Use get_or_create for reusable records.
- Prevent duplicate seed records.
- Mark demo records using a dedicated field or reliable demo-data marker.
- Never delete real production data.
- Require explicit confirmation for destructive reset operations.
- Provide a dry-run or preview option where practical.
- Print a summary of generated records.
- Verify all foreign-key relationships.
- Verify the final record count is at least 2,000.

Never generate fake attachment files with invalid references. Generate realistic attachment metadata and optional small sample files if supported.

## Demo accounts

Create:

Platform administrator:
admin@workflow.local

Organization owner:
owner@workflow.local

Organization administrator:
manager@workflow.local

Project manager:
projectmanager@workflow.local

Employee:
employee@workflow.local

Use a configurable demo password.

Document the demo password clearly in the development README.

Never create known demo credentials automatically in production.

The seeding command must refuse to run in production unless an explicit, separately documented override is provided.

# PART 20 — FRONTEND

Create a modern enterprise SaaS dashboard.

Requirements:

- Professional layout.
- Responsive sidebar.
- Top navigation.
- Organization switcher.
- User profile menu.
- Light and dark modes.
- Responsive tables.
- Dashboard cards.
- Interactive charts.
- Task status badges.
- Priority indicators.
- Toast notifications.
- Confirmation modals.
- Loading states.
- Empty states.
- Error states.

Main navigation:

- Overview.
- My Tasks.
- Inbox.
- Projects.
- Teams.
- Departments.
- Calendar.
- Approvals.
- Time Tracking.
- Reports.
- Automations.
- Integrations.
- Organization Settings.

Show navigation according to the user's permissions.

All controls must work.

# PART 21 — DOCKER ARCHITECTURE

Create compose.yaml with exactly three core services.

## web

Build from Dockerfile.

Requirements:

- Python 3.12-slim.
- Django 5.2.
- Gunicorn.
- Non-root application user.
- Environment variables.
- Port mapping 8000:8000.
- Application health check.
- Persistent media and static mounts as appropriate.
- Restart policy.

Gunicorn command:

gunicorn config.wsgi:application --bind 0.0.0.0:8000

## db

Image:

postgres:16-alpine

Requirements:

- Database credentials from environment.
- Persistent named volume.
- Health check using pg_isready.
- Internal network only.
- No public port mapping by default.

## redis

Image:

redis:7-alpine

Requirements:

- Persistent volume if persistence is enabled.
- Health check using redis-cli ping.
- Internal network only.
- No public port mapping by default.

Redis is used for Django caching only.

Do not configure Celery.

## Docker Compose rules

- Use named volumes.
- Use service health checks.
- Use service dependencies with healthy conditions.
- Use environment files.
- Use restart policies.
- Configure appropriate logging.
- Use internal Docker networking.
- Do not install Nginx.
- Do not install Celery.
- Do not create worker services.
- Do not create beat services.
- Do not expose PostgreSQL or Redis publicly.

# PART 22 — PROJECT STRUCTURE

workflow-enterprise/
│
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── cache.py
│
├── apps/
│   ├── accounts/
│   ├── organizations/
│   ├── rbac/
│   ├── departments/
│   ├── projects/
│   ├── tasks/
│   ├── collaboration/
│   ├── approvals/
│   ├── time_tracking/
│   ├── notifications/
│   ├── automations/
│   ├── reports/
│   ├── ai_assistant/
│   ├── integrations/
│   └── audit/
│
├── management/
│   └── commands/
│       ├── seed_demo.py
│       ├── clear_demo.py
│       ├── verify_demo.py
│       ├── send_due_reminders.py
│       ├── process_recurring_tasks.py
│       └── process_webhooks.py
│
├── templates/
├── static/
├── media/
├── scripts/
├── tests/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── .env.example
├── manage.py
└── README.md

Each Django application should have:

- models.py
- views.py
- urls.py
- forms.py
- admin.py
- services.py
- selectors.py where needed
- permissions.py
- tests/
- migrations/

Keep business logic out of large views.

# PART 23 — SECURITY

Implement:

- CSRF protection.
- Secure session cookies.
- Secure password hashing.
- Input validation.
- Output escaping.
- XSS protection.
- SQL injection protection.
- Clickjacking protection.
- Host validation.
- HTTPS enforcement in production.
- Secure cookie configuration.
- Content Security Policy where practical.
- Tenant isolation.
- Object-level permissions.
- API authentication.
- Rate limiting.
- Audit logging.
- File upload validation.
- Secret management.

Production must use DEBUG=False.

Do not commit secrets.

Do not expose database or Redis publicly.

Do not expose private attachments using predictable public URLs.

Do not allow cross-tenant access through APIs, reports, AI, caching, notifications, or integrations.

# PART 24 — TESTING

Write automated tests for:

Authentication:
- Registration.
- Login.
- Logout.
- Password reset.
- Invitations.

Multi-tenancy:
- Organization isolation.
- Project isolation.
- Task isolation.
- Attachment isolation.
- API isolation.
- Notification isolation.

RBAC:
- Role assignment.
- Permission enforcement.
- Custom roles.
- Approval permissions.

Business logic:
- Project CRUD.
- Task CRUD.
- Task dependencies.
- Recurring tasks.
- Approvals.
- Time tracking.
- Timesheets.
- Telegram integration.
- AI authorization.

Seed data:
- Minimum record count.
- Valid foreign keys.
- Correct tenant relationships.
- Idempotency.
- Safe reset behavior.
- Production safety checks.

Infrastructure:
- PostgreSQL connectivity.
- Redis connectivity.
- Gunicorn startup.
- Health checks.
- Docker volumes.

Run tests before declaring any phase complete.

# PART 25 — DATABASE OPERATIONS

Do not run migrations during Docker image building.

Initial setup:

docker compose build

docker compose up -d db redis

docker compose run --rm web python manage.py migrate

docker compose run --rm web python manage.py createsuperuser

docker compose run --rm web python manage.py collectstatic --noinput

docker compose up -d

Generate demo data:

docker compose exec web python manage.py seed_demo

Verify demo data:

docker compose exec web python manage.py verify_demo

Run tests:

docker compose exec web python manage.py test

View logs:

docker compose logs -f web

docker compose logs -f db

docker compose logs -f redis

Access:

http://localhost:8000

# PART 26 — IMPLEMENTATION PHASES

Phase 0: Architecture and planning.

Phase 1: Django foundation and Docker infrastructure.

Phase 2: Authentication and multi-tenancy.

Phase 3: RBAC, departments, and teams.

Phase 4: Projects and task management.

Phase 5: Enterprise frontend and dashboards.

Phase 6: Collaboration and approvals.

Phase 7: Time tracking.

Phase 8: Redis caching, notifications, and Telegram.

Phase 9: REST API, webhooks, and automation.

Phase 10: AI project assistant.

Phase 11: Analytics, reports, and audit logs.

Phase 12: Seed data, comprehensive testing, and production hardening.

For each phase:

1. Explain the objective.
2. Implement the required code.
3. List created and modified files.
4. Generate required migrations.
5. Execute automated tests.
6. Verify Docker services.
7. Report known issues.
8. Provide execution commands.
9. Wait for approval before proceeding.

Do not claim tests passed without executing them.

# PART 27 — FINAL DELIVERABLES

Provide:

- Complete Django source code.
- Database models.
- Database migrations.
- HTML templates.
- CSS and JavaScript.
- Dockerfile.
- compose.yaml.
- .dockerignore.
- .env.example.
- requirements files.
- Seed data commands.
- Automated tests.
- ER diagram.
- Architecture diagram.
- README.
- Deployment documentation.
- Backup and restore documentation.
- API documentation.
- Security documentation.

# FINAL OBJECTIVE

Deliver a functional, secure, multi-tenant enterprise SaaS work management system.

It must run using only:

1. Django + Gunicorn.
2. PostgreSQL.
3. Redis.

The system must not depend on Nginx, Celery, Celery Worker, or Celery Beat.

It must include a repeatable seed data system generating at least 2,000 realistic interconnected records.

Prioritize tenant isolation, RBAC, database integrity, application security, maintainability, and functional correctness.