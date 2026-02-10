from enum import StrEnum

from src.budgets.models import BudgetRole


class BudgetScope(StrEnum):
    # Budget settings
    BUDGET_DELETE = "budget:delete"
    BUDGET_READ = "budget:read"
    BUDGET_UPDATE = "budget:update"

    # Member management
    MEMBERS_ADD = "members:add"
    MEMBERS_MANAGE_ROLES = "members:manage_roles"
    MEMBERS_READ = "members:read"
    MEMBERS_REMOVE = "members:remove"

    # Account management
    ACCOUNTS_CREATE = "accounts:create"
    ACCOUNTS_DELETE = "accounts:delete"
    ACCOUNTS_READ = "accounts:read"
    ACCOUNTS_UPDATE = "accounts:update"

    # Payee management
    PAYEES_CREATE = "payees:create"
    PAYEES_DELETE = "payees:delete"
    PAYEES_READ = "payees:read"
    PAYEES_UPDATE = "payees:update"

    # Location management
    LOCATIONS_CREATE = "locations:create"
    LOCATIONS_DELETE = "locations:delete"
    LOCATIONS_READ = "locations:read"
    LOCATIONS_UPDATE = "locations:update"

    # Transaction management
    TRANSACTIONS_CREATE = "transactions:create"
    TRANSACTIONS_DELETE = "transactions:delete"
    TRANSACTIONS_READ = "transactions:read"
    TRANSACTIONS_UPDATE = "transactions:update"

    # Recurring transaction management
    RECURRING_CREATE = "recurring:create"
    RECURRING_DELETE = "recurring:delete"
    RECURRING_READ = "recurring:read"
    RECURRING_UPDATE = "recurring:update"

    # Envelope management
    ENVELOPES_CREATE = "envelopes:create"
    ENVELOPES_DELETE = "envelopes:delete"
    ENVELOPES_READ = "envelopes:read"
    ENVELOPES_UPDATE = "envelopes:update"

    # Envelope group management
    ENVELOPE_GROUPS_CREATE = "envelope_groups:create"
    ENVELOPE_GROUPS_DELETE = "envelope_groups:delete"
    ENVELOPE_GROUPS_READ = "envelope_groups:read"
    ENVELOPE_GROUPS_UPDATE = "envelope_groups:update"

    # Allocation management
    ALLOCATIONS_CREATE = "allocations:create"
    ALLOCATIONS_DELETE = "allocations:delete"
    ALLOCATIONS_READ = "allocations:read"
    ALLOCATIONS_UPDATE = "allocations:update"

    # Allocation rule management
    ALLOCATION_RULES_CREATE = "allocation_rules:create"
    ALLOCATION_RULES_DELETE = "allocation_rules:delete"
    ALLOCATION_RULES_READ = "allocation_rules:read"
    ALLOCATION_RULES_UPDATE = "allocation_rules:update"

    # Notification management
    NOTIFICATIONS_READ = "notifications:read"
    NOTIFICATIONS_UPDATE = "notifications:update"

    # Data export/import/repair
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_REPAIR = "data:repair"


