from app.core.routing import select_model


def test_complex_intents_route_to_strong_model():
    for intent in ("course_complex", "plan_action", "reflection", "practice"):
        route = select_model(intent=intent, source_count=0, message="ngắn")
        assert route.model_env == "OPENAI_STRONG_MODEL"


def test_many_sources_route_to_strong_model():
    route = select_model(intent="course_fact", source_count=3, message="ngắn")
    assert route.model_env == "OPENAI_STRONG_MODEL"


def test_long_message_routes_to_strong_model():
    route = select_model(intent="course_fact", source_count=0, message="a" * 701)
    assert route.model_env == "OPENAI_STRONG_MODEL"


def test_simple_short_request_routes_to_light_model():
    route = select_model(intent="course_fact", source_count=1, message="ngắn")
    assert route.model_env == "OPENAI_LIGHT_MODEL"
