"""Validation and date calculations for chore recurrence rules.

The fixed schedule vocabulary is intentionally small and explicit:

* ``daily``: ``{"rule": "daily", "interval": positive_integer}``
* ``weekly``: ``{"rule": "weekly", "weekday": 0..6}``, where Monday is 0

The configuration keys are exact. A daily schedule cannot contain ``weekday``
and a weekly schedule cannot contain ``interval``. ``validate_fixed_schedule``
is the single validation API used by the Chore model and therefore by chore
forms.

``next_due_date`` works on calendar dates, consistent with the project's UTC
``TIME_ZONE`` and ``USE_TZ`` settings. It never converts a timestamp and never
writes a record. By default the reference date is exclusive: a daily schedule
returns a date after it, and a weekly schedule skips the reference date when it
is the configured weekday. With ``inclusive=True``, the reference date is
returned when it is itself due; otherwise the next due date is unchanged.
For a daily interval, the supplied reference date is treated as a due date, so
the exclusive result is exactly ``interval`` calendar days later.

Flexible rules use this exact JSON configuration::

    {
        "rule": "flexible",
        "start_date": "2024-01-15",
        "period": "month",
        "interval": 1,
        "window_start": 0,
        "deadline": 6
    }

``period`` is one of ``day``, ``week``, ``month``, or ``year``. ``interval``
is the positive number of periods between window anchors. ``window_start`` and
``deadline`` are nonnegative day offsets from the anchor; the deadline must be
strictly after the window start. The first occurrence is period ``0``. Windows
include both dates, so unfinished work is overdue only when the reference date
is after the deadline. Completed work is never overdue. All calculations use
``datetime.date`` and do not create or modify database records.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
import re

from django.core.exceptions import ValidationError


DAILY = "daily"
WEEKLY = "weekly"
FIXED_SCHEDULE_TYPES = (DAILY, WEEKLY)
FLEXIBLE = "flexible"
FLEXIBLE_PERIODS = ("day", "week", "month", "year")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class FlexibleWindow:
    """The inclusive date window for one flexible occurrence period."""

    start: date
    deadline: date


def validate_fixed_schedule(schedule_type, config):
    """Validate one fixed schedule configuration or raise ValidationError."""
    if schedule_type not in FIXED_SCHEDULE_TYPES:
        raise ValidationError("Unsupported fixed schedule type.")
    if not isinstance(config, dict):
        raise ValidationError("Fixed schedule configuration must be an object.")

    if schedule_type == DAILY:
        if set(config) != {"rule", "interval"} or config.get("rule") != DAILY:
            raise ValidationError(
                "Daily schedules require only rule='daily' and interval."
            )
        interval = config["interval"]
        if type(interval) is not int or interval <= 0:
            raise ValidationError("Daily schedule interval must be a positive integer.")
        return

    if set(config) != {"rule", "weekday"} or config.get("rule") != WEEKLY:
        raise ValidationError(
            "Weekly schedules require only rule='weekly' and weekday."
        )
    weekday = config["weekday"]
    if type(weekday) is not int or not 0 <= weekday <= 6:
        raise ValidationError("Weekly schedule weekday must be an integer from 0 to 6.")


def next_due_date(schedule_type, config, reference_date, *, inclusive=False):
    """Return the next due calendar date after or on ``reference_date``.

    ``reference_date`` must be a ``datetime.date`` rather than a datetime. A
    datetime would make the result depend on an implicit timezone conversion,
    which is outside this date-only recurrence API.
    """
    validate_fixed_schedule(schedule_type, config)
    if not isinstance(reference_date, date) or hasattr(reference_date, "hour"):
        raise TypeError("reference_date must be a datetime.date")

    if schedule_type == DAILY:
        if inclusive:
            return reference_date
        return reference_date + timedelta(days=config["interval"])

    days_until_weekday = (config["weekday"] - reference_date.weekday()) % 7
    if days_until_weekday == 0 and not inclusive:
        days_until_weekday = 7
    return reference_date + timedelta(days=days_until_weekday)


def _parse_flexible_date(value):
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValidationError("Flexible recurrence start_date must be YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValidationError("Flexible recurrence start_date must be a valid date.") from error


def validate_flexible_schedule(config):
    """Validate one flexible window configuration or raise ValidationError."""
    if not isinstance(config, dict):
        raise ValidationError("Flexible recurrence configuration must be an object.")

    required = {"rule", "start_date", "period", "interval", "window_start", "deadline"}
    if set(config) != required:
        raise ValidationError(
            "Flexible recurrence requires only rule, start_date, period, interval, "
            "window_start, and deadline."
        )
    if config["rule"] != FLEXIBLE:
        raise ValidationError("Flexible recurrence rule must be 'flexible'.")
    _parse_flexible_date(config["start_date"])
    if config["period"] not in FLEXIBLE_PERIODS:
        raise ValidationError("Flexible recurrence period is not supported.")
    if type(config["interval"]) is not int or config["interval"] <= 0:
        raise ValidationError("Flexible recurrence interval must be a positive integer.")
    for key in ("window_start", "deadline"):
        if type(config[key]) is not int or config[key] < 0:
            raise ValidationError(f"Flexible recurrence {key} must be a nonnegative integer.")
    if config["deadline"] <= config["window_start"]:
        raise ValidationError("Flexible recurrence deadline must be after window_start.")


def _add_months(value, months):
    month_number = value.month - 1 + months
    year, month = divmod(month_number, 12)
    year += value.year
    day = min(value.day, monthrange(year, month + 1)[1])
    return date(year, month + 1, day)


def _period_anchor(start_date, period, interval, occurrence_period):
    periods = interval * occurrence_period
    if period == "day":
        return start_date + timedelta(days=periods)
    if period == "week":
        return start_date + timedelta(weeks=periods)
    if period == "month":
        return _add_months(start_date, periods)
    return _add_months(start_date, periods * 12)


def flexible_window(config, occurrence_period):
    """Return the inclusive window for a zero-based occurrence period."""
    validate_flexible_schedule(config)
    if type(occurrence_period) is not int or occurrence_period < 0:
        raise ValueError("occurrence_period must be a nonnegative integer.")

    anchor = _period_anchor(
        _parse_flexible_date(config["start_date"]),
        config["period"],
        config["interval"],
        occurrence_period,
    )
    return FlexibleWindow(
        start=anchor + timedelta(days=config["window_start"]),
        deadline=anchor + timedelta(days=config["deadline"]),
    )


def flexible_is_overdue(window, as_of, *, completed=False):
    """Return whether a flexible occurrence is overdue on a calendar date."""
    if not isinstance(window, FlexibleWindow):
        raise TypeError("window must be a FlexibleWindow")
    if not isinstance(as_of, date) or hasattr(as_of, "hour"):
        raise TypeError("as_of must be a datetime.date")
    if type(completed) is not bool:
        raise TypeError("completed must be a bool")
    return not completed and as_of > window.deadline
