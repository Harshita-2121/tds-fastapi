from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_assigned_base_layers_and_secret_masking():
    response = client.get("/effective-config")
    assert response.status_code == 200
    assert response.json() == {
        "port": 8011,
        "workers": 3,
        "debug": True,
        "log_level": "warning",
        "api_key": "****",
    }


def test_cli_overrides_win_and_types_are_coerced():
    response = client.get(
        "/effective-config",
        params=[("set", "port=9000"), ("set", "debug=TrUe"), ("set", "workers=7")],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 9000 and isinstance(data["port"], int)
    assert data["workers"] == 7 and isinstance(data["workers"], int)
    assert data["debug"] is True
    assert data["log_level"] == "warning"
    assert data["api_key"] == "****"


def test_false_bool_and_extra_string_key():
    response = client.get(
        "/effective-config",
        params=[("set", "debug=no"), ("set", "region=ap-south-1")],
    )
    assert response.status_code == 200
    assert response.json()["debug"] is False
    assert response.json()["region"] == "ap-south-1"


def test_api_key_cannot_be_overridden_into_response():
    response = client.get("/effective-config?set=api_key=super-secret")
    assert response.status_code == 200
    assert response.json()["api_key"] == "****"
    assert "super-secret" not in response.text


def test_cors_preflight():
    response = client.options(
        "/effective-config",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
