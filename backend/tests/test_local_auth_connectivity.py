from app.core.config import Settings


def test_development_cors_allows_local_next_ports():
    settings = Settings(
        environment="development",
        cors_origins="https://app.synzept.com",
        frontend_url="http://localhost:3001",
    )

    assert "http://localhost:3000" in settings.cors_origin_list
    assert "http://localhost:3001" in settings.cors_origin_list
    assert "http://127.0.0.1:3001" in settings.cors_origin_list
    assert "https://app.synzept.com" in settings.cors_origin_list
