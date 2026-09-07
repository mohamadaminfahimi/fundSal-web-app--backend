"""Public API URL configuration.

The project URLConf includes this module so every API endpoint has one
central entry point and can be versioned without changing the root config.
"""

from django.urls import include, path

urlpatterns = [
    path("v1/", include("api.v1.urls")),
]
