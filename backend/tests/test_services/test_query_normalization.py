from src.services.rag.query_normalization import (
    looks_like_accent_stripped_vietnamese,
    normalize_query,
    strip_formatting,
)


def test_strip_backticks_and_markdown():
    assert strip_formatting("`Xin chào`") == "Xin chào"
    assert strip_formatting("**hello**") == "hello"
    assert strip_formatting('  "Hi"  ') == "Hi"


def test_normalize_typos_and_accents():
    result = normalize_query("`xin chao`")
    assert result.folded == "xin chao"
    assert "chào" in result.cleaned or result.cleaned == "xin chào"


# --- Vietnamese-diacritics-loss detector (a weaker fallback LLM occasionally
# drops every dấu under structured-JSON output — reported live via a
# screenshot where a companion reply / weekly-plan task title came back
# fully accent-stripped). ---


def test_accent_stripped_vietnamese_is_detected():
    broken = (
        "Chao ban, minh rat vui duoc dong hanh cung ban truoc ky thi sap toi. "
        "Voi tu cach la tro giang hoc tap, minh khong the lam bai kiem tra thay ban, "
        "nhung minh hoan toan co the giup ban on tap."
    )
    assert looks_like_accent_stripped_vietnamese(broken) is True


def test_properly_accented_vietnamese_is_not_flagged():
    proper = (
        "Chào bạn, mình rất vui được đồng hành cùng bạn trước kỳ thi sắp tới. "
        "Với tư cách là trợ giảng học tập, mình không thể làm bài kiểm tra thay bạn."
    )
    assert looks_like_accent_stripped_vietnamese(proper) is False


def test_english_answer_is_not_falsely_flagged():
    english = (
        "Bubble sort is a simple sorting algorithm that repeatedly steps "
        "through the list, compares adjacent elements, and swaps them."
    )
    assert looks_like_accent_stripped_vietnamese(english) is False


def test_short_or_empty_answer_is_not_flagged():
    assert looks_like_accent_stripped_vietnamese("") is False
    assert looks_like_accent_stripped_vietnamese("code") is False
