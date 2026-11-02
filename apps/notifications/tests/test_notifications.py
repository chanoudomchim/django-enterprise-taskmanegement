"""Automated tests for Notifications, Telegram Bot, Management Commands, and Redis Caching."""

from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task, TaskAssignment
from apps.notifications.models import (
    Notification,
    NotificationPreference,
    NotificationDelivery,
    TelegramAccount,
    TelegramIntegration,
)
from apps.notifications.services import (
    send_notification,
    handle_telegram_command,
)
from config.cache import set_tenant_cache, get_tenant_cache, delete_tenant_cache

User = get_user_model()


class NotificationsTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="notif_owner@company.local", password="password123")
        self.worker = User.objects.create_user(email="notif_worker@company.local", password="password123")

        self.org = Organization.objects.create(name="Notification Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.worker, role="member", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="Notif Project",
            key="NTF",
            owner=self.owner,
        )

        self.client = Client()
        self.client.force_login(self.worker)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_notification_dispatch_and_delivery_records(self):
        """Notification creates in-app and delivery records."""
        notif = send_notification(
            recipient=self.worker,
            organization=self.org,
            title="Assigned to Task",
            body="You were assigned to task NTF-1.",
            notification_type="task_assigned",
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.recipient, self.worker)
        self.assertFalse(notif.is_read)

        # In-app delivery recorded
        delivery = NotificationDelivery.objects.filter(notification=notif, channel="in_app").first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.status, "sent")

    def test_notification_preferences_suppression(self):
        """Disabling notifications in preferences suppresses generation."""
        pref, _ = NotificationPreference.objects.get_or_create(
            organization=self.org,
            user=self.worker,
        )
        pref.notify_on_task_assigned = False
        pref.save()

        notif = send_notification(
            recipient=self.worker,
            organization=self.org,
            title="Suppressed Notification",
            body="This should not be delivered.",
            notification_type="task_assigned",
        )
        self.assertIsNone(notif)

    def test_telegram_bot_commands(self):
        """Telegram account linking via verification code and command query."""
        today = timezone.localdate()
        task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Urgent Bug Fix",
            due_date=today,
        )
        TaskAssignment.objects.create(task=task, user=self.worker, assigned_by=self.owner)

        account = TelegramAccount.objects.create(
            organization=self.org,
            user=self.worker,
            verification_code="testcode123",
        )

        # 1. Unverified user fails private queries
        resp_unverified = handle_telegram_command(self.org, chat_id="999888", command_text="/mytasks")
        self.assertIn("must verify your Telegram account", resp_unverified)

        # 2. Link account with /start code
        resp_start = handle_telegram_command(self.org, chat_id="999888", command_text="/start testcode123")
        self.assertIn("Linked to notif_worker@company.local", resp_start)
        account.refresh_from_db()
        self.assertTrue(account.is_verified)
        self.assertEqual(account.telegram_chat_id, "999888")

        # 3. Verified user queries /mytasks
        resp_tasks = handle_telegram_command(self.org, chat_id="999888", command_text="/mytasks")
        self.assertIn("Urgent Bug Fix", resp_tasks)

        # 4. /today command
        resp_today = handle_telegram_command(self.org, chat_id="999888", command_text="/today")
        self.assertIn("Urgent Bug Fix", resp_today)

    def test_send_due_reminders_management_command(self):
        """Idempotent management command sends reminders without duplicates."""
        today = timezone.localdate()
        task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Due Tomorrow Task",
            due_date=today + timedelta(days=1),
        )
        TaskAssignment.objects.create(task=task, user=self.worker, assigned_by=self.owner)

        # Run command first time
        call_command("send_due_reminders")
        count1 = Notification.objects.filter(recipient=self.worker, notification_type="task_due_reminder").count()
        self.assertEqual(count1, 1)

        # Run command second time (idempotency prevents duplicate)
        call_command("send_due_reminders")
        count2 = Notification.objects.filter(recipient=self.worker, notification_type="task_due_reminder").count()
        self.assertEqual(count2, 1)

    def test_redis_tenant_cache_isolation(self):
        """Test tenant-scoped caching operations in Redis."""
        org_id = str(self.org.id)
        set_tenant_cache(org_id, "stats_summary", {"tasks": 42}, timeout=60)

        val = get_tenant_cache(org_id, "stats_summary")
        self.assertEqual(val, {"tasks": 42})

        delete_tenant_cache(org_id, "stats_summary")
        val_after_del = get_tenant_cache(org_id, "stats_summary")
        self.assertIsNone(val_after_del)

    def test_notification_views(self):
        """Notification list and mark-read views."""
        notif = send_notification(
            recipient=self.worker,
            organization=self.org,
            title="Test Notice",
            body="Notice details",
        )

        resp = self.client.get(reverse("notification_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Notice")

        # Mark read
        resp_read = self.client.post(reverse("notification_mark_read", kwargs={"notification_id": notif.id}))
        self.assertRedirects(resp_read, reverse("notification_list"))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

