from django.urls import reverse
from rest_framework.test import APIClient


class TestHealthAndSecurity:
    def test_health_endpoint_is_public(self):
        client = APIClient()
        response = client.get(reverse("health-check"))
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_auth_endpoints_are_exposed(self):
        client = APIClient()
        assert client.get("/api/v1/auth/login/").status_code in (200, 400, 405)
