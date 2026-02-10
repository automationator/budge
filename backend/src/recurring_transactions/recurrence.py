"""Date calculation utilities for recurring transactions."""

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction


def calculate_next_date(
    current_date: date,
    frequency_value: int,
    frequency_unit: FrequencyUnit,
) -> date:
    """Calculate the next occurrence date based on frequency."""
    match frequency_unit:
        case FrequencyUnit.DAYS:
            return current_date + timedelta(days=frequency_value)
        case FrequencyUnit.WEEKS:
            return current_date + timedelta(weeks=frequency_value)
        case FrequencyUnit.MONTHS:
            return current_date + relativedelta(months=frequency_value)
        case FrequencyUnit.YEARS:
            return current_date + relativedelta(years=frequency_value)


def generate_dates_until(
    rule: RecurringTransaction,
    horizon: date,
) -> list[date]:
    """Generate all occurrence dates from next_occurrence_date until horizon.

    Returns a list of dates, stopping at end_date if set.
    """
    dates: list[date] = []
    current = rule.next_occurrence_date

    while current <= horizon:
        # Stop if we've passed the end date
        if rule.end_date and current > rule.end_date:
            break

        dates.append(current)
        current = calculate_next_date(
            current,
            rule.frequency_value,
            rule.frequency_unit,
        )

    return dates
