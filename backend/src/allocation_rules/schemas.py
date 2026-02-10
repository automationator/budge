from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.allocation_rules.models import AllocationCapPeriodUnit, AllocationRuleType


class AllocationRuleCreate(BaseModel):
    """Input for creating an allocation rule."""

    envelope_id: UUID
    priority: int = Field(ge=0)
    rule_type: AllocationRuleType
    amount: int = Field(default=0, ge=0)  # Cents or basis points
    is_active: bool = True
    name: str | None = Field(default=None, max_length=100)
    respect_target: bool = False  # Stop allocating when envelope reaches target
    cap_period_value: int = Field(default=1, ge=1)
    cap_period_unit: AllocationCapPeriodUnit | None = None

    @model_validator(mode="after")
    def validate_rule(self) -> AllocationRuleCreate:
        if self.rule_type == AllocationRuleType.PERIOD_CAP:
            if self.cap_period_unit is None:
                raise ValueError("cap_period_unit is required for period_cap rules")
            if self.amount <= 0:
                raise ValueError("amount must be greater than 0 for period_cap rules")
        if self.rule_type == AllocationRuleType.FILL_TO_TARGET:
            self.amount = 0
        return self


class AllocationRuleUpdate(BaseModel):
    """Input for updating an allocation rule."""

    envelope_id: UUID | None = None
    priority: int | None = Field(default=None, ge=0)
    rule_type: AllocationRuleType | None = None
    amount: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    name: str | None = Field(default=None, max_length=100)
    respect_target: bool | None = None
    cap_period_value: int | None = Field(default=None, ge=1)
    cap_period_unit: AllocationCapPeriodUnit | None = None


class AllocationRuleResponse(BaseModel):
    """Response for an allocation rule."""

    id: UUID
    budget_id: UUID
    envelope_id: UUID
    priority: int
    rule_type: AllocationRuleType
    amount: int
    is_active: bool
    name: str | None
    respect_target: bool
    cap_period_value: int
    cap_period_unit: AllocationCapPeriodUnit | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class RulePreviewInput(BaseModel):
    """Input for previewing rule application."""

    amount: int = Field(gt=0)  # Income amount to distribute


class RulePreviewAllocation(BaseModel):
    """A single allocation in the preview result."""

    envelope_id: UUID
    amount: int
    rule_id: UUID
    rule_name: str | None


class RulePreviewResponse(BaseModel):
    """Response for rule preview."""

    income_amount: int
    allocations: list[RulePreviewAllocation]
    unallocated: int  # Amount not covered by any rule


class ApplyRulesAllocation(BaseModel):
    """A single allocation created by applying rules."""

    envelope_id: UUID
    envelope_name: str
    amount: int
    rule_id: UUID | None
    rule_name: str | None


class ApplyRulesResponse(BaseModel):
    """Response after applying allocation rules to unallocated money."""

    initial_unallocated: int
    allocations: list[ApplyRulesAllocation]
    final_unallocated: int
