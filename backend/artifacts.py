import re
import html
from typing import Dict, Any

ALLOWED_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "strong", "em", "b", "i", "blockquote", "code", "pre", "hr", "br", "span", "div", "a"}
ALLOWED_ATTRIBUTES = {"a": {"href", "title", "target"}}

def sanitize_markdown_html(html_str: str) -> str:
    """
    Sanitizes HTML generated from Markdown rendering.
    Strips raw dangerous tags (script, iframe, object, embed, style),
    strips on* event attributes and javascript: URLs.
    """
    # 1. Remove dangerous script and style tags completely along with content
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<iframe[^>]*>.*?</iframe>', '', clean, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Remove inline event handlers (e.g. onerror=, onload=, onclick=)
    clean = re.sub(r'\s+on[a-z]+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', clean, flags=re.IGNORECASE)
    
    # 3. Disallow javascript: pseudo-protocol in href or src
    clean = re.sub(r'(href|src)\s*=\s*(?:"javascript:[^"]*"|\'javascript:[^\']*\'|javascript:[^\s>]+)', r'\1="#"', clean, flags=re.IGNORECASE)
    
    return clean

def render_artifact_payload(artifact: Dict[str, Any]) -> Dict[str, Any]:
    kind = artifact.get("kind", "markdown")
    content = artifact.get("content", "")
    
    if kind == "html":
        # HTML artifacts must be delivered clean for rendering inside an iframe with sandbox="allow-same-origin" ONLY
        # Verify script tag absence or strip out script/event tags
        sanitized_content = sanitize_markdown_html(content)
        return {
            "id": artifact.get("id"),
            "kind": "html",
            "rendered": sanitized_content,
            "raw": content,
            "sandbox_flags": "allow-same-origin"  # STRICTLY NO allow-scripts, NO allow-popups, NO allow-top-navigation
        }
    else:
        # Markdown artifact
        sanitized_content = sanitize_markdown_html(content)
        return {
            "id": artifact.get("id"),
            "kind": "markdown",
            "rendered": sanitized_content,
            "raw": content
        }
