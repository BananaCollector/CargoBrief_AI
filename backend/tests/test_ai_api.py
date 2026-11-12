import json
from types import SimpleNamespace

import httpx

from app.api import ai as ai_api
from app.schemas import AIAnalyzedOrder, AIAnalyzeResponse
from app.services import ai_analyzer
from app.services.ai_analyzer import DEMO_SAMPLE_MESSAGE


def test_analyze_endpoint_returns_explicit_demo_result(client, monkeypatch) -> None:
    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", None)
    response = client.post(
        "/api/v1/ai/analyze",
        json={"message": DEMO_SAMPLE_MESSAGE},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["order"]["cargo_description"] == "Kanapa"
    assert payload["order"]["length_cm"] == 220
    assert payload["order"]["pickup_location"] == "Warszawa"
    assert payload["order"]["delivery_location"] == "Kraków"
    assert payload["order"]["preferred_date"] is None
    assert "preferred_date" in payload["missing_fields"]
    assert payload["ambiguities"] == []


def test_analyze_endpoint_rejects_empty_message(client) -> None:
    response = client.post("/api/v1/ai/analyze", json={"message": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_analyze_endpoint_enforces_message_length_limit(client) -> None:
    response = client.post(
        "/api/v1/ai/analyze",
        json={"message": "x" * 3001},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_analyze_endpoint_accepts_message_at_length_limit(client, monkeypatch) -> None:
    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", None)
    response = client.post(
        "/api/v1/ai/analyze",
        json={"message": "x" * 3000},
    )

    assert response.status_code == 200
    assert len(response.json()["order"]["original_message"]) == 3000


def test_analyze_endpoint_uses_gemini_and_validates_the_result(client, monkeypatch) -> None:
    message = "Proszę przewieźć kanapę z Gdańska do Gdyni."
    raw_result = {
        "order": {
            "cargo_description": "Kanapa",
            "quantity": 1,
            "pickup_location": "Gdańsk",
            "delivery_location": "Gdynia",
        },
        "ambiguities": ["Nie podano wymiarów ładunku."],
    }
    recorded: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs):
            recorded.update(kwargs)
            return SimpleNamespace(output_text=json.dumps(raw_result))

    class FakeClient:
        interactions = FakeInteractions()

        def __init__(self, **kwargs):
            recorded["client_options"] = kwargs

        def close(self):
            recorded["closed"] = True

    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", "test-secret")
    monkeypatch.setattr(ai_analyzer.settings, "gemini_model", "test-model")
    monkeypatch.setattr(ai_analyzer.genai, "Client", FakeClient)
    monkeypatch.setattr(ai_api, "_rate_limit_state", {})

    response = client.post("/api/v1/ai/analyze", json={"message": message})

    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "ai"
    assert result["order"]["original_message"] == message
    assert result["order"]["pickup_location"] == "Gdańsk"
    assert "length_cm" in result["missing_fields"]
    assert result["ambiguities"] == raw_result["ambiguities"]
    assert recorded["model"] == "test-model"
    assert recorded["input"] == message
    assert "niezaufanym" in recorded["system_instruction"].lower()
    assert recorded["response_format"]["mime_type"] == "application/json"
    assert recorded["closed"] is True


def test_gemini_timeout_returns_safe_error(client, monkeypatch) -> None:
    class FakeInteractions:
        def create(self, **_kwargs):
            assert _kwargs["input"] == "Test"
            raise httpx.TimeoutException("test-secret")

    class FakeClient:
        interactions = FakeInteractions()

        def __init__(self, **_kwargs):
            assert _kwargs["api_key"] == "test-secret"

        def close(self):
            pass

    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", "test-secret")
    monkeypatch.setattr(ai_analyzer.genai, "Client", FakeClient)
    monkeypatch.setattr(ai_api, "_rate_limit_state", {})

    response = client.post("/api/v1/ai/analyze", json={"message": "Test"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_timeout"
    assert "test-secret" not in response.text


def test_invalid_gemini_output_returns_safe_error(client, monkeypatch) -> None:
    class FakeInteractions:
        def create(self, **_kwargs):
            assert _kwargs["input"] == "Test"
            return SimpleNamespace(output_text='{"unexpected": "invalid"}')

    class FakeClient:
        interactions = FakeInteractions()

        def __init__(self, **_kwargs):
            assert _kwargs["api_key"] == "test-secret"

        def close(self):
            pass

    monkeypatch.setattr(ai_analyzer.settings, "gemini_api_key", "test-secret")
    monkeypatch.setattr(ai_analyzer.genai, "Client", FakeClient)
    monkeypatch.setattr(ai_api, "_rate_limit_state", {})

    response = client.post("/api/v1/ai/analyze", json={"message": "Test"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_invalid_response"
    assert "test-secret" not in response.text


def test_gemini_requests_are_rate_limited_per_client(client, monkeypatch) -> None:
    demo_response = AIAnalyzeResponse(
        order=AIAnalyzedOrder(original_message="Test"),
        missing_fields=[],
        ambiguities=[],
        mode="ai",
    )

    def fake_analyze(message: str) -> AIAnalyzeResponse:
        assert message == "Test"
        return demo_response

    monkeypatch.setattr(ai_api.settings, "gemini_api_key", "test-secret")
    monkeypatch.setattr(ai_api, "analyze_message", fake_analyze)
    monkeypatch.setattr(ai_api, "_rate_limit_state", {})

    responses = [
        client.post("/api/v1/ai/analyze", json={"message": "Test"})
        for _ in range(ai_api._RATE_LIMIT_MAX_REQUESTS + 1)
    ]

    assert all(
        response.status_code == 200
        for response in responses[: ai_api._RATE_LIMIT_MAX_REQUESTS]
    )
    assert responses[-1].status_code == 429
    assert responses[-1].json()["error"]["code"] == "ai_rate_limited"
