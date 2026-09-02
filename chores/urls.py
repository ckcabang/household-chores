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
]
