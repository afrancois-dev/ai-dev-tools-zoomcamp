from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.contrib.staticfiles import finders
from unittest.mock import patch

from .forms import ChoreForm, HouseholdJoinForm
from .models import Chore, Household, Member
from .recurrence import (
    FlexibleWindow,
    flexible_is_overdue,
    flexible_window,
    next_due_date,
    validate_fixed_schedule,
    validate_flexible_schedule,
)
from .session import SESSION_MEMBER_ID, get_active_member


class ProjectSmokeTest(SimpleTestCase):
    def test_django_test_runner_is_configured(self):
        self.assertTrue(True)

    def test_public_smoke_page_renders_the_base_structure(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="viewport"')
        self.assertContains(response, '<main class="page-shell">')
        self.assertContains(response, "Frontend foundation ready.")
        self.assertContains(response, "htmx.org@2.0.10")
        self.assertContains(response, "integrity=\"sha384-")

    def test_project_static_asset_is_discoverable(self):
        self.assertIsNotNone(finders.find("css/site.css"))


class HouseholdModelTest(TestCase):
    def test_household_and_member_defaults_and_creator_assignment(self):
        household = Household.objects.create(name="Maple House")
        member = Member.objects.create(household=household, nickname="Alex")

        household.creator = member
        household.save(update_fields=["creator"])
        household.refresh_from_db()

        self.assertIsNotNone(household.created_at)
        self.assertIsNotNone(member.joined_at)
        self.assertTrue(member.active)
        self.assertEqual(household.creator, member)

    def test_duplicate_nickname_is_rejected_within_household(self):
        household = Household.objects.create(name="Maple House")
        Member.objects.create(household=household, nickname="Alex")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Member.objects.create(household=household, nickname="Alex")

    def test_nickname_can_be_reused_in_another_household(self):
        first = Household.objects.create(name="Maple House")
        second = Household.objects.create(name="Pine House")

        first_member = Member.objects.create(household=first, nickname="Alex")
        second_member = Member.objects.create(household=second, nickname="Alex")

        self.assertNotEqual(first_member.pk, second_member.pk)

    def test_database_rejects_blank_or_whitespace_only_values(self):
        for name in ("", "   "):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Household.objects.create(name=name)

        household = Household.objects.create(name="Maple House")
        for nickname in ("", "   "):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Member.objects.create(household=household, nickname=nickname)

    def test_database_rejects_member_without_household(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Member.objects.create(household=None, nickname="Alex")


class ChoreModelTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Maple House")

    def valid_chore_data(self):
        return {
            "household": self.household,
            "name": "Take out trash",
            "points": 10,
            "recurrence_type": Chore.FIXED,
            "recurrence_config": {"rule": "daily", "interval": 1},
        }

    def test_valid_chore_persists_required_data_and_timestamps(self):
        chore = Chore.objects.create(**self.valid_chore_data())

        self.assertEqual(chore.household, self.household)
        self.assertEqual(chore.name, "Take out trash")
        self.assertEqual(chore.points, 10)
        self.assertEqual(chore.recurrence_type, Chore.FIXED)
        self.assertEqual(chore.recurrence_config, {"rule": "daily", "interval": 1})
        self.assertIsNotNone(chore.created_at)
        self.assertIsNotNone(chore.updated_at)

    def test_recurrence_configuration_defaults_to_present_empty_object(self):
        data = self.valid_chore_data()
        del data["recurrence_config"]

        chore = Chore.objects.create(**data)

        self.assertEqual(chore.recurrence_config, {})

    def test_supported_recurrence_categories_validate(self):
        for recurrence_type in (Chore.FIXED, Chore.FLEXIBLE):
            with self.subTest(recurrence_type=recurrence_type):
                data = self.valid_chore_data()
                data["recurrence_type"] = recurrence_type
                if recurrence_type == Chore.FLEXIBLE:
                    data["recurrence_config"] = {
                        "rule": "flexible",
                        "start_date": "2024-01-15",
                        "period": "month",
                        "interval": 1,
                        "window_start": 0,
                        "deadline": 6,
                    }
                chore = Chore(**data)
                chore.full_clean()

    def test_flexible_recurrence_configuration_is_validated_by_the_model(self):
        data = self.valid_chore_data()
        data["recurrence_type"] = Chore.FLEXIBLE
        data["recurrence_config"] = {
            "rule": "flexible",
            "start_date": "2024-01-15",
            "period": "month",
            "interval": 0,
            "window_start": 0,
            "deadline": 6,
        }

        with self.assertRaises(ValidationError) as context:
            Chore(**data).full_clean()

        self.assertIn("recurrence_config", context.exception.message_dict)

    def test_name_rejects_blank_and_whitespace_only_values(self):
        for name in ("", "   ", "\t"):
            with self.subTest(name=name):
                data = self.valid_chore_data()
                data["name"] = name
                chore = Chore(**data)
                with self.assertRaises(ValidationError):
                    chore.full_clean()

    def test_points_accept_only_integer_values_from_one_through_one_hundred(self):
        for points in (1, 100):
            with self.subTest(points=points):
                data = self.valid_chore_data()
                data["points"] = points
                chore = Chore(**data)
                chore.full_clean()

        for points in (0, -1, 101, 1.5, "not-an-integer"):
            with self.subTest(points=points):
                data = self.valid_chore_data()
                data["points"] = points
                chore = Chore(**data)
                with self.assertRaises(ValidationError):
                    chore.full_clean()

    def test_database_rejects_invalid_points_and_missing_household(self):
        for points in (0, 101):
            with self.subTest(points=points), self.assertRaises(IntegrityError):
                data = self.valid_chore_data()
                data["points"] = points
                with transaction.atomic():
                    Chore.objects.create(**data)

        with self.assertRaises(IntegrityError), transaction.atomic():
            data = self.valid_chore_data()
            data["household"] = None
            Chore.objects.create(**data)

    def test_recurrence_configuration_cannot_be_null(self):
        data = self.valid_chore_data()
        data["recurrence_config"] = None
        chore = Chore(**data)

        with self.assertRaises(ValidationError):
            chore.full_clean()

        with self.assertRaises(IntegrityError), transaction.atomic():
            Chore.objects.create(**data)


class FixedScheduleTest(SimpleTestCase):
    def test_daily_and_weekly_configurations_are_valid(self):
        validate_fixed_schedule("daily", {"rule": "daily", "interval": 2})
        validate_fixed_schedule("weekly", {"rule": "weekly", "weekday": 0})

    def test_invalid_and_incompatible_configurations_are_rejected(self):
        invalid_configs = (
            ("daily", {"rule": "daily"}),
            ("daily", {"rule": "daily", "interval": 0}),
            ("daily", {"rule": "daily", "interval": -1}),
            ("daily", {"rule": "daily", "interval": True}),
            ("daily", {"rule": "daily", "interval": 1, "weekday": 0}),
            ("weekly", {"rule": "weekly"}),
            ("weekly", {"rule": "weekly", "weekday": -1}),
            ("weekly", {"rule": "weekly", "weekday": 7}),
            ("weekly", {"rule": "weekly", "weekday": 1, "interval": 1}),
            ("monthly", {"rule": "monthly"}),
            ("daily", []),
        )

        for schedule_type, config in invalid_configs:
            with self.subTest(schedule_type=schedule_type, config=config):
                with self.assertRaises(ValidationError):
                    validate_fixed_schedule(schedule_type, config)

    def test_daily_next_date_is_exclusive_by_default_and_inclusive_on_request(self):
        reference = date(2024, 2, 28)

        self.assertEqual(
            next_due_date("daily", {"rule": "daily", "interval": 1}, reference),
            date(2024, 2, 29),
        )
        self.assertEqual(
            next_due_date(
                "daily", {"rule": "daily", "interval": 1}, reference, inclusive=True
            ),
            reference,
        )

    def test_weekly_next_date_handles_same_day_and_year_boundary(self):
        config = {"rule": "weekly", "weekday": 0}
        monday = date(2023, 12, 25)

        self.assertEqual(next_due_date("weekly", config, monday), date(2024, 1, 1))
        self.assertEqual(
            next_due_date("weekly", config, monday, inclusive=True), monday
        )
        self.assertEqual(
            next_due_date("weekly", config, date(2023, 12, 31)), date(2024, 1, 1)
        )

    def test_next_date_rejects_datetime_reference(self):
        with self.assertRaises(TypeError):
            next_due_date(
                "daily",
                {"rule": "daily", "interval": 1},
                datetime(2024, 1, 1),
            )


class FlexibleScheduleTest(SimpleTestCase):
    def setUp(self):
        self.config = {
            "rule": "flexible",
            "start_date": "2024-01-15",
            "period": "month",
            "interval": 1,
            "window_start": 0,
            "deadline": 6,
        }

    def test_valid_configuration_returns_first_window(self):
        validate_flexible_schedule(self.config)

        self.assertEqual(
            flexible_window(self.config, 0),
            FlexibleWindow(date(2024, 1, 15), date(2024, 1, 21)),
        )

    def test_invalid_missing_malformed_irrelevant_and_window_values_are_rejected(self):
        invalid_configs = (
            {**self.config, "start_date": "2024/01/15"},
            {**self.config, "start_date": "2024-02-30"},
            {**self.config, "interval": 0},
            {**self.config, "interval": True},
            {**self.config, "window_start": -1},
            {**self.config, "deadline": 0},
            {**self.config, "deadline": 4, "window_start": 4},
            {**self.config, "extra": "unsupported"},
            {key: value for key, value in self.config.items() if key != "start_date"},
        )
        for config in invalid_configs:
            with self.subTest(config=config), self.assertRaises(ValidationError):
                validate_flexible_schedule(config)

    def test_later_periods_use_calendar_months_and_year_boundaries(self):
        self.config.update(start_date="2023-12-31", period="month", deadline=2)
        self.assertEqual(
            flexible_window(self.config, 1),
            FlexibleWindow(date(2024, 1, 31), date(2024, 2, 2)),
        )

        self.config.update(start_date="2023-02-28", period="year", deadline=2)
        self.assertEqual(
            flexible_window(self.config, 1),
            FlexibleWindow(date(2024, 2, 28), date(2024, 3, 1)),
        )

    def test_period_index_must_be_a_nonnegative_integer(self):
        with self.assertRaises(ValueError):
            flexible_window(self.config, -1)
        with self.assertRaises(ValueError):
            flexible_window(self.config, True)

    def test_deadline_is_not_overdue_but_the_next_date_is(self):
        window = flexible_window(self.config, 0)

        self.assertFalse(flexible_is_overdue(window, window.deadline))
        self.assertTrue(flexible_is_overdue(window, window.deadline + timedelta(days=1)))
        self.assertFalse(
            flexible_is_overdue(window, window.deadline + timedelta(days=1), completed=True)
        )


class ChoreFormTest(TestCase):
    def test_valid_form_normalizes_name_and_parses_recurrence_json(self):
        form = ChoreForm(
            {
                "name": "  Take out trash  ",
                "points": "10",
                "recurrence_type": Chore.FIXED,
                "recurrence_config": '{"rule": "daily", "interval": 1}',
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Take out trash")
        self.assertEqual(form.cleaned_data["points"], 10)
        self.assertEqual(
            form.cleaned_data["recurrence_config"], {"rule": "daily", "interval": 1}
        )

    def test_fixed_recurrence_uses_model_schedule_validation(self):
        form = ChoreForm(
            {
                "name": "Take out trash",
                "points": "10",
                "recurrence_type": Chore.FIXED,
                "recurrence_config": '{"rule": "daily", "interval": 0}',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("recurrence_config", form.errors)

    def test_flexible_recurrence_uses_model_window_validation(self):
        form = ChoreForm(
            {
                "name": "Take out trash",
                "points": "10",
                "recurrence_type": Chore.FLEXIBLE,
                "recurrence_config": '{"rule": "flexible", "interval": 1}',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("recurrence_config", form.errors)

    def test_invalid_name_points_and_recurrence_have_visible_errors(self):
        form = ChoreForm(
            {
                "name": "   ",
                "points": "101",
                "recurrence_type": "unsupported",
                "recurrence_config": "not json",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("points", form.errors)
        self.assertIn("recurrence_type", form.errors)
        self.assertIn("recurrence_config", form.errors)


class ChoreRequestTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Maple House")
        self.member = Member.objects.create(household=self.household, nickname="Sam")
        self.other_household = Household.objects.create(name="Pine House")
        self.other_member = Member.objects.create(
            household=self.other_household,
            nickname="Pat",
        )
        self.chore = Chore.objects.create(
            household=self.household,
            name="Take out trash",
            points=10,
            recurrence_type=Chore.FIXED,
            recurrence_config={"rule": "daily", "interval": 1},
        )
        self.other_chore = Chore.objects.create(
            household=self.other_household,
            name="Wash windows",
            points=20,
            recurrence_type=Chore.FLEXIBLE,
            recurrence_config={"rule": "later"},
        )

    def use_member_session(self, member_id):
        session = self.client.session
        session[SESSION_MEMBER_ID] = member_id
        session.save()

    def test_list_is_scoped_to_active_members_household(self):
        self.use_member_session(self.member.pk)

        response = self.client.get(reverse("chore-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.chore.name)
        self.assertNotContains(response, self.other_chore.name)

    def test_active_member_can_create_chore_and_is_redirected(self):
        self.use_member_session(self.member.pk)

        response = self.client.post(
            reverse("chore-create"),
            {
                "name": "  Clean kitchen  ",
                "points": "15",
                "recurrence_type": Chore.FIXED,
                "recurrence_config": '{"rule": "weekly", "weekday": 0}',
            },
        )

        self.assertRedirects(response, reverse("chore-list"))
        created = Chore.objects.get(name="Clean kitchen")
        self.assertEqual(created.household, self.household)
        self.assertEqual(created.points, 15)
        self.assertEqual(
            created.recurrence_config, {"rule": "weekly", "weekday": 0}
        )

    def test_active_member_can_edit_household_chore(self):
        self.use_member_session(self.member.pk)

        response = self.client.post(
            reverse("chore-edit", args=[self.chore.pk]),
            {
                "name": "Clean kitchen",
                "points": "25",
                "recurrence_type": Chore.FLEXIBLE,
                "recurrence_config": (
                    '{"rule": "flexible", "start_date": "2024-01-15", '
                    '"period": "month", "interval": 1, "window_start": 0, '
                    '"deadline": 6}'
                ),
            },
        )

        self.assertRedirects(response, reverse("chore-list"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.name, "Clean kitchen")
        self.assertEqual(self.chore.points, 25)
        self.assertEqual(self.chore.recurrence_type, Chore.FLEXIBLE)
        self.assertEqual(
            self.chore.recurrence_config,
            {
                "rule": "flexible",
                "start_date": "2024-01-15",
                "period": "month",
                "interval": 1,
                "window_start": 0,
                "deadline": 6,
            },
        )

    def test_active_member_can_delete_chore_only_with_post(self):
        self.use_member_session(self.member.pk)

        get_response = self.client.get(reverse("chore-delete", args=[self.chore.pk]))
        post_response = self.client.post(reverse("chore-delete", args=[self.chore.pk]))

        self.assertEqual(get_response.status_code, 405)
        self.assertRedirects(post_response, reverse("chore-list"))
        self.assertFalse(Chore.objects.filter(pk=self.chore.pk).exists())

    def test_invalid_create_is_visible_and_does_not_save(self):
        self.use_member_session(self.member.pk)

        response = self.client.post(
            reverse("chore-create"),
            {
                "name": " ",
                "points": "101",
                "recurrence_type": "unsupported",
                "recurrence_config": "not json",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ensure this value is less than or equal to 100")
        self.assertEqual(Chore.objects.count(), 2)

    def test_missing_or_inactive_session_cannot_list_or_mutate(self):
        for method, url, data in (
            (self.client.get, reverse("chore-list"), None),
            (self.client.post, reverse("chore-create"), {}),
            (self.client.post, reverse("chore-delete", args=[self.chore.pk]), {}),
        ):
            with self.subTest(url=url):
                response = method(url, data) if data is not None else method(url)
                self.assertEqual(response.status_code, 403)

        self.use_member_session(self.member.pk)
        self.member.active = False
        self.member.save(update_fields=["active"])
        response = self.client.get(reverse("chore-list"))
        self.assertEqual(response.status_code, 403)

    def test_cross_household_chore_identifier_is_not_read_or_mutated(self):
        self.use_member_session(self.member.pk)

        edit_response = self.client.get(reverse("chore-edit", args=[self.other_chore.pk]))
        delete_response = self.client.post(
            reverse("chore-delete", args=[self.other_chore.pk])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(Chore.objects.filter(pk=self.other_chore.pk).exists())


class HouseholdCreationRequestTest(TestCase):
    def test_creation_page_displays_required_fields(self):
        response = self.client.get(reverse("household-create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="nickname"')

    def test_valid_submission_creates_household_member_and_creator(self):
        response = self.client.post(
            reverse("household-create"),
            {"name": "Maple House", "nickname": "Alex"},
        )

        self.assertEqual(response.status_code, 200)
        household = Household.objects.get()
        member = Member.objects.get()
        self.assertEqual(household.name, "Maple House")
        self.assertTrue(household.invite_code)
        self.assertEqual(household.creator, member)
        self.assertTrue(member.active)
        self.assertEqual(member.nickname, "Alex")
        self.assertContains(response, household.invite_code)
        self.assertContains(response, 'readonly')
        self.assertEqual(response.context["household"], household)
        self.assertEqual(self.client.session[SESSION_MEMBER_ID], member.pk)

    def test_blank_values_are_rejected_without_creating_records(self):
        response = self.client.post(
            reverse("household-create"),
            {"name": "   ", "nickname": "\t"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a household name.")
        self.assertContains(response, "Enter a nickname.")
        self.assertFalse(Household.objects.exists())
        self.assertFalse(Member.objects.exists())

    @patch("core.views.generate_invite_code", side_effect=["taken", "available"])
    def test_invite_code_collision_retries_without_partial_records(self, generate_code):
        Household.objects.create(name="Existing", invite_code="taken")

        response = self.client.post(
            reverse("household-create"),
            {"name": "Maple House", "nickname": "Alex"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate_code.call_count, 2)
        self.assertEqual(Household.objects.count(), 2)
        created = Household.objects.get(name="Maple House")
        self.assertEqual(created.invite_code, "available")
        self.assertEqual(Member.objects.count(), 1)

    @patch("core.views.generate_invite_code", return_value="taken")
    def test_exhausted_invite_code_collisions_are_controlled_and_atomic(self, generate_code):
        Household.objects.create(name="Existing", invite_code="taken")

        response = self.client.post(
            reverse("household-create"),
            {"name": "Maple House", "nickname": "Alex"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We could not generate an invite code.")
        self.assertEqual(generate_code.call_count, 5)
        self.assertFalse(Household.objects.filter(name="Maple House").exists())
        self.assertFalse(Member.objects.exists())


class HouseholdJoinFormTest(SimpleTestCase):
    def test_normalization_trims_both_fields_and_preserves_invite_code_case(self):
        form = HouseholdJoinForm(
            {"invite_code": "  AbC123  ", "nickname": "  Sam  "}
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["invite_code"], "AbC123")
        self.assertEqual(form.cleaned_data["nickname"], "Sam")

    def test_blank_values_have_field_errors(self):
        form = HouseholdJoinForm({"invite_code": "\t", "nickname": "   "})

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["invite_code"], ["Enter an invite code."])
        self.assertEqual(form.errors["nickname"], ["Enter a nickname."])


class HouseholdJoinRequestTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(
            name="Maple House",
            invite_code="AbC123",
        )
        self.other_household = Household.objects.create(
            name="Pine House",
            invite_code="Pine456",
        )

    def test_join_page_displays_required_fields(self):
        response = self.client.get(reverse("household-join"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="invite_code"')
        self.assertContains(response, 'name="nickname"')
        self.assertContains(response, "Invite codes are case-sensitive")

    def test_valid_join_trims_input_and_creates_one_active_member(self):
        response = self.client.post(
            reverse("household-join"),
            {"invite_code": "  AbC123  ", "nickname": "  Sam  "},
        )

        self.assertEqual(response.status_code, 200)
        member = Member.objects.get()
        self.assertEqual(member.household, self.household)
        self.assertEqual(member.nickname, "Sam")
        self.assertTrue(member.active)
        self.assertEqual(Member.objects.count(), 1)
        self.assertContains(response, "You joined Maple House.")
        self.assertEqual(self.client.session[SESSION_MEMBER_ID], member.pk)

    def test_invite_code_matching_is_case_sensitive(self):
        response = self.client.post(
            reverse("household-join"),
            {"invite_code": "abc123", "nickname": "Sam"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That invite code is not valid.")
        self.assertEqual(Member.objects.count(), 0)

    def test_unknown_or_malformed_code_has_safe_error_and_no_member(self):
        for invite_code in ("missing", "x" * 33):
            with self.subTest(invite_code=invite_code):
                response = self.client.post(
                    reverse("household-join"),
                    {"invite_code": invite_code, "nickname": "Sam"},
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "That invite code is not valid.")
                self.assertEqual(Member.objects.count(), 0)
                self.assertNotContains(response, "Pine House")

    def test_duplicate_nickname_has_error_and_does_not_change_membership(self):
        existing = Member.objects.create(
            household=self.household,
            nickname="Sam",
            active=False,
        )

        response = self.client.post(
            reverse("household-join"),
            {"invite_code": self.household.invite_code, "nickname": "Sam"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That nickname is already used in this household.")
        self.assertEqual(Member.objects.count(), 1)
        existing.refresh_from_db()
        self.assertFalse(existing.active)

    def test_blank_nickname_has_error_and_does_not_create_member(self):
        response = self.client.post(
            reverse("household-join"),
            {"invite_code": self.household.invite_code, "nickname": "  "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a nickname.")
        self.assertEqual(Member.objects.count(), 0)

    def test_failed_join_cannot_create_member_in_another_household(self):
        response = self.client.post(
            reverse("household-join"),
            {"invite_code": "missing", "nickname": "Sam"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Member.objects.filter(household=self.other_household).count(), 0)
        self.assertEqual(Member.objects.count(), 0)

    @patch("core.views.Member.objects.create", side_effect=IntegrityError)
    def test_uniqueness_race_returns_controlled_error_without_member(self, create_member):
        response = self.client.post(
            reverse("household-join"),
            {"invite_code": self.household.invite_code, "nickname": "Sam"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That nickname is already used in this household.")
        self.assertEqual(create_member.call_count, 1)
        self.assertEqual(Member.objects.count(), 0)


class MemberSessionTest(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.household = Household.objects.create(name="Maple House")
        self.member = Member.objects.create(
            household=self.household,
            nickname="Alex",
        )
        self.other_household = Household.objects.create(name="Pine House")
        self.other_member = Member.objects.create(
            household=self.other_household,
            nickname="Alex",
        )

    def request_with_session(self):
        request = self.request_factory.get("/")
        request.session = self.client.session
        return request

    def test_active_member_lookup_returns_member_and_database_household(self):
        session = self.client.session
        session[SESSION_MEMBER_ID] = self.member.pk
        session.save()

        member = get_active_member(self.request_with_session())

        self.assertEqual(member, self.member)
        self.assertEqual(member.household, self.household)

    def test_missing_member_session_is_unauthenticated(self):
        request = self.request_with_session()

        self.assertIsNone(get_active_member(request))

    def test_non_integer_member_session_values_are_cleared(self):
        for member_id in (1.5, True, False, "", "1.5", "not-a-member-id", None):
            with self.subTest(member_id=member_id):
                session = self.client.session
                session[SESSION_MEMBER_ID] = member_id
                session.save()

                request = self.request_with_session()

                self.assertIsNone(get_active_member(request))
                self.assertNotIn(SESSION_MEMBER_ID, request.session)

    def test_inactive_member_session_is_cleared(self):
        self.member.active = False
        self.member.save(update_fields=["active"])
        session = self.client.session
        session[SESSION_MEMBER_ID] = self.member.pk
        session.save()

        request = self.request_with_session()

        self.assertIsNone(get_active_member(request))
        self.assertNotIn(SESSION_MEMBER_ID, request.session)

    def test_deleted_member_session_is_cleared(self):
        member_id = self.member.pk
        self.member.delete()
        session = self.client.session
        session[SESSION_MEMBER_ID] = member_id
        session.save()

        request = self.request_with_session()

        self.assertIsNone(get_active_member(request))
        self.assertNotIn(SESSION_MEMBER_ID, request.session)

    def test_session_member_id_cannot_override_persisted_household(self):
        session = self.client.session
        session[SESSION_MEMBER_ID] = self.other_member.pk
        session.save()

        member = get_active_member(self.request_with_session())

        self.assertEqual(member, self.other_member)
        self.assertEqual(member.household_id, self.other_household.pk)


class ActiveMemberRequestTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Maple House")
        self.member = Member.objects.create(
            household=self.household,
            nickname="Sam",
        )
        self.other_household = Household.objects.create(name="Pine House")
        self.other_member = Member.objects.create(
            household=self.other_household,
            nickname="Pat",
        )

    def use_member_session(self, member_id):
        session = self.client.session
        session[SESSION_MEMBER_ID] = member_id
        session.save()

    def test_active_member_sees_only_persisted_household_context(self):
        self.use_member_session(self.member.pk)

        response = self.client.get(reverse("current-household"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.household.name)
        self.assertContains(response, self.member.nickname)
        self.assertNotContains(response, self.other_household.name)
        self.assertNotContains(response, self.other_member.nickname)

    def test_missing_malformed_and_inactive_sessions_are_denied_safely(self):
        cases = (None, "not-a-member-id", self.member.pk)
        self.member.active = False
        self.member.save(update_fields=["active"])

        for member_id in cases:
            with self.subTest(member_id=member_id):
                if member_id is None:
                    self.client.session.flush()
                else:
                    self.use_member_session(member_id)

                response = self.client.get(reverse("current-household"))

                self.assertEqual(response.status_code, 403)
                self.assertContains(
                    response,
                    "You must be an active household member to access this page.",
                    status_code=403,
                )
                self.assertNotContains(response, self.household.name, status_code=403)
                self.assertNotContains(
                    response,
                    self.other_household.name,
                    status_code=403,
                )


class MemberRemovalRequestTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Maple House")
        self.creator = Member.objects.create(
            household=self.household,
            nickname="Alex",
        )
        self.household.creator = self.creator
        self.household.save(update_fields=["creator"])
        self.member = Member.objects.create(
            household=self.household,
            nickname="Sam",
        )
        self.other_household = Household.objects.create(name="Pine House")
        self.other_member = Member.objects.create(
            household=self.other_household,
            nickname="Pat",
        )

    def use_member_session(self, member):
        session = self.client.session
        session[SESSION_MEMBER_ID] = member.pk
        session.save()

    def test_creator_can_view_management_and_remove_active_member(self):
        self.use_member_session(self.creator)

        response = self.client.get(reverse("member-management"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.creator.nickname)
        self.assertContains(response, self.member.nickname)

        response = self.client.post(
            reverse("member-remove", args=[self.member.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The member was removed from the household.")
        self.member.refresh_from_db()
        self.assertFalse(self.member.active)
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())

    def test_creator_cannot_remove_themself(self):
        self.use_member_session(self.creator)

        response = self.client.post(
            reverse("member-remove", args=[self.creator.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That member is no longer an active household member.")
        self.creator.refresh_from_db()
        self.assertTrue(self.creator.active)

    def test_non_creator_cannot_view_or_remove_members(self):
        self.use_member_session(self.member)

        page_response = self.client.get(reverse("member-management"))
        remove_response = self.client.post(
            reverse("member-remove", args=[self.creator.pk]),
        )

        self.assertEqual(page_response.status_code, 403)
        self.assertEqual(remove_response.status_code, 403)
        self.creator.refresh_from_db()
        self.assertTrue(self.creator.active)

    def test_missing_session_cannot_remove_members(self):
        response = self.client.post(
            reverse("member-remove", args=[self.member.pk]),
        )

        self.assertEqual(response.status_code, 403)
        self.member.refresh_from_db()
        self.assertTrue(self.member.active)

    def test_cross_household_target_does_not_change_membership(self):
        self.use_member_session(self.creator)

        response = self.client.post(
            reverse("member-remove", args=[self.other_member.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That member is no longer an active household member.")
        self.assertNotContains(response, self.other_household.name)
        self.other_member.refresh_from_db()
        self.assertTrue(self.other_member.active)

    def test_missing_and_inactive_targets_return_safe_result(self):
        self.use_member_session(self.creator)
        self.member.active = False
        self.member.save(update_fields=["active"])

        for member_id in (self.member.pk, 999999):
            with self.subTest(member_id=member_id):
                response = self.client.post(
                    reverse("member-remove", args=[member_id]),
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "That member is no longer an active household member.",
                )

        self.member.refresh_from_db()
        self.assertFalse(self.member.active)

    def test_removed_members_existing_session_is_rejected(self):
        self.use_member_session(self.creator)
        self.client.post(reverse("member-remove", args=[self.member.pk]))

        self.use_member_session(self.member)
        response = self.client.get(reverse("member-management"))

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(SESSION_MEMBER_ID, self.client.session)

    def test_malformed_session_has_the_shared_active_member_failure(self):
        session = self.client.session
        session[SESSION_MEMBER_ID] = "not-a-member-id"
        session.save()

        response = self.client.get(reverse("member-management"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You must be an active household member to access this page.",
            status_code=403,
        )
        self.assertNotIn(SESSION_MEMBER_ID, self.client.session)

    def test_inactive_session_has_the_shared_creator_failure(self):
        self.use_member_session(self.creator)
        self.creator.active = False
        self.creator.save(update_fields=["active"])

        response = self.client.get(reverse("member-management"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You must be an active household member to access this page.",
            status_code=403,
        )
        self.assertNotIn(SESSION_MEMBER_ID, self.client.session)

    def test_non_creator_gets_shared_creator_failure_without_household_data(self):
        self.use_member_session(self.member)

        response = self.client.get(reverse("member-management"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Only the household creator can manage members.",
            status_code=403,
        )
        self.assertNotContains(
            response,
            self.household.name,
            status_code=403,
        )

    def test_cross_household_target_uses_same_safe_failure_as_missing_target(self):
        self.use_member_session(self.creator)

        cross_household_response = self.client.post(
            reverse("member-remove", args=[self.other_member.pk]),
        )
        missing_response = self.client.post(
            reverse("member-remove", args=[999999]),
        )

        self.assertEqual(cross_household_response.status_code, 200)
        self.assertEqual(missing_response.status_code, 200)
        safe_error = "That member is no longer an active household member."
        self.assertContains(cross_household_response, safe_error)
        self.assertContains(missing_response, safe_error)
