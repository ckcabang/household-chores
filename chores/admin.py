from django.contrib import admin

from .models import Household, Invitation, Membership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "member_count", "created_at")
    search_fields = ("name",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "household", "created_at")
    list_select_related = ("user", "household")
    search_fields = ("user__username", "household__name")


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
