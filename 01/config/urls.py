from django.contrib import admin
from django.urls import path

from core.views import (
    current_household,
    chore_create,
    chore_delete,
    chore_edit,
    chore_list,
    household_create,
    household_join,
    member_management,
    remove_member,
    smoke_page,
)


urlpatterns = [
    path("", smoke_page, name="home"),
    path("households/create/", household_create, name="household-create"),
    path("households/join/", household_join, name="household-join"),
    path("households/current/", current_household, name="current-household"),
    path("households/chores/", chore_list, name="chore-list"),
    path("households/chores/create/", chore_create, name="chore-create"),
    path("households/chores/<int:chore_id>/edit/", chore_edit, name="chore-edit"),
    path("households/chores/<int:chore_id>/delete/", chore_delete, name="chore-delete"),
    path("households/members/", member_management, name="member-management"),
    path(
        "households/members/<int:member_id>/remove/",
        remove_member,
        name="member-remove",
    ),
    path("admin/", admin.site.urls),
]
