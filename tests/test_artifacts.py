import pytest
from backend.artifacts import sanitize_markdown_html, render_artifact_payload

def test_sanitize_markdown_html_script_removal():
    dirty_html = "<h1>Title</h1><script>alert('xss')</script><p>Safe text</p>"
    clean = sanitize_markdown_html(dirty_html)
    assert "<script>" not in clean
    assert "alert" not in clean
    assert "<h1>Title</h1>" in clean
    assert "<p>Safe text</p>" in clean

def test_sanitize_markdown_html_event_handlers():
    dirty_html = '<img src="x" onerror="alert(1)" onclick="doEvil()"/>'
    clean = sanitize_markdown_html(dirty_html)
    assert "onerror" not in clean
    assert "onclick" not in clean

def test_sanitize_markdown_html_javascript_urls():
    dirty_html = '<a href="javascript:alert(1)">Click me</a>'
    clean = sanitize_markdown_html(dirty_html)
    assert 'href="javascript:' not in clean
    assert 'href="#"' in clean

def test_render_artifact_payload_sandbox_flags():
    artifact = {
        "id": "art-123",
        "kind": "html",
        "content": "<p>Hello</p><script>alert('test')</script>"
    }
    payload = render_artifact_payload(artifact)
    assert payload["sandbox_flags"] == "allow-same-origin"
    assert "<script>" not in payload["rendered"]
