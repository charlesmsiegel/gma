from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    """
    Home page view for the Game Master Application.

    Shows the main landing page with features and getting started information.
    """
    return render(request, "core/index.html")
