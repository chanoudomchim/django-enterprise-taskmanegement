"""Management command to retry failed webhook deliveries."""

from django.core.management.base import BaseCommand
from apps.integrations.services import retry_failed_webhooks


class Command(BaseCommand):
    help = "Retry failed outgoing webhook deliveries up to 3 attempts."

    def handle(self, *args, **options):
        retried, succeeded = retry_failed_webhooks()
        self.stdout.write(self.style.SUCCESS(f"Processed webhooks: {retried} retried, {succeeded} succeeded."))

