from django.contrib import admin

from .models import Household, Membership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "member_count", "created_at")
    search_fields = ("name",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "household", "created_at")
    list_select_related = ("user", "household")
    search_fields = ("user__username", "household__name")
