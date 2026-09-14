import pytest
from backend.artifacts import render_artifact_payload

def test_frontend_sandbox_contract():
    # Verify strict sandbox flags returned for HTML artifacts
    html_artifact = {
        "id": "art-test",
        "kind": "html",
        "content": "<html><body><h1>Test</h1><script>alert('xss')</script></body></html>"
    }
    payload = render_artifact_payload(html_artifact)
    assert payload["sandbox_flags"] == "allow-same-origin"
    assert "allow-scripts" not in payload["sandbox_flags"]
    assert "<script>" not in payload["rendered"]
