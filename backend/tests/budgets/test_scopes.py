from src.budgets.models import BudgetRole
from src.budgets.scopes import ROLE_SCOPES, BudgetScope, get_effective_scopes


class TestGetEffectiveScopes:
    def test_owner_has_all_scopes(self) -> None:
        scopes = get_effective_scopes(BudgetRole.OWNER)
        assert BudgetScope.BUDGET_DELETE in scopes
        assert BudgetScope.BUDGET_UPDATE in scopes
        assert BudgetScope.MEMBERS_MANAGE_ROLES in scopes
        assert BudgetScope.MEMBERS_ADD in scopes
        assert BudgetScope.MEMBERS_REMOVE in scopes

    def test_admin_has_most_scopes_except_delete_and_manage_roles(self) -> None:
        scopes = get_effective_scopes(BudgetRole.ADMIN)
        assert BudgetScope.BUDGET_READ in scopes
        assert BudgetScope.BUDGET_UPDATE in scopes
        assert BudgetScope.MEMBERS_READ in scopes
        assert BudgetScope.MEMBERS_ADD in scopes
        assert BudgetScope.MEMBERS_REMOVE in scopes
        # Admin should NOT have these
        assert BudgetScope.BUDGET_DELETE not in scopes
        assert BudgetScope.MEMBERS_MANAGE_ROLES not in scopes

    def test_member_has_budget_read_only(self) -> None:
        scopes = get_effective_scopes(BudgetRole.MEMBER)
        assert BudgetScope.BUDGET_READ in scopes
        # Member should NOT have other scopes
        assert BudgetScope.MEMBERS_READ not in scopes
        assert BudgetScope.BUDGET_UPDATE not in scopes
        assert BudgetScope.MEMBERS_ADD not in scopes
        assert BudgetScope.MEMBERS_REMOVE not in scopes

    def test_viewer_has_budget_read_only(self) -> None:
        scopes = get_effective_scopes(BudgetRole.VIEWER)
        assert BudgetScope.BUDGET_READ in scopes
        # Viewer should NOT have other scopes
        assert BudgetScope.MEMBERS_READ not in scopes
        assert BudgetScope.BUDGET_UPDATE not in scopes
        assert BudgetScope.BUDGET_DELETE not in scopes
        assert BudgetScope.MEMBERS_ADD not in scopes

    def test_scope_additions(self) -> None:
        scopes = get_effective_scopes(
            BudgetRole.VIEWER,
            scope_additions=[BudgetScope.MEMBERS_ADD],
        )
        # Should have the added scope
        assert BudgetScope.MEMBERS_ADD in scopes
        # Should still have base scopes
        assert BudgetScope.BUDGET_READ in scopes

    def test_scope_removals(self) -> None:
        scopes = get_effective_scopes(
            BudgetRole.MEMBER,
            scope_removals=[BudgetScope.MEMBERS_READ],
        )
        # Should NOT have the removed scope
        assert BudgetScope.MEMBERS_READ not in scopes
        # Should still have other base scopes
        assert BudgetScope.BUDGET_READ in scopes

    def test_additions_and_removals_combined(self) -> None:
        scopes = get_effective_scopes(
            BudgetRole.MEMBER,
            scope_additions=[BudgetScope.MEMBERS_ADD],
            scope_removals=[BudgetScope.MEMBERS_READ],
        )
        # Should have the added scope
        assert BudgetScope.MEMBERS_ADD in scopes
        # Should NOT have the removed scope
        assert BudgetScope.MEMBERS_READ not in scopes
        # Should still have other base scopes
        assert BudgetScope.BUDGET_READ in scopes

    def test_empty_additions_and_removals(self) -> None:
        scopes = get_effective_scopes(
            BudgetRole.MEMBER,
            scope_additions=[],
            scope_removals=[],
        )
        # Should equal base scopes
        expected = {s.value for s in ROLE_SCOPES[BudgetRole.MEMBER]}
        assert scopes == expected

    def test_none_additions_and_removals(self) -> None:
        scopes = get_effective_scopes(
            BudgetRole.MEMBER,
            scope_additions=None,
            scope_removals=None,
        )
        # Should equal base scopes
        expected = {s.value for s in ROLE_SCOPES[BudgetRole.MEMBER]}
        assert scopes == expected

    def test_custom_scope_addition(self) -> None:
        # Test adding a custom scope not in BudgetScope enum
        scopes = get_effective_scopes(
            BudgetRole.VIEWER,
            scope_additions=["custom:scope"],
        )
        assert "custom:scope" in scopes
        assert BudgetScope.BUDGET_READ in scopes
