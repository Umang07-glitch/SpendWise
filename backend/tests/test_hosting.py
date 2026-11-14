import pytest
from app.config import Settings


@pytest.mark.parametrize("url", ["postgres://user:pass@host/db", "postgresql://user:pass@host/db"])
def test_managed_postgres_driver(url):
    config = Settings(_env_file=None, database_url=url)
    assert config.database_url == "postgresql+psycopg://user:pass@host/db"


def test_render_origin_and_secure_login(client, monkeypatch):
    from app.config import settings
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://spendwise-test.onrender.com/")
    hosted = Settings(_env_file=None, cookie_secure=True)
    assert hosted.allowed_origins == "https://spendwise-test.onrender.com"
    monkeypatch.setattr(settings, "allowed_origins", hosted.allowed_origins)
    monkeypatch.setattr(settings, "cookie_secure", True)
    client.base_url = "https://spendwise-test.onrender.com"
    response = client.post("/auth/register", headers={"Origin": hosted.allowed_origins},
                           json={"name": "Hosted User", "email": "hosted@example.com", "password": "test-password-123"})
    assert response.status_code == 201
    assert "Secure" in response.headers["set-cookie"]
    assert client.get("/auth/me").status_code == 200
    assert client.post("/transactions", headers={"Origin": "https://evil.example"}, json={}).status_code == 403
