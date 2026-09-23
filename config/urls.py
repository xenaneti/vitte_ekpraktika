from django.urls import include, path

urlpatterns = [path("", include("baths.urls"))]
handler404 = "baths.views.not_found"
handler403 = "baths.views.forbidden"
