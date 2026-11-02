"""URL configuration for organizations."""

from django.urls import path
from apps.organizations.views import (
    OrganizationListView,
    OrganizationCreateView,
    OrganizationSwitchView,
    OrganizationSettingsView,
    OrganizationMembersView,
    OrganizationInviteView,
    InvitationAcceptView,
)

urlpatterns = [
    path("", OrganizationListView.as_view(), name="org_list"),
    path("create/", OrganizationCreateView.as_view(), name="org_create"),
    path("switch/<uuid:org_id>/", OrganizationSwitchView.as_view(), name="org_switch"),
    path("settings/", OrganizationSettingsView.as_view(), name="org_settings"),
    path("members/", OrganizationMembersView.as_view(), name="org_members"),
    path("invite/", OrganizationInviteView.as_view(), name="org_invite"),
    path("invitations/<uuid:token>/accept/", InvitationAcceptView.as_view(), name="invitation_accept"),
]

