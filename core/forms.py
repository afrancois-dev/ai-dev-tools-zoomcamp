from django import forms

from .models import Chore


class HouseholdCreationForm(forms.Form):
    name = forms.CharField(
        label="Household name",
        max_length=200,
        required=True,
        error_messages={"required": "Enter a household name."},
    )
    nickname = forms.CharField(
        label="Your nickname",
        max_length=100,
        required=True,
        error_messages={"required": "Enter a nickname."},
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter a household name.")
        return name

    def clean_nickname(self):
        nickname = self.cleaned_data["nickname"].strip()
        if not nickname:
            raise forms.ValidationError("Enter a nickname.")
        return nickname


class HouseholdJoinForm(forms.Form):
    invite_code = forms.CharField(
        label="Invite code",
        max_length=32,
        required=True,
        error_messages={
            "required": "Enter an invite code.",
            "max_length": "That invite code is not valid.",
        },
        help_text="Invite codes are case-sensitive; surrounding spaces are ignored.",
    )
    nickname = forms.CharField(
        label="Your nickname",
        max_length=100,
        required=True,
        error_messages={"required": "Enter a nickname."},
        help_text="Surrounding spaces are ignored.",
    )

    def clean_invite_code(self):
        invite_code = self.cleaned_data["invite_code"].strip()
        if not invite_code:
            raise forms.ValidationError("Enter an invite code.")
        return invite_code

    def clean_nickname(self):
        nickname = self.cleaned_data["nickname"].strip()
        if not nickname:
            raise forms.ValidationError("Enter a nickname.")
        return nickname


class ChoreForm(forms.ModelForm):
    recurrence_config = forms.JSONField(
        label="Recurrence configuration",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=(
            "Enter recurrence JSON. Flexible rules use start_date, period, interval, "
            "window_start, and deadline."
        ),
    )

    class Meta:
        model = Chore
        fields = ("name", "points", "recurrence_type", "recurrence_config")

    def clean_name(self):
        return self.cleaned_data["name"].strip()
