from django.urls import path

from . import views

app_name = "chores"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("household/new/", views.HouseholdCreateView.as_view(), name="household_create"),
    path("household/invite/", views.InviteView.as_view(), name="invite"),
    path(
        "household/join/<str:token>/",
        views.InviteAcceptView.as_view(),
        name="invite_accept",
    ),
    path(
        "household/fairness/",
        views.FairnessWeightsUpdateView.as_view(),
        name="fairness_edit",
    ),
    path(
        "household/rebalance/",
        views.RebalanceView.as_view(),
        name="rebalance",
    ),
    path("chores/", views.ChoreListView.as_view(), name="chore_list"),
    path("chores/new/", views.ChoreCreateView.as_view(), name="chore_create"),
    path("chores/<int:pk>/edit/", views.ChoreUpdateView.as_view(), name="chore_edit"),
    path(
        "chores/<int:pk>/delete/",
        views.ChoreDeleteView.as_view(),
        name="chore_delete",
    ),
    path(
        "chores/<int:chore_pk>/constraints/add/",
        views.ConstraintCreateView.as_view(),
        name="constraint_add",
    ),
    path(
        "chores/<int:chore_pk>/constraints/<int:pk>/delete/",
        views.ConstraintDeleteView.as_view(),
        name="constraint_delete",
    ),
    path(
        "proposals/estimates/",
        views.EstimateProposalListView.as_view(),
        name="estimate_proposal_list",
    ),
    path(
        "proposals/estimates/refresh/",
        views.EstimateProposalRefreshView.as_view(),
        name="estimate_proposal_refresh",
    ),
    path(
        "proposals/estimates/<int:pk>/accept/",
        views.EstimateProposalAcceptView.as_view(),
        name="estimate_proposal_accept",
    ),
    path(
        "proposals/estimates/<int:pk>/dismiss/",
        views.EstimateProposalDismissView.as_view(),
        name="estimate_proposal_dismiss",
    ),
    path(
        "occurrences/",
        views.OccurrenceListView.as_view(),
        name="occurrence_list",
    ),
    path(
        "occurrences/<int:pk>/complete/",
        views.OccurrenceCompleteView.as_view(),
        name="occurrence_complete",
    ),
    path(
        "occurrences/<int:pk>/claim/",
        views.OccurrenceClaimView.as_view(),
        name="occurrence_claim",
    ),
]
