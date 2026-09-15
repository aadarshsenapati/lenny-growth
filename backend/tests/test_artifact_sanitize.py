from app.agent.skills.artifact_skill import sanitize_html


def test_sanitize_strips_script_tags():
    raw = '<div>Hello<script>alert("xss")</script></div>'
    cleaned = sanitize_html(raw)
    assert "<script" not in cleaned.lower()
    assert "Hello" in cleaned


def test_sanitize_strips_inline_event_handlers():
    raw = '<button onclick="alert(1)">Click</button>'
    cleaned = sanitize_html(raw)
    assert "onclick" not in cleaned.lower()


def test_sanitize_neutralizes_javascript_urls():
    raw = '<a href="javascript:alert(1)">link</a>'
    cleaned = sanitize_html(raw)
    assert "javascript:" not in cleaned.lower()


def test_sanitize_blocks_external_resources():
    raw = '<img src="https://evil.example.com/track.png">'
    cleaned = sanitize_html(raw)
    assert "https://evil.example.com" not in cleaned
