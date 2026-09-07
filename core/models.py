from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

from .recurrence import validate_fixed_schedule, validate_flexible_schedule


class Household(models.Model):
    name = models.CharField(max_length=200)
    invite_code = models.CharField(max_length=32, unique=True, blank=True, null=True)
    creator = models.ForeignKey(
        "Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_households",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"),
                name="household_name_not_blank",
            ),
        ]


class Member(models.Model):
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="members",
    )
    nickname = models.CharField(max_length=100)
    joined_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nickname__regex=r"\S"),
                name="member_nickname_not_blank",
            ),
            models.UniqueConstraint(
                fields=["household", "nickname"],
                name="unique_member_nickname_per_household",
            ),
        ]


class Chore(models.Model):
    FIXED = "fixed"
    FLEXIBLE = "flexible"
    RECURRENCE_TYPES = (
        (FIXED, "Fixed schedule"),
        (FLEXIBLE, "Flexible window"),
    )

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="chores",
    )
    name = models.CharField(max_length=200)
    points = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    recurrence_type = models.CharField(max_length=20, choices=RECURRENCE_TYPES)
    recurrence_config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def full_clean(self, *args, **kwargs):
        if self.points is not None and type(self.points) is not int:
            raise ValidationError({"points": "Chore points must be an integer."})
        return super().full_clean(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        if not isinstance(self.name, str) or not self.name.strip():
            errors["name"] = "Chore name cannot be blank."
        if self.points is not None and type(self.points) is not int:
            errors["points"] = "Chore points must be an integer."
        if self.recurrence_type == self.FIXED:
            try:
                schedule_type = self.recurrence_config.get("rule")
                validate_fixed_schedule(schedule_type, self.recurrence_config)
            except (AttributeError, ValidationError) as error:
                errors["recurrence_config"] = getattr(
                    error, "messages", [str(error)]
                )
        elif self.recurrence_type == self.FLEXIBLE:
            try:
                validate_flexible_schedule(self.recurrence_config)
            except ValidationError as error:
                errors["recurrence_config"] = error.messages
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"),
                name="chore_name_not_blank",
            ),
            models.CheckConstraint(
                condition=models.Q(points__gte=1, points__lte=100),
                name="chore_points_between_1_and_100",
            ),
        ]
