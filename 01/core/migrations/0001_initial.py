from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Household",
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
                    "invite_code",
                    models.CharField(
                        blank=True,
                        max_length=32,
                        null=True,
                        unique=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(name__regex=r"\S"),
                        name="household_name_not_blank",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Member",
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
                ("nickname", models.CharField(max_length=100)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("active", models.BooleanField(default=True)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="core.household",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(nickname__regex=r"\S"),
                        name="member_nickname_not_blank",
                    ),
                    models.UniqueConstraint(
                        fields=("household", "nickname"),
                        name="unique_member_nickname_per_household",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="household",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_households",
                to="core.member",
            ),
        ),
    ]
