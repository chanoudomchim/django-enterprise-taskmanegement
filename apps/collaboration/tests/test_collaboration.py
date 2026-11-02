"""Automated tests for Collaboration: Comments, Mentions, Attachments, and Secure Downloads."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.collaboration.models import Comment, CommentMention, Attachment, Activity
from apps.collaboration.services import create_comment, create_attachment

User = get_user_model()


class CollaborationTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="collab_owner@company.local", password="password123")
        self.member = User.objects.create_user(email="collab_member@company.local", password="password123")
        self.other_user = User.objects.create_user(email="outsider@other.local", password="password123")

        self.org = Organization.objects.create(name="Collab Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.member, role="member", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="Collab Project",
            key="CLB",
            owner=self.owner,
        )
        self.task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Collab Task",
        )

        self.client = Client()
        self.client.force_login(self.owner)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_comment_creation_and_mentions(self):
        """Comments create audit entries and extract user @mentions."""
        content = f"Hey collab_member@company.local please check this task."
        comment = create_comment(
            organization=self.org,
            author=self.owner,
            content=content,
            task=self.task,
        )

        self.assertEqual(comment.author, self.owner)
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.organization, self.org)

        # Verify mention created
        mention = CommentMention.objects.filter(comment=comment, user=self.member).first()
        self.assertIsNotNone(mention)

        # Verify activity logged
        activity = Activity.objects.filter(task=self.task, action="commented").first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.actor, self.owner)

    def test_attachment_upload_and_secure_download(self):
        """Attachments are securely stored and enforce tenant isolation upon download."""
        dummy_file = SimpleUploadedFile("spec.pdf", b"%PDF-1.4 dummy content", content_type="application/pdf")

        attachment = create_attachment(
            organization=self.org,
            uploaded_by=self.owner,
            file_obj=dummy_file,
            task=self.task,
        )

        self.assertEqual(attachment.file_name, "spec.pdf")
        self.assertEqual(attachment.organization, self.org)

        # Download by tenant member succeeds
        download_url = reverse("secure_attachment_download", kwargs={"attachment_id": attachment.id})
        resp = self.client.get(download_url)
        self.assertEqual(resp.status_code, 200)

        # Download by outsider fails with 403 Forbidden
        outsider_client = Client()
        outsider_client.force_login(self.other_user)
        resp_outsider = outsider_client.get(download_url)
        self.assertEqual(resp_outsider.status_code, 403)

        # Download unauthenticated fails with 403 Forbidden
        anon_client = Client()
        resp_anon = anon_client.get(download_url)
        self.assertEqual(resp_anon.status_code, 403)

    def test_attachment_dangerous_file_extension_blocked(self):
        """Dangerous executable file types are blocked by validation."""
        bad_file = SimpleUploadedFile("malicious.sh", b"#!/bin/bash\necho hack", content_type="text/x-shellscript")
        with self.assertRaises(Exception):
            create_attachment(
                organization=self.org,
                uploaded_by=self.owner,
                file_obj=bad_file,
                task=self.task,
            )

    def test_activity_feed_view(self):
        """Activity feed renders organization activities."""
        create_comment(
            organization=self.org,
            author=self.owner,
            content="Activity test comment",
            task=self.task,
        )
        resp = self.client.get(reverse("activity_feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Activity test comment")

