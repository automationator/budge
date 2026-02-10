"""
Base models and common model utilities.

Domain-specific models should be defined in their respective modules
(e.g., src/users/models.py, src/posts/models.py).

Import all models here so Alembic can detect them for migrations.
"""

from src.accounts.models import Account
from src.admin.models import SystemSettings
from src.allocation_rules.models import AllocationRule
from src.allocations.models import Allocation
from src.auth.models import RefreshToken
from src.budgets.models import Budget, BudgetMembership
from src.database import Base
from src.envelope_groups.models import EnvelopeGroup
from src.envelopes.models import Envelope
from src.locations.models import Location
from src.notifications.models import Notification, NotificationPreference
from src.payees.models import Payee
from src.recurring_transactions.models import RecurringTransaction
from src.transactions.models import Transaction
from src.users.models import User

__all__ = [
    "Account",
    "Allocation",
    "AllocationRule",
    "Base",
    "Envelope",
    "EnvelopeGroup",
    "Location",
    "Notification",
    "NotificationPreference",
    "Payee",
    "RecurringTransaction",
    "RefreshToken",
    "Budget",
    "BudgetMembership",
    "SystemSettings",
    "Transaction",
    "User",
]
