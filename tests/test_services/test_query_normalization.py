from src.services.ai.conversation_intent_service import ConversationIntentService
from src.services.rag.query_normalization import normalize_query, strip_formatting


def test_strip_backticks_and_markdown():
    assert strip_formatting("`Xin chào`") == "Xin chào"
    assert strip_formatting("**hello**") == "hello"
    assert strip_formatting('  "Hi"  ') == "Hi"


def test_normalize_typos_and_accents():
    result = normalize_query("`xin chao`")
    assert result.folded == "xin chao"
    assert "chào" in result.cleaned or result.cleaned == "xin chào"


def test_conversation_intent_handles_noisy_greeting():
    service = ConversationIntentService()
    intent = service.resolve("`Xin chào`", subject_code="SSA101")
    assert intent.is_chat is True
    assert intent.answer
    assert "SSA101" in intent.answer
