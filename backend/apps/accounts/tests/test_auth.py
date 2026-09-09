import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


def test_register_creates_user(api_client):
    resp = api_client.post(
        "/api/v1/auth/register/",
        {"username": "newcitizen", "email": "a@b.com", "password": "S3cure-Pass!23"},
        format="json",
    )
    assert resp.status_code == 201
    assert User.objects.filter(username="newcitizen").exists()


def test_register_rejects_weak_password(api_client):
    resp = api_client.post(
        "/api/v1/auth/register/",
        {"username": "weakpw", "password": "123"},
        format="json",
    )
    assert resp.status_code == 400


def test_login_returns_access_and_refresh_tokens(api_client):
    User.objects.create_user(username="citizen", password="S3cure-Pass!23")
    resp = api_client.post(
        "/api/v1/auth/login/", {"username": "citizen", "password": "S3cure-Pass!23"}, format="json"
    )
    assert resp.status_code == 200
    assert "access" in resp.data
    assert "refresh" in resp.data


def test_login_rejects_wrong_password(api_client):
    User.objects.create_user(username="citizen", password="S3cure-Pass!23")
    resp = api_client.post("/api/v1/auth/login/", {"username": "citizen", "password": "wrong"}, format="json")
    assert resp.status_code == 401


def test_refresh_token_issues_new_access_token(api_client):
    User.objects.create_user(username="citizen", password="S3cure-Pass!23")
    login = api_client.post(
        "/api/v1/auth/login/", {"username": "citizen", "password": "S3cure-Pass!23"}, format="json"
    )
    resp = api_client.post("/api/v1/auth/refresh/", {"refresh": login.data["refresh"]}, format="json")
    assert resp.status_code == 200
    assert "access" in resp.data
