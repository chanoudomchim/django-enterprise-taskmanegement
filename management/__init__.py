"""Management package for WorkFlow Enterprise."""

import sys

# Ensure Django command loader imports management.management.commands as management.commands
sys.modules["management.management"] = sys.modules[__name__]


