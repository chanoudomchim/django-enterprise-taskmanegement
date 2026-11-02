"""Management command to safely remove all demo and seeded records."""

import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization

User = get_user_model()


class Command(BaseCommand):
    help = "Safely delete all demo organizations, demo users, and associated data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_true",
            help="Do not prompt for confirmation before deleting demo data.",
        )
        parser.add_argument(
            "--force-production",
            action="store_true",
            help="Allow running in production / when DEBUG is False.",
        )

    def handle(self, *args, **options):
        is_debug = getattr(settings, "DEBUG", False)
        force_prod = options.get("force_production", False)

        if not is_debug and not force_prod:
            raise CommandError(
                "Refusing to clear demo data in a production environment (DEBUG=False) "
                "without explicit --force-production override."
            )

        if not options.get("no_input"):
            confirm = input(
                "WARNING: This will permanently delete all demo organizations, demo users, and associated records.\n"
                "Are you sure you want to proceed? [y/N]: "
            )
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write(self.style.WARNING("Operation cancelled by user."))
                sys.exit(0)

        with transaction.atomic():
            demo_orgs = Organization.objects.filter(is_demo=True)
            org_count = demo_orgs.count()
            demo_orgs.delete()

            demo_users = User.objects.filter(is_demo=True)
            user_count = demo_users.count()
            demo_users.delete()

            # Also catch any residual demo accounts by domain
            local_users = User.objects.filter(email__endswith="@workflow.local")
            local_user_count = local_users.count()
            if local_user_count > 0:
                local_users.delete()
                user_count += local_user_count

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {org_count} demo organization(s) and {user_count} demo user(s) "
                "along with all cascading tenant records."
            )
        )

