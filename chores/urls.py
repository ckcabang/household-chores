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
