from django.shortcuts import render


def index(request):
    """
    Home page view for the Game Master Application.
    
    Shows the main landing page with features and getting started information.
    """
    return render(request, 'core/index.html')