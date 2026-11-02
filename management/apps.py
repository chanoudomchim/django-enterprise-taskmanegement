import os
from django.apps import AppConfig


class ManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "management"
    verbose_name = "System Management Commands"
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


