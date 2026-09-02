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
    path("chores/", views.ChoreListView.as_view(), name="chore_list"),
    path("chores/new/", views.ChoreCreateView.as_view(), name="chore_create"),
    path("chores/<int:pk>/edit/", views.ChoreUpdateView.as_view(), name="chore_edit"),
    path(
        "chores/<int:pk>/delete/",
        views.ChoreDeleteView.as_view(),
        name="chore_delete",
    ),
]
