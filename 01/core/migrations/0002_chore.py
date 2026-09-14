from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Chore",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                (
                    "points",
                    models.IntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(100),
                        ]
                    ),
                ),
                (
                    "recurrence_type",
                    models.CharField(
                        choices=[
                            ("fixed", "Fixed schedule"),
                            ("flexible", "Flexible window"),
                        ],
                        max_length=20,
                    ),
                ),
                ("recurrence_config", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chores",
                        to="core.household",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(name__regex=r"\S"),
                        name="chore_name_not_blank",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(points__gte=1, points__lte=100),
                        name="chore_points_between_1_and_100",
                    ),
                ],
            },
        ),
    ]
