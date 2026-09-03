from django.contrib import admin

from .models import (
    AISetupDraft,
    Chore,
    ChoreOccurrence,
    Completion,
    Constraint,
    ContributionCredit,
    EstimateProposal,
    FairnessWeights,
    Household,
    Invitation,
    Membership,
    WeightProposal,
)


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "member_count", "created_at")
    search_fields = ("name",)


@admin.register(FairnessWeights)
class FairnessWeightsAdmin(admin.ModelAdmin):
    list_display = (
        "household",
        "time_weight",
        "difficulty_weight",
        "decay_half_life_days",
        "updated_at",
    )
    list_select_related = ("household",)
    search_fields = ("household__name",)


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


@admin.register(ChoreOccurrence)
class ChoreOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("chore", "due_date", "status", "completed_at", "claimed_by")
    list_filter = ("status", "chore__household")
    list_select_related = ("chore", "chore__household", "claimed_by__user")
    search_fields = ("chore__name", "chore__household__name")


@admin.register(Completion)
class CompletionAdmin(admin.ModelAdmin):
    list_display = (
        "occurrence",
        "completed_by",
        "actual_minutes",
        "actual_effort",
        "created_at",
    )
    list_select_related = ("occurrence", "completed_by__user")
    list_filter = ("completed_by__household",)
    search_fields = ("occurrence__chore__name", "completed_by__user__username")


@admin.register(ContributionCredit)
class ContributionCreditAdmin(admin.ModelAdmin):
    list_display = ("completion", "helper", "owner", "workload_value", "created_at")
    list_select_related = (
        "completion__occurrence__chore",
        "helper__user",
        "owner__user",
    )
    list_filter = ("helper__household",)
    search_fields = (
        "completion__occurrence__chore__name",
        "helper__user__username",
        "owner__user__username",
    )


@admin.register(EstimateProposal)
class EstimateProposalAdmin(admin.ModelAdmin):
    list_display = (
        "chore",
        "proposed_minutes",
        "proposed_difficulty",
        "status",
        "created_at",
        "decided_at",
        "decided_by",
    )
    list_filter = ("status", "chore__household")
    list_select_related = ("chore", "decided_by__user")
    search_fields = ("chore__name", "rationale")
    date_hierarchy = "created_at"


@admin.register(WeightProposal)
class WeightProposalAdmin(admin.ModelAdmin):
    list_display = (
        "household",
        "time_weight",
        "difficulty_weight",
        "decay_half_life_days",
        "status",
        "created_by",
        "created_at",
        "resolved_at",
    )
    list_filter = ("status", "household")
    list_select_related = ("household", "created_by__user")
    filter_horizontal = ("approved_by",)
    search_fields = ("household__name",)
    date_hierarchy = "created_at"


@admin.register(AISetupDraft)
class AISetupDraftAdmin(admin.ModelAdmin):
    list_display = ("household", "status", "created_at", "applied_at")
    list_filter = ("status", "household")
    list_select_related = ("household",)
    search_fields = ("household__name", "reasoning")
    date_hierarchy = "created_at"


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