ROLE_SCOPES: dict[BudgetRole, set[BudgetScope]] = {
    BudgetRole.OWNER: {
        BudgetScope.ACCOUNTS_CREATE,
        BudgetScope.ACCOUNTS_DELETE,
        BudgetScope.ACCOUNTS_READ,
        BudgetScope.ACCOUNTS_UPDATE,
        BudgetScope.ALLOCATIONS_CREATE,
        BudgetScope.ALLOCATIONS_DELETE,
        BudgetScope.ALLOCATIONS_READ,
        BudgetScope.ALLOCATIONS_UPDATE,
        BudgetScope.ALLOCATION_RULES_CREATE,
        BudgetScope.ALLOCATION_RULES_DELETE,
        BudgetScope.ALLOCATION_RULES_READ,
        BudgetScope.ALLOCATION_RULES_UPDATE,
        BudgetScope.DATA_EXPORT,
        BudgetScope.DATA_IMPORT,
        BudgetScope.DATA_REPAIR,
        BudgetScope.ENVELOPE_GROUPS_CREATE,
        BudgetScope.ENVELOPE_GROUPS_DELETE,
        BudgetScope.ENVELOPE_GROUPS_READ,
        BudgetScope.ENVELOPE_GROUPS_UPDATE,
        BudgetScope.ENVELOPES_CREATE,
        BudgetScope.ENVELOPES_DELETE,
        BudgetScope.ENVELOPES_READ,
        BudgetScope.ENVELOPES_UPDATE,
        BudgetScope.LOCATIONS_CREATE,
        BudgetScope.LOCATIONS_DELETE,
        BudgetScope.LOCATIONS_READ,
        BudgetScope.LOCATIONS_UPDATE,
        BudgetScope.MEMBERS_ADD,
        BudgetScope.MEMBERS_MANAGE_ROLES,
        BudgetScope.MEMBERS_READ,
        BudgetScope.MEMBERS_REMOVE,
        BudgetScope.NOTIFICATIONS_READ,
        BudgetScope.NOTIFICATIONS_UPDATE,
        BudgetScope.PAYEES_CREATE,
        BudgetScope.PAYEES_DELETE,
        BudgetScope.PAYEES_READ,
        BudgetScope.PAYEES_UPDATE,
        BudgetScope.RECURRING_CREATE,
        BudgetScope.RECURRING_DELETE,
        BudgetScope.RECURRING_READ,
        BudgetScope.RECURRING_UPDATE,
        BudgetScope.BUDGET_DELETE,
        BudgetScope.BUDGET_READ,
        BudgetScope.BUDGET_UPDATE,
        BudgetScope.TRANSACTIONS_CREATE,
        BudgetScope.TRANSACTIONS_DELETE,
        BudgetScope.TRANSACTIONS_READ,
        BudgetScope.TRANSACTIONS_UPDATE,
    },
    BudgetRole.ADMIN: {
        BudgetScope.ACCOUNTS_CREATE,
        BudgetScope.ACCOUNTS_READ,
        BudgetScope.ACCOUNTS_UPDATE,
        BudgetScope.ALLOCATIONS_CREATE,
        BudgetScope.ALLOCATIONS_DELETE,
        BudgetScope.ALLOCATIONS_READ,
        BudgetScope.ALLOCATIONS_UPDATE,
        BudgetScope.ALLOCATION_RULES_CREATE,
        BudgetScope.ALLOCATION_RULES_DELETE,
        BudgetScope.ALLOCATION_RULES_READ,
        BudgetScope.ALLOCATION_RULES_UPDATE,
        BudgetScope.ENVELOPE_GROUPS_CREATE,
        BudgetScope.ENVELOPE_GROUPS_DELETE,
        BudgetScope.ENVELOPE_GROUPS_READ,
        BudgetScope.ENVELOPE_GROUPS_UPDATE,
        BudgetScope.ENVELOPES_CREATE,
        BudgetScope.ENVELOPES_DELETE,
        BudgetScope.ENVELOPES_READ,
        BudgetScope.ENVELOPES_UPDATE,
        BudgetScope.LOCATIONS_CREATE,
        BudgetScope.LOCATIONS_READ,
        BudgetScope.LOCATIONS_UPDATE,
        BudgetScope.MEMBERS_ADD,
        BudgetScope.MEMBERS_READ,
        BudgetScope.MEMBERS_REMOVE,
        BudgetScope.NOTIFICATIONS_READ,
        BudgetScope.NOTIFICATIONS_UPDATE,
        BudgetScope.PAYEES_CREATE,
        BudgetScope.PAYEES_READ,
        BudgetScope.PAYEES_UPDATE,
        BudgetScope.RECURRING_CREATE,
        BudgetScope.RECURRING_READ,
        BudgetScope.RECURRING_UPDATE,
        BudgetScope.BUDGET_READ,
        BudgetScope.BUDGET_UPDATE,
        BudgetScope.TRANSACTIONS_CREATE,
        BudgetScope.TRANSACTIONS_READ,
        BudgetScope.TRANSACTIONS_UPDATE,
    },
    BudgetRole.MEMBER: {
        BudgetScope.ACCOUNTS_READ,
        BudgetScope.ALLOCATIONS_CREATE,
        BudgetScope.ALLOCATIONS_READ,
        BudgetScope.ALLOCATIONS_UPDATE,
        BudgetScope.ALLOCATION_RULES_CREATE,
        BudgetScope.ALLOCATION_RULES_READ,
        BudgetScope.ALLOCATION_RULES_UPDATE,
        BudgetScope.ENVELOPE_GROUPS_CREATE,
        BudgetScope.ENVELOPE_GROUPS_READ,
        BudgetScope.ENVELOPE_GROUPS_UPDATE,
        BudgetScope.ENVELOPES_CREATE,
        BudgetScope.ENVELOPES_READ,
        BudgetScope.ENVELOPES_UPDATE,
        BudgetScope.LOCATIONS_READ,
        BudgetScope.NOTIFICATIONS_READ,
        BudgetScope.NOTIFICATIONS_UPDATE,
        BudgetScope.PAYEES_READ,
        BudgetScope.RECURRING_CREATE,
        BudgetScope.RECURRING_READ,
        BudgetScope.RECURRING_UPDATE,
        BudgetScope.BUDGET_READ,
        BudgetScope.TRANSACTIONS_CREATE,
        BudgetScope.TRANSACTIONS_READ,
        BudgetScope.TRANSACTIONS_UPDATE,
    },
    BudgetRole.VIEWER: {
        BudgetScope.ACCOUNTS_READ,
        BudgetScope.ALLOCATIONS_READ,
        BudgetScope.ALLOCATION_RULES_READ,
        BudgetScope.ENVELOPE_GROUPS_READ,
        BudgetScope.ENVELOPES_READ,
        BudgetScope.LOCATIONS_READ,
        BudgetScope.NOTIFICATIONS_READ,
        BudgetScope.PAYEES_READ,
        BudgetScope.RECURRING_READ,
        BudgetScope.BUDGET_READ,
        BudgetScope.TRANSACTIONS_READ,
    },
}


def get_effective_scopes(
    role: BudgetRole,
    scope_additions: list[str] | None = None,
    scope_removals: list[str] | None = None,
) -> set[str]:
    """Calculate effective scopes for a membership."""
    base_scopes = {s.value for s in ROLE_SCOPES.get(role, set())}

    if scope_additions:
        base_scopes.update(scope_additions)
    if scope_removals:
        base_scopes -= set(scope_removals)

    return base_scopes
