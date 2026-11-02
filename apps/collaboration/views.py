"""Views for Collaboration: Comments, Attachments, Secure Media Download, and Activity Feed."""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.http import HttpResponseForbidden, FileResponse, Http404
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.organizations.models import OrganizationMembership
from apps.tasks.models import Task
from apps.projects.models import Project
from apps.collaboration.models import Comment, Attachment, Activity
from apps.collaboration.forms import CommentForm, AttachmentForm
from apps.collaboration.services import create_comment, create_attachment, log_activity


class CommentCreateView(TenantRequiredMixin, View):
    """Create a comment on a Task or Project, or reply to an existing comment."""

    def post(self, request):
        form = CommentForm(request.POST)
        task_id = request.POST.get("task_id")
        project_id = request.POST.get("project_id")
        parent_id = request.POST.get("parent_id")

        task = Task.objects.filter(organization=request.tenant, id=task_id).first() if task_id else None
        project = Project.objects.filter(organization=request.tenant, id=project_id).first() if project_id else None
        parent = Comment.objects.filter(organization=request.tenant, id=parent_id).first() if parent_id else None

        if not task and not project and not parent:
            messages.error(request, _("Invalid comment target."))
            return redirect("home")

        if form.is_valid():
            content = form.cleaned_data["content"]
            is_internal = form.cleaned_data.get("is_internal", False)
            resolved_task = task or (parent.task if parent else None)
            resolved_project = project or (parent.project if parent else None)

            create_comment(
                organization=request.tenant,
                author=request.user,
                content=content,
                task=resolved_task,
                project=resolved_project,
                parent=parent,
                is_internal=is_internal,
            )
            messages.success(request, _("Comment added."))

        if task:
            return redirect("task_detail", task_key=task.task_key)
        elif project:
            return redirect("project_detail", project_key=project.key)
        elif parent and parent.task:
            return redirect("task_detail", task_key=parent.task.task_key)
        elif parent and parent.project:
            return redirect("project_detail", project_key=parent.project.key)

        return redirect("home")


class CommentDeleteView(TenantRequiredMixin, View):
    """Delete a comment (allowed by comment author, workspace owner, or admin)."""

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id, organization=request.tenant)

        is_admin = OrganizationMembership.objects.filter(
            organization=request.tenant,
            user=request.user,
            role__in=["owner", "admin"],
            is_active=True,
        ).exists()

        if comment.author != request.user and not is_admin:
            messages.error(request, _("You do not have permission to delete this comment."))
            return redirect("home")

        task_key = comment.task.task_key if comment.task else None
        project_key = comment.project.key if comment.project else None

        comment.delete()
        messages.info(request, _("Comment deleted."))

        if task_key:
            return redirect("task_detail", task_key=task_key)
        elif project_key:
            return redirect("project_detail", project_key=project_key)
        return redirect("home")


class AttachmentUploadView(TenantRequiredMixin, View):
    """Upload a file attachment to a Task or Project."""

    def post(self, request):
        form = AttachmentForm(request.POST, request.FILES)
        task_id = request.POST.get("task_id")
        project_id = request.POST.get("project_id")

        task = Task.objects.filter(organization=request.tenant, id=task_id).first() if task_id else None
        project = Project.objects.filter(organization=request.tenant, id=project_id).first() if project_id else None

        if not task and not project:
            messages.error(request, _("Invalid attachment target."))
            return redirect("home")

        if form.is_valid():
            try:
                file_obj = form.cleaned_data["file"]
                is_public = form.cleaned_data.get("is_public", False)
                create_attachment(
                    organization=request.tenant,
                    uploaded_by=request.user,
                    file_obj=file_obj,
                    task=task,
                    project=project,
                    is_public=is_public,
                )
                messages.success(request, _("File uploaded successfully."))
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, "message") else e))
        else:
            messages.error(request, _("Failed to upload file. Please check file format and size."))

        if task:
            return redirect("task_detail", task_key=task.task_key)
        elif project:
            return redirect("project_detail", project_key=project.key)
        return redirect("home")


class AttachmentDeleteView(TenantRequiredMixin, View):
    """Delete an uploaded attachment."""

    def post(self, request, attachment_id):
        attachment = get_object_or_404(Attachment, id=attachment_id, organization=request.tenant)

        is_admin = OrganizationMembership.objects.filter(
            organization=request.tenant,
            user=request.user,
            role__in=["owner", "admin"],
            is_active=True,
        ).exists()

        if attachment.uploaded_by != request.user and not is_admin:
            messages.error(request, _("You do not have permission to delete this attachment."))
            return redirect("home")

        task_key = attachment.task.task_key if attachment.task else None
        project_key = attachment.project.key if attachment.project else None

        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()
        messages.info(request, _("Attachment deleted."))

        if task_key:
            return redirect("task_detail", task_key=task_key)
        elif project_key:
            return redirect("project_detail", project_key=project_key)
        return redirect("home")


class SecureAttachmentDownloadView(View):
    """
    Secure attachment download endpoint (/media/secure/<uuid>/).
    Validates tenant isolation: user must be an active member of the owning organization.
    """

    def get(self, request, attachment_id):
        attachment = get_object_or_404(Attachment, id=attachment_id)

        # If public attachment, allow download
        if attachment.is_public:
            return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.file_name)

        # Authenticated check
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required to access private attachments.")

        # Superuser check
        if request.user.is_superuser:
            return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.file_name)

        # Check organization membership
        is_member = OrganizationMembership.objects.filter(
            organization=attachment.organization,
            user=request.user,
            is_active=True,
        ).exists()

        if not is_member:
            return HttpResponseForbidden("Access denied. You do not belong to this organization.")

        try:
            return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.file_name)
        except FileNotFoundError:
            raise Http404("Attachment file not found on disk.")


class ActivityFeedView(TenantRequiredMixin, View):
    """View recent activity feed across the organization."""

    def get(self, request):
        activities = (
            Activity.objects.filter(organization=request.tenant)
            .select_related("actor", "task", "project")
            .order_by("-created_at")[:50]
        )
        return render(
            request,
            "collaboration/activity_feed.html",
            {
                "activities": activities,
            },
        )

