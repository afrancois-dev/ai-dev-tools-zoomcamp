import secrets

from django.db import IntegrityError, transaction
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .authorization import active_member_required, creator_required
from .forms import ChoreForm, HouseholdCreationForm, HouseholdJoinForm
from .models import Chore, Household, Member
from .session import SESSION_MEMBER_ID


INVITE_CODE_ATTEMPTS = 5


class InviteCodeGenerationError(Exception):
    """Raised when a unique invite code cannot be allocated."""


def generate_invite_code():
    return secrets.token_urlsafe(16)


def create_household(name, nickname):
    with transaction.atomic():
        for _ in range(INVITE_CODE_ATTEMPTS):
            invite_code = generate_invite_code()
            try:
                with transaction.atomic():
                    household = Household.objects.create(
                        name=name,
                        invite_code=invite_code,
                    )
            except IntegrityError:
                if Household.objects.filter(invite_code=invite_code).exists():
                    continue
                raise

            member = Member.objects.create(
                household=household,
                nickname=nickname,
                active=True,
            )
            household.creator = member
            household.save(update_fields=["creator"])
            return household

    raise InviteCodeGenerationError


def smoke_page(request):
    return render(request, "core/smoke.html")


def household_create(request):
    form = HouseholdCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            household = create_household(
                name=form.cleaned_data["name"],
                nickname=form.cleaned_data["nickname"],
            )
        except InviteCodeGenerationError:
            form.add_error(
                None,
                "We could not generate an invite code. Please try again.",
            )
        else:
            request.session[SESSION_MEMBER_ID] = household.creator_id
            return render(
                request,
                "core/household_created.html",
                {"household": household},
            )

    return render(request, "core/household_create.html", {"form": form})


def household_join(request):
    form = HouseholdJoinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        invite_code = form.cleaned_data["invite_code"]
        nickname = form.cleaned_data["nickname"]
        member = None

        try:
            with transaction.atomic():
                household = Household.objects.select_for_update().get(
                    invite_code=invite_code,
                )
                if Member.objects.filter(
                    household=household,
                    nickname=nickname,
                ).exists():
                    form.add_error(
                        "nickname",
                        "That nickname is already used in this household.",
                    )
                else:
                    member = Member.objects.create(
                        household=household,
                        nickname=nickname,
                        active=True,
                    )
        except Household.DoesNotExist:
            form.add_error(
                "invite_code",
                "That invite code is not valid.",
            )
        except IntegrityError:
            # The unique constraint is the final authority if another join wins
            # the race between the duplicate check and this insert.
            form.add_error(
                "nickname",
                "That nickname is already used in this household.",
            )
        else:
            if member is not None:
                request.session[SESSION_MEMBER_ID] = member.pk
                return render(
                    request,
                    "core/household_joined.html",
                    {"household": household, "member": member},
                )

    return render(request, "core/household_join.html", {"form": form})


@require_GET
@active_member_required
def current_household(request, *, member, household):
    return render(
        request,
        "core/current_household.html",
        {"member": member, "household": household},
    )


@require_GET
@active_member_required
@creator_required
def member_management(request, *, member, household):
    return render(
        request,
        "core/member_management.html",
        {
            "household": household,
            "active_members": household.members.filter(active=True),
        },
    )


@require_POST
@creator_required
def remove_member(request, member_id, *, member, household):
    with transaction.atomic():
        removed = (
            household.members.filter(
                pk=member_id,
                active=True,
            )
            .exclude(pk=member.pk)
            .update(active=False)
        )

    context = {
        "household": household,
        "active_members": household.members.filter(active=True),
    }
    if removed:
        context["message"] = "The member was removed from the household."
    else:
        context["error"] = "That member is no longer an active household member."
    return render(request, "core/member_management.html", context)


@require_GET
@active_member_required
def chore_list(request, *, member, household):
    return render(
        request,
        "core/chore_list.html",
        {
            "member": member,
            "household": household,
            "chores": household.chores.all(),
        },
    )


@require_http_methods(["GET", "POST"])
@active_member_required
def chore_create(request, *, member, household):
    form = ChoreForm(
        request.POST if request.method == "POST" else None,
        instance=Chore(household=household),
    )
    if request.method == "POST" and form.is_valid():
        chore = form.save(commit=False)
        chore.household = household
        chore.save()
        messages.success(request, "The chore was created.")
        return redirect("chore-list")

    return render(
        request,
        "core/chore_form.html",
        {"form": form, "household": household, "member": member, "action": "Create"},
    )


@require_http_methods(["GET", "POST"])
@active_member_required
def chore_edit(request, chore_id, *, member, household):
    chore = get_object_or_404(household.chores, pk=chore_id)
    form = ChoreForm(request.POST if request.method == "POST" else None, instance=chore)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "The chore was updated.")
        return redirect("chore-list")

    return render(
        request,
        "core/chore_form.html",
        {
            "form": form,
            "household": household,
            "member": member,
            "chore": chore,
            "action": "Edit",
        },
    )


@require_POST
@active_member_required
def chore_delete(request, chore_id, *, member, household):
    chore = get_object_or_404(household.chores, pk=chore_id)
    chore.delete()
    messages.success(request, "The chore was deleted.")
    return redirect("chore-list")
