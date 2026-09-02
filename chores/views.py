from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Placeholder landing page that exercises the base layout."""

    template_name = "chores/home.html"
