"""Deterministic demo seed data engine for WorkFlow Enterprise.

Generates at least 2,080 interconnected realistic records across all core models
with zero Celery dependency, strict multi-tenant isolation, and safe idempotent reset.
"""

import os
import random
from datetime import timedelta, date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    SubscriptionPlan,
    Subscription,
)
from apps.rbac.services import seed_default_organization_roles
from apps.departments.models import Department, DepartmentMembership, Team, TeamMembership
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskCategory, TaskAssignment
from apps.collaboration.models import Comment, Attachment
from apps.approvals.models import ApprovalWorkflow, ApprovalStage, ApprovalRequest
from apps.time_tracking.models import TimeEntry
from apps.notifications.models import Notification
from apps.audit.models import AuditLog

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with >= 2,080 realistic, interconnected demo records."

    def add_arguments(self, parser):
        parser.add_argument("--organizations", type=int, default=10, help="Number of demo organizations (min 10)")
        parser.add_argument("--users", type=int, default=100, help="Number of demo users (min 100)")
        parser.add_argument("--departments", type=int, default=30, help="Number of departments (min 30)")
        parser.add_argument("--teams", type=int, default=50, help="Number of teams (min 50)")
        parser.add_argument("--projects", type=int, default=100, help="Number of projects (min 100)")
        parser.add_argument("--tasks", type=int, default=1000, help="Number of tasks (min 1000)")
        parser.add_argument("--comments", type=int, default=200, help="Number of comments (min 200)")
        parser.add_argument("--time-entries", type=int, default=100, help="Number of time entries (min 100)")
        parser.add_argument("--notifications", type=int, default=100, help="Number of notifications (min 100)")
        parser.add_argument("--audit-logs", type=int, default=100, help="Number of audit logs (min 100)")
        parser.add_argument("--approval-requests", type=int, default=50, help="Number of approval requests (min 50)")
        parser.add_argument("--attachments", type=int, default=20, help="Number of attachments (min 20)")
        parser.add_argument("--categories", type=int, default=20, help="Number of task categories (min 20)")
        parser.add_argument("--reset", action="store_true", help="Reset all existing demo records before seeding")
        parser.add_argument("--force-production", action="store_true", help="Allow running when DEBUG is False")
        parser.add_argument("--password", type=str, default=None, help="Password for generated demo accounts")

    def handle(self, *args, **options):
        is_debug = getattr(settings, "DEBUG", False)
        force_prod = options.get("force_production", False)

        if not is_debug and not force_prod:
            raise CommandError(
                "Refusing to seed demo data in a production environment (DEBUG=False) "
                "without explicit --force-production override."
            )

        demo_password = options.get("password") or os.environ.get("DEMO_PASSWORD", "WorkflowDemo2026!")

        # Enforce deterministic random generation for reproducibility
        random.seed(42)

        self.stdout.write(self.style.NOTICE("Initializing WorkFlow Enterprise Deterministic Seed Engine..."))

        if options.get("reset"):
            self.stdout.write(self.style.WARNING("Reset flag provided. Purging existing demo records..."))
            with transaction.atomic():
                Organization.objects.filter(is_demo=True).delete()
                User.objects.filter(is_demo=True).delete()
                User.objects.filter(email__endswith="@workflow.local").delete()
            self.stdout.write(self.style.SUCCESS("Existing demo records cleared."))

        with transaction.atomic():
            stats = self._execute_seed(options, demo_password)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("WORKFLOW ENTERPRISE DEMO SEEDING COMPLETE"))
        self.stdout.write("=" * 60)
        total_records = sum(stats.values())
        for model_name, count in stats.items():
            self.stdout.write(f"  * {model_name:<26}: {count:>6} records")
        self.stdout.write("-" * 60)
        self.stdout.write(self.style.SUCCESS(f"  * TOTAL SEEDED RECORDS     : {total_records:>6} records (Target: >= 2,080)"))
        self.stdout.write("=" * 60)
        self.stdout.write("\nKey Demo User Credentials (Password: " + demo_password + "):")
        self.stdout.write("  - Platform Admin   : admin@workflow.local (Superuser)")
        self.stdout.write("  - Org Owner        : owner@workflow.local")
        self.stdout.write("  - Workspace Manager: manager@workflow.local")
        self.stdout.write("  - Project Manager  : projectmanager@workflow.local")
        self.stdout.write("  - Employee         : employee@workflow.local\n")

    def _execute_seed(self, options, demo_password):
        stats = {}
        now = timezone.now()
        today = timezone.localdate()

        # 1. Subscription Plans
        enterprise_plan, _ = SubscriptionPlan.objects.get_or_create(
            code="enterprise",
            defaults={
                "name": "Enterprise Unlimited",
                "max_users": 1000,
                "max_projects": 500,
                "price": Decimal("299.00"),
                "billing_interval": "monthly",
            },
        )
        SubscriptionPlan.objects.get_or_create(
            code="pro",
            defaults={
                "name": "Professional",
                "max_users": 50,
                "max_projects": 50,
                "price": Decimal("79.00"),
                "billing_interval": "monthly",
            },
        )

        # 2. Users (100 total)
        self.stdout.write("Seeding Users...")
        users = []
        user_specs = [
            ("admin@workflow.local", "Platform", "Admin", True, True),
            ("owner@workflow.local", "Alexander", "Owner", True, False),
            ("manager@workflow.local", "Marcus", "Manager", True, False),
            ("projectmanager@workflow.local", "Patricia", "Manager", False, False),
            ("employee@workflow.local", "Ethan", "Employee", False, False),
        ]

        first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Oliver", "Sophia", "Lucas", "Mia",
                       "Benjamin", "Charlotte", "Henry", "Amelia", "Alexander", "Harper", "William", "Evelyn"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                      "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]

        # Key demo accounts
        for email, fn, ln, staff, superuser in user_specs:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "is_staff": staff,
                    "is_superuser": superuser,
                    "is_active": True,
                    "is_verified": True,
                    "is_demo": True,
                },
            )
            if created or not user.check_password(demo_password):
                user.set_password(demo_password)
                user.is_demo = True
                user.is_verified = True
                user.save()
            users.append(user)

        # Fill remaining users up to 100
        target_users = max(options.get("users", 100), 100)
        while len(users) < target_users:
            idx = len(users) - 4
            email = f"user{idx:03d}@workflow.local"
            fn = random.choice(first_names)
            ln = random.choice(last_names)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                    "is_verified": True,
                    "is_demo": True,
                },
            )
            if created or not user.check_password(demo_password):
                user.set_password(demo_password)
                user.is_demo = True
                user.is_verified = True
                user.save()
            users.append(user)

        stats["Users"] = len(users)

        # 3. Organizations (10 total)
        self.stdout.write("Seeding Organizations & Subscriptions...")
        org_data = [
            ("Acme Corporation", "acme-corp", "#0d6efd"),
            ("Globex Corporation", "globex-corp", "#198754"),
            ("Initech Technologies", "initech-tech", "#6f42c1"),
            ("Umbrella Enterprise", "umbrella-enterprise", "#dc3545"),
            ("Stark Industries", "stark-industries", "#fd7e14"),
            ("Wayne Enterprises", "wayne-enterprises", "#212529"),
            ("Cyberdyne Systems", "cyberdyne-systems", "#0dcaf0"),
            ("Soylent Corporation", "soylent-corp", "#20c997"),
            ("Massive Dynamic", "massive-dynamic", "#d63384"),
            ("Hooli Cloud", "hooli-cloud", "#ffc107"),
        ]

        target_orgs = max(options.get("organizations", 10), 10)
        organizations = []
        for i in range(target_orgs):
            if i < len(org_data):
                name, slug, color = org_data[i]
            else:
                name = f"Enterprise Tenant {i+1}"
                slug = f"tenant-{i+1}"
                color = "#0d6efd"

            org_owner = users[1] if i == 0 else users[(i * 9) % len(users)]
            org, _ = Organization.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "primary_color": color,
                    "status": "active",
                    "is_active": True,
                    "is_demo": True,
                    "created_by": org_owner,
                },
            )
            org.is_demo = True
            org.save(update_fields=["is_demo"])

            # Settings
            OrganizationSettings.objects.get_or_create(
                organization=org,
                defaults={
                    "timezone": "UTC",
                    "time_tracking_enabled": True,
                    "ai_assistant_enabled": True,
                    "telegram_notifications_enabled": True,
                },
            )

            # Subscription
            Subscription.objects.get_or_create(
                organization=org,
                defaults={
                    "plan": enterprise_plan,
                    "status": "active",
                },
            )

            # RBAC Roles
            seed_default_organization_roles(org)

            organizations.append(org)

        stats["Organizations"] = len(organizations)

        # Memberships: Acme Corp has all primary demo accounts
        primary_org = organizations[0]
        OrganizationMembership.objects.get_or_create(
            organization=primary_org, user=users[0], defaults={"role": "owner", "is_default": True}
        )
        OrganizationMembership.objects.get_or_create(
            organization=primary_org, user=users[1], defaults={"role": "owner", "is_default": True}
        )
        OrganizationMembership.objects.get_or_create(
            organization=primary_org, user=users[2], defaults={"role": "admin", "is_default": True}
        )
        OrganizationMembership.objects.get_or_create(
            organization=primary_org, user=users[3], defaults={"role": "manager", "is_default": True}
        )
        OrganizationMembership.objects.get_or_create(
            organization=primary_org, user=users[4], defaults={"role": "member", "is_default": True}
        )

        # Distribute remaining users into orgs
        for idx, u in enumerate(users[5:], start=5):
            assigned_org = organizations[idx % len(organizations)]
            OrganizationMembership.objects.get_or_create(
                organization=assigned_org,
                user=u,
                defaults={"role": "member", "is_default": True},
            )

        # 4. Task Categories (>= 20)
        self.stdout.write("Seeding Task Categories...")
        cat_templates = [
            ("Feature", "#0d6efd", "bi-stars"),
            ("Bug Fix", "#dc3545", "bi-bug"),
            ("Security", "#fd7e14", "bi-shield-check"),
            ("Enhancement", "#198754", "bi-arrow-up-circle"),
            ("Documentation", "#6c757d", "bi-book"),
        ]
        categories = []
        for org in organizations:
            for cname, ccolor, cicon in cat_templates[:2]:
                cat, _ = TaskCategory.objects.get_or_create(
                    organization=org,
                    name=cname,
                    defaults={"color": ccolor, "icon": cicon},
                )
                categories.append(cat)

        stats["Task Categories"] = len(categories)

        # 5. Departments (>= 30)
        self.stdout.write("Seeding Departments & Teams...")
        dept_templates = [
            ("Engineering", "ENG"),
            ("Product & Design", "PRD"),
            ("Operations & Support", "OPS"),
        ]
        departments = []
        for org in organizations:
            org_members = [
                m.user for m in OrganizationMembership.objects.filter(organization=org).select_related("user")
            ]
            mgr = org_members[0] if org_members else users[1]
            for dname, dcode in dept_templates:
                dept, _ = Department.objects.get_or_create(
                    organization=org,
                    code=f"{dcode}-{org.slug[:3].upper()}",
                    defaults={"name": dname, "manager": mgr},
                )
                departments.append(dept)
                # Membership
                for u in org_members[:3]:
                    DepartmentMembership.objects.get_or_create(
                        department=dept, user=u, defaults={"role_in_department": "Member"}
                    )

        stats["Departments"] = len(departments)

        # 6. Teams (>= 50)
        team_names = ["Backend Platform", "Frontend Web", "Mobile Apps", "DevOps & SRE", "QA & Reliability"]
        teams = []
        for org in organizations:
            org_depts = [d for d in departments if d.organization_id == org.id]
            org_members = [
                m.user for m in OrganizationMembership.objects.filter(organization=org).select_related("user")
            ]
            lead = org_members[0] if org_members else users[1]
            for t_idx, tname in enumerate(team_names):
                assigned_dept = org_depts[t_idx % len(org_depts)] if org_depts else None
                team, _ = Team.objects.get_or_create(
                    organization=org,
                    name=f"{org.name} - {tname}",
                    defaults={"department": assigned_dept, "lead": lead},
                )
                teams.append(team)
                for u in org_members[:2]:
                    TeamMembership.objects.get_or_create(
                        team=team, user=u, defaults={"role_in_team": "Engineer"}
                    )

        stats["Teams"] = len(teams)

        # 7. Projects (>= 100)
        self.stdout.write("Seeding Projects & Memberships...")
        project_templates = [
            ("Core Platform API v2", "API"),
            ("Mobile iOS & Android App", "MOB"),
            ("Enterprise SSO & Security", "SSO"),
            ("Cloud Migration to Kubernetes", "K8S"),
            ("Customer Self-Service Portal", "PRT"),
            ("Data Analytics Pipeline", "DAT"),
            ("Realtime Telemetry & Metrics", "TEL"),
            ("Billing & Subscription Revamp", "BIL"),
            ("AI Workflow Automation", "AIW"),
            ("Compliance & Audit Overhaul", "AUD"),
        ]

        projects = []
        project_memberships = []
        p_statuses = ["active", "active", "planning", "completed", "on_hold"]
        p_priorities = ["urgent", "high", "medium", "low"]

        for o_idx, org in enumerate(organizations):
            org_members = [
                m.user for m in OrganizationMembership.objects.filter(organization=org).select_related("user")
            ]
            owner = org_members[0] if org_members else users[1]
            manager = org_members[1] if len(org_members) > 1 else owner

            for p_idx, (pname, pcode) in enumerate(project_templates):
                key = f"{pcode}{o_idx+1}"
                status = p_statuses[p_idx % len(p_statuses)]
                priority = p_priorities[p_idx % len(p_priorities)]
                budget = Decimal(random.randint(25, 250) * 1000)

                start_d = today - timedelta(days=random.randint(30, 180))
                target_d = today + timedelta(days=random.randint(30, 90))

                proj, _ = Project.objects.get_or_create(
                    organization=org,
                    key=key,
                    defaults={
                        "name": f"{pname} ({org.name[:12]})",
                        "owner": owner,
                        "manager": manager,
                        "status": status,
                        "priority": priority,
                        "budget": budget,
                        "start_date": start_d,
                        "target_end_date": target_d,
                        "is_demo": True,
                    },
                )
                proj.is_demo = True
                proj.save(update_fields=["is_demo"])
                projects.append(proj)

                # Project Memberships (2 per project)
                pm1, _ = ProjectMembership.objects.get_or_create(
                    project=proj, user=owner, defaults={"role": "manager"}
                )
                project_memberships.append(pm1)

                second_user = org_members[2] if len(org_members) > 2 else users[4]
                pm2, _ = ProjectMembership.objects.get_or_create(
                    project=proj, user=second_user, defaults={"role": "member"}
                )
                project_memberships.append(pm2)

        stats["Projects"] = len(projects)
        stats["Project Memberships"] = len(project_memberships)

        # 8. Tasks (>= 1,000)
        self.stdout.write("Seeding Tasks & Assignments (Target: 1,000)...")
        task_titles = [
            "Implement JWT and session authentication refresh handler",
            "Optimize PostgreSQL connection pooling and transaction isolation",
            "Design responsive Kanban board layout with HTMX drag-and-drop",
            "Write comprehensive multi-tenant isolation unit tests",
            "Set up Redis caching layer with tenant key prefixes",
            "Build executive analytics dashboard with Chart.js visualizations",
            "Refactor REST API serializers with TenantFilterBackend",
            "Configure outbound webhook deliveries with HMAC-SHA256 signatures",
            "Implement approval request state machine with multi-stage review",
            "Create timesheet submission and manager review approval flow",
            "Enforce file upload validator blocking executable extensions",
            "Integrate Telegram bot webhook commands for user task queries",
            "Conduct security audit of tenant foreign key constraints",
            "Benchmark database query execution times under simulated load",
            "Prepare automated database backup and restore validation scripts",
        ]

        task_statuses = ["completed", "completed", "completed", "in_progress", "in_progress", "todo", "in_review", "backlog", "blocked", "cancelled"]
        task_priorities = ["high", "medium", "urgent", "low"]

        tasks = []
        for proj in projects:
            org = proj.organization
            org_members = [
                m.user for m in OrganizationMembership.objects.filter(organization=org).select_related("user")
            ]
            creator = org_members[0] if org_members else users[1]
            org_cats = [c for c in categories if c.organization_id == org.id]

            for t_idx in range(10):
                tkey = f"{proj.key}-{t_idx+1}"
                status = task_statuses[t_idx % len(task_statuses)]
                priority = task_priorities[t_idx % len(task_priorities)]
                title = f"{task_titles[t_idx % len(task_titles)]} [{t_idx+1}]"
                cat = org_cats[t_idx % len(org_cats)] if org_cats else None

                est_hours = Decimal(random.randint(2, 40))
                act_hours = est_hours if status == "completed" else Decimal(random.randint(1, int(est_hours)))
                due_d = today + timedelta(days=random.randint(-30, 45))

                task, created = Task.objects.get_or_create(
                    organization=org,
                    task_key=tkey,
                    defaults={
                        "project": proj,
                        "title": title,
                        "description": f"Detailed specifications for {title} on project {proj.name}.",
                        "status": status,
                        "priority": priority,
                        "category": cat,
                        "created_by": creator,
                        "due_date": due_d,
                        "estimated_hours": est_hours,
                        "actual_hours": act_hours,
                        "progress": 100 if status == "completed" else (50 if status == "in_progress" else 0),
                        "completed_date": (now - timedelta(days=random.randint(1, 30))) if status == "completed" else None,
                        "is_demo": True,
                    },
                )
                if not created:
                    task.is_demo = True
                    task.save(update_fields=["is_demo"])
                tasks.append(task)

                # Task Assignment
                assigned_user = org_members[(t_idx + 1) % len(org_members)] if org_members else creator
                TaskAssignment.objects.get_or_create(
                    task=task,
                    user=assigned_user,
                    defaults={"assigned_by": creator},
                )

        stats["Tasks"] = len(tasks)

        # 9. Comments (>= 200)
        self.stdout.write("Seeding Comments & Mentions...")
        comment_samples = [
            "Sprint review complete: unit tests and integration tests passing with 100% coverage.",
            "Please verify tenant data isolation before pushing this commit to the release branch.",
            "Reviewed the schema migrations; indexed foreign keys are performing within SLA.",
            "Dependencies updated and verified against the security vulnerability catalog.",
            "Database load test successfully processed 10,000 queries with under 15ms p99 latency.",
            "Initial mockup approved by product owner. Proceeding with frontend implementation.",
            "Blocked waiting for approval from the infrastructure security review team.",
            "Deploying migration script during scheduled maintenance window.",
        ]

        comments = []
        for i in range(max(options.get("comments", 200), 200)):
            target_task = tasks[i % len(tasks)]
            author = target_task.project.owner
            content = comment_samples[i % len(comment_samples)]
            parent = comments[i - 1] if (i % 7 == 0 and comments and comments[-1].task_id == target_task.id) else None

            comment = Comment.objects.create(
                organization=target_task.organization,
                task=target_task,
                author=author,
                content=content,
                is_internal=(i % 5 == 0),
                parent=parent,
            )
            comments.append(comment)

        stats["Comments"] = len(comments)

        # 10. Time Entries (>= 100)
        self.stdout.write("Seeding Time Entries...")
        time_entries = []
        for i in range(max(options.get("time_entries", 100), 100)):
            target_task = tasks[i % len(tasks)]
            user = target_task.created_by
            entry_date = today - timedelta(days=random.randint(0, 30))
            duration_s = random.randint(1, 8) * 1800  # 0.5h to 4.0h

            start_t = now - timedelta(days=random.randint(0, 30), hours=random.randint(1, 6))
            end_t = start_t + timedelta(seconds=duration_s)

            entry = TimeEntry.objects.create(
                organization=target_task.organization,
                task=target_task,
                project=target_task.project,
                user=user,
                description=f"Work session on {target_task.title[:40]}",
                start_time=start_t,
                end_time=end_t,
                duration_seconds=duration_s,
                is_billable=True,
                hourly_rate=Decimal("85.00"),
                date=entry_date,
            )
            time_entries.append(entry)

        stats["Time Entries"] = len(time_entries)

        # 11. Notifications (>= 100)
        self.stdout.write("Seeding Notifications...")
        notif_types = ["task_assigned", "task_due_reminder", "comment_mention", "approval_requested", "system"]
        notifications = []
        for i in range(max(options.get("notifications", 100), 100)):
            target_task = tasks[i % len(tasks)]
            recipient = target_task.created_by
            ntype = notif_types[i % len(notif_types)]

            notif = Notification.objects.create(
                organization=target_task.organization,
                recipient=recipient,
                actor=users[0],
                notification_type=ntype,
                title=f"Update regarding {target_task.task_key}",
                body=f"Important notification for task {target_task.title[:50]}.",
                task=target_task,
                project=target_task.project,
                target_url=f"/tasks/{target_task.id}/",
                is_read=(i % 3 == 0),
            )
            notifications.append(notif)

        stats["Notifications"] = len(notifications)

        # 12. Audit Logs (>= 100)
        self.stdout.write("Seeding Audit Logs...")
        audit_actions = ["create", "update", "status_change", "export_csv", "login"]
        audit_logs = []
        for i in range(max(options.get("audit_logs", 100), 100)):
            target_task = tasks[i % len(tasks)]
            action = audit_actions[i % len(audit_actions)]

            audit = AuditLog.objects.create(
                organization=target_task.organization,
                user=target_task.created_by,
                action=action,
                model_name="Task",
                object_id=str(target_task.id),
                object_repr=f"[{target_task.task_key}] {target_task.title[:30]}",
                changes={"field": "status", "old": "todo", "new": "completed"},
                ip_address=f"192.168.1.{10 + (i % 200)}",
                user_agent="Mozilla/5.0 (Enterprise SaaS WorkFlow Client; Linux x86_64)",
            )
            audit_logs.append(audit)

        stats["Audit Logs"] = len(audit_logs)

        # 13. Approval Workflows & Requests (>= 50)
        self.stdout.write("Seeding Approval Workflows & Requests...")
        approval_requests = []
        workflows = []
        for org in organizations:
            wf, _ = ApprovalWorkflow.objects.get_or_create(
                organization=org,
                name=f"{org.name} Operational Review",
                defaults={"description": "Standard multi-stage managerial sign-off."},
            )
            stage1, _ = ApprovalStage.objects.get_or_create(
                organization=org,
                workflow=wf,
                step_number=1,
                defaults={"name": "Manager Review"},
            )
            stage2, _ = ApprovalStage.objects.get_or_create(
                organization=org,
                workflow=wf,
                step_number=2,
                defaults={"name": "Director Sign-Off"},
            )
            workflows.append(wf)

        appr_statuses = ["approved", "approved", "pending", "rejected"]
        target_appr = max(options.get("approval_requests", 50), 50)
        for i in range(target_appr):
            target_task = tasks[i % len(tasks)]
            org = target_task.organization
            wf = next((w for w in workflows if w.organization_id == org.id), workflows[0])
            status = appr_statuses[i % len(appr_statuses)]

            req = ApprovalRequest.objects.create(
                organization=org,
                workflow=wf,
                task=target_task,
                project=target_task.project,
                requester=target_task.created_by,
                title=f"Sign-off request for {target_task.task_key}",
                description=f"Verification sign-off on deliverable for {target_task.title[:40]}.",
                status=status,
                current_stage=wf.stages.first(),
            )
            approval_requests.append(req)

        stats["Approval Requests"] = len(approval_requests)

        # 14. Attachment Metadata (>= 20)
        self.stdout.write("Seeding Attachments...")
        attachments = []
        sample_files = [
            ("architecture_spec.pdf", "application/pdf", 1024 * 128),
            ("database_erd.png", "image/png", 1024 * 256),
            ("sprint_review_deck.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 1024 * 64),
            ("financial_projections.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 1024 * 80),
        ]

        target_att = max(options.get("attachments", 20), 20)
        for i in range(target_att):
            target_task = tasks[i % len(tasks)]
            fname, mtype, fsize = sample_files[i % len(sample_files)]
            dummy_file = ContentFile(b"Sample WorkFlow Enterprise demo attachment content.", name=f"demo_{i}_{fname}")

            att = Attachment.objects.create(
                organization=target_task.organization,
                task=target_task,
                project=target_task.project,
                uploaded_by=target_task.created_by,
                file=dummy_file,
                file_name=fname,
                file_size=fsize,
                mime_type=mtype,
                is_public=False,
            )
            attachments.append(att)

        stats["Attachment Metadata"] = len(attachments)

        return stats

