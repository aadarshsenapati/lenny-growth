from app.agent.router import detect_artifact_kind, route


def test_route_defaults_to_grounded_qa():
    assert route("What did Lenny's guests say about PLG pricing?") == "grounded_qa"


def test_route_detects_ship30_essay_request():
    assert route("Turn this into a Ship 30 for 30 essay") == "ship30"
    assert route("Can you write an atomic essay about onboarding?") == "ship30"


def test_route_detects_artifact_request():
    assert route("Generate a markdown document summarizing this") == "artifact"
    assert route("Render this as an HTML snippet") == "artifact"


def test_detect_artifact_kind_defaults_to_markdown():
    assert detect_artifact_kind("generate a doc") == "markdown"
    assert detect_artifact_kind("give me an html page") == "html"
