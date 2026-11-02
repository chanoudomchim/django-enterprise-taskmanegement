"""Admin configuration for Organizations."""

from django.contrib import admin
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
    OrganizationSettings,
    SubscriptionPlan,
    Subscription,
)


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    raw_id_fields = ("user",)


class OrganizationSettingsInline(admin.StackedInline):
    model = OrganizationSettings
    can_delete = False


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "is_active", "is_demo", "created_at")
    list_filter = ("status", "is_active", "is_demo")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrganizationSettingsInline, OrganizationMembershipInline]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_default", "is_active", "joined_at")
    list_filter = ("role", "is_default", "is_active")
    search_fields = ("organization__name", "user__email")
    raw_id_fields = ("organization", "user")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ("organization", "email", "role", "status", "expires_at", "created_at")
    list_filter = ("status", "role")
    search_fields = ("organization__name", "email")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price", "billing_interval", "max_users", "is_active")
    list_filter = ("billing_interval", "is_active")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "start_date", "end_date")
    list_filter = ("status",)

