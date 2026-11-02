"""Verification command to audit database integrity and confirm demo record counts."""

import os
import sys
from django.core.management.base import BaseCommand
from django.db.models import F
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization
from apps.departments.models import Department, Team
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskCategory
from apps.collaboration.models import Comment, Attachment
from apps.approvals.models import ApprovalRequest, ApprovalWorkflow
from apps.time_tracking.models import TimeEntry
from apps.notifications.models import Notification
from apps.audit.models import AuditLog

User = get_user_model()


class Command(BaseCommand):
    help = "Verify that database contains >= 2,080 demo records and integrity constraints hold."

    def add_arguments(self, parser):
        parser.add_argument("--password", type=str, default=None, help="Password to verify for demo accounts")

    def handle(self, *args, **options):
        demo_password = options.get("password") or os.environ.get("DEMO_PASSWORD", "WorkflowDemo2026!")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.NOTICE("WORKFLOW ENTERPRISE DEMO DATA INTEGRITY VERIFICATION"))
        self.stdout.write("=" * 70)

        targets = [
            ("Organizations", Organization, {"is_demo": True}, 10),
            ("Users", User, {"is_demo": True}, 100),
            ("Departments", Department, {"organization__is_demo": True}, 30),
            ("Teams", Team, {"organization__is_demo": True}, 50),
            ("Projects", Project, {"is_demo": True}, 100),
            ("Project Memberships", ProjectMembership, {"project__is_demo": True}, 200),
            ("Tasks", Task, {"is_demo": True}, 1000),
            ("Comments", Comment, {"organization__is_demo": True}, 200),
            ("Time Entries", TimeEntry, {"organization__is_demo": True}, 100),
            ("Notifications", Notification, {"organization__is_demo": True}, 100),
            ("Audit Logs", AuditLog, {"organization__is_demo": True}, 100),
            ("Approval Requests", ApprovalRequest, {"organization__is_demo": True}, 50),
            ("Attachment Metadata", Attachment, {"organization__is_demo": True}, 20),
            ("Task Categories", TaskCategory, {"organization__is_demo": True}, 20),
        ]

        all_passed = True
        total_actual = 0
        total_target = 0

        self.stdout.write(f"{'Model / Entity':<24} | {'Target':>8} | {'Actual':>8} | {'Status':>8}")
        self.stdout.write("-" * 70)

        for name, model_cls, filter_kwargs, target_cnt in targets:
            actual_cnt = model_cls.objects.filter(**filter_kwargs).count()
            total_actual += actual_cnt
            total_target += target_cnt
            passed = actual_cnt >= target_cnt
            if not passed:
                all_passed = False
            status_str = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")
            self.stdout.write(f"{name:<24} | {target_cnt:>8} | {actual_cnt:>8} | {status_str:>8}")

        self.stdout.write("-" * 70)
        total_passed = total_actual >= 2080
        if not total_passed:
            all_passed = False
        summary_status = self.style.SUCCESS("PASS") if total_passed else self.style.ERROR("FAIL")
        self.stdout.write(f"{'TOTAL CORE RECORDS':<24} | {total_target:>8} | {total_actual:>8} | {summary_status:>8}")
        self.stdout.write("=" * 70)

        # 2. Key Demo Account Verification
        self.stdout.write("\nAuditing Key Demo User Accounts & Password Authentication...")
        demo_accounts = [
            ("admin@workflow.local", True),
            ("owner@workflow.local", False),
            ("manager@workflow.local", False),
            ("projectmanager@workflow.local", False),
            ("employee@workflow.local", False),
        ]
        accounts_passed = True
        for email, is_super in demo_accounts:
            user = User.objects.filter(email=email).first()
            if not user:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Missing expected account: {email}"))
                accounts_passed = False
                all_passed = False
            else:
                pwd_ok = user.check_password(demo_password)
                super_ok = (user.is_superuser == is_super)
                if not pwd_ok:
                    self.stdout.write(self.style.ERROR(f"  [FAIL] Password mismatch for {email}"))
                    accounts_passed = False
                    all_passed = False
                elif not super_ok:
                    self.stdout.write(self.style.ERROR(f"  [FAIL] Superuser flag mismatch for {email}"))
                    accounts_passed = False
                    all_passed = False
                else:
                    self.stdout.write(self.style.SUCCESS(f"  [PASS] Verified account: {email}"))

        # 3. Multi-Tenant Cross-Isolation Integrity Checks
        self.stdout.write("\nAuditing Multi-Tenant Database Cross-Isolation...")
        isolation_errors = 0

        # Tasks vs Project organization
        task_leaks = Task.objects.exclude(organization=F("project__organization")).count()
        if task_leaks > 0:
            self.stdout.write(self.style.ERROR(f"  [FAIL] {task_leaks} task(s) have mismatched project organizations!"))
            isolation_errors += 1
            all_passed = False
        else:
            self.stdout.write(self.style.SUCCESS("  [PASS] All tasks strictly share organization with parent project."))

        # Time Entries vs Project organization
        time_leaks = TimeEntry.objects.exclude(organization=F("project__organization")).count()
        if time_leaks > 0:
            self.stdout.write(self.style.ERROR(f"  [FAIL] {time_leaks} time entries have mismatched project organizations!"))
            isolation_errors += 1
            all_passed = False
        else:
            self.stdout.write(self.style.SUCCESS("  [PASS] All time entries strictly match project organization."))

        # Comments vs Task organization
        comment_leaks = Comment.objects.filter(task__isnull=False).exclude(organization=F("task__organization")).count()
        if comment_leaks > 0:
            self.stdout.write(self.style.ERROR(f"  [FAIL] {comment_leaks} comments have mismatched task organizations!"))
            isolation_errors += 1
            all_passed = False
        else:
            self.stdout.write(self.style.SUCCESS("  [PASS] All task comments strictly match task organization."))

        # Approval Requests vs Workflow organization
        approval_leaks = ApprovalRequest.objects.exclude(organization=F("workflow__organization")).count()
        if approval_leaks > 0:
            self.stdout.write(self.style.ERROR(f"  [FAIL] {approval_leaks} approval requests have mismatched workflow organizations!"))
            isolation_errors += 1
            all_passed = False
        else:
            self.stdout.write(self.style.SUCCESS("  [PASS] All approval requests strictly match workflow organization."))

        self.stdout.write("\n" + "=" * 70)
        if all_passed:
            self.stdout.write(self.style.SUCCESS("ALL 2,080+ RECORD COUNT AND MULTI-TENANT AUDIT CHECKS PASSED SUCCESSFULLY."))
            self.stdout.write("=" * 70 + "\n")
            sys.exit(0)
        else:
            self.stdout.write(self.style.ERROR("ONE OR MORE VERIFICATION CHECKS FAILED. SEE AUDIT LOG ABOVE."))
            self.stdout.write("=" * 70 + "\n")
            sys.exit(1)

