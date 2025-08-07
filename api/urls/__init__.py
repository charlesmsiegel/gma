from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("auth/", include("api.urls.auth_urls")),
    path("profile/", include("api.urls.profile_urls")),
]
