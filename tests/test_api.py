from fastapi.testclient import TestClient

from idea_generator import app as api_module


def test_health_endpoint():
    response = TestClient(api_module.app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_endpoint_passes_category(monkeypatch):
    received = {}

    def fake_generate(context):
        received["context"] = context
        return {
            "title": "QueuePilot",
            "problem": "Small garages lose bookings to phone queues.",
            "category": "car website",
            "target_users": "Independent repair shops",
            "core_features": "Booking, reminders, customer updates",
            "suggested_stack": "Next.js, FastAPI, SQLite",
            "why_now": "Customers expect self-service booking.",
        }

    monkeypatch.setattr(api_module.generator, "generate_idea", fake_generate)
    monkeypatch.setattr(api_module, "provider_configuration_error", lambda: None)
    monkeypatch.setattr(api_module, "save_idea", lambda idea, generation_source="ai": {
        "id": 1, **idea, "is_favorite": False, "created_at": "2026-01-01T00:00:00+00:00", "generation_source": generation_source
    })
    response = TestClient(api_module.app).post("/ideas/generate", json={"category": "car website"})

    assert response.status_code == 200
    assert response.json()["title"] == "QueuePilot"
    assert "car website" in received["context"]


def test_generate_endpoint_uses_fallback_when_provider_is_not_configured(monkeypatch):
    monkeypatch.setattr(api_module, "provider_configuration_error", lambda: "OPENROUTER_API_KEY is not configured in the backend .env file.")
    monkeypatch.setattr(api_module, "generate_fallback_idea", lambda category: {
        "title": "FallbackPilot", "problem": "A problem", "category": category,
        "target_users": "Small teams", "core_features": "Reminders", "suggested_stack": "FastAPI", "why_now": "Useful now"
    })
    monkeypatch.setattr(api_module, "save_idea", lambda idea, generation_source="ai": {
        "id": 1, **idea, "is_favorite": False, "created_at": "2026-01-01T00:00:00+00:00", "generation_source": generation_source
    })

    response = TestClient(api_module.app).post("/ideas/generate", json={})

    assert response.status_code == 200
    assert response.json()["generation_source"] == "fallback"
