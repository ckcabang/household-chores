from django.contrib import admin

from .models import Chore, Constraint, Household, Invitation, Membership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "member_count", "created_at")
    search_fields = ("name",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "household", "created_at")
    list_select_related = ("user", "household")
    search_fields = ("user__username", "household__name")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "household",
        "cadence_days",
        "estimated_minutes",
        "difficulty",
        "primary_owner",
        "allows_multiple_contributors",
    )
    list_filter = ("household", "difficulty", "allows_multiple_contributors")
    list_select_related = ("household", "primary_owner__user")
    search_fields = ("name", "household__name")


@admin.register(Constraint)
class ConstraintAdmin(admin.ModelAdmin):
    list_display = ("chore", "membership", "kind", "created_at")
    list_filter = ("kind",)
    list_select_related = ("chore", "membership__user")
    search_fields = ("chore__name", "membership__user__username")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "household",
        "created_by",
        "created_at",
        "accepted_by",
        "accepted_at",
    )
    list_select_related = ("household", "created_by", "accepted_by")
    search_fields = ("household__name", "created_by__username", "accepted_by__username")
