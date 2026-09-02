from django.urls import path

from . import views

app_name = "chores"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("household/new/", views.HouseholdCreateView.as_view(), name="household_create"),
]
