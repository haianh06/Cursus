"""Public landing-page chat widget — a pre-login product demo for anonymous
visitors, same pattern as Intercom/Drift's marketing-site chat bubble.
Reachable with zero auth, so this only ever answers from a fixed FAQ list:
no LLM call, no DB read, no student data. Previously this forwarded free-
text questions to an LLM (cost-bearing, reachable by anyone with no auth);
it's now a pure lookup table so the widget can never incur AI spend.
"""
from __future__ import annotations

FALLBACK_ANSWER = {
    "vi": (
        "Mình chỉ trả lời được các câu hỏi có sẵn ở trên. Bấm \"Trải nghiệm Cursus\" "
        "để dùng thử và khám phá thêm nhé!"
    ),
    "en": (
        "I can only answer the preset questions above. Click \"Try Cursus\" to "
        "explore the rest hands-on!"
    ),
}

# Each entry: stable `id` (what the frontend sends back), the question shown
# on the button, and the pre-written answer -- both localized so the widget
# reads naturally in whichever language LanguageContext is currently set to.
FAQ_ITEMS: list[dict[str, dict[str, str]]] = [
    {
        "id": "how-it-works",
        "question": {
            "vi": "Cursus hoạt động thế nào?",
            "en": "How does Cursus work?",
        },
        "answer": {
            "vi": (
                "Cursus theo chu trình Plan-Do-Reflect: biến syllabus môn học thành "
                "kế hoạch theo tuần, gợi ý việc cần làm, rồi mời bạn phản tư sau mỗi "
                "tuần học. Mọi câu trả lời về nội dung môn học đều kèm trích dẫn "
                "nguồn tài liệu, không bịa thông tin."
            ),
            "en": (
                "Cursus follows a Plan-Do-Reflect cycle: it turns your course syllabus "
                "into a week-by-week plan, suggests what to work on, then prompts a "
                "short reflection at the end of each week. Every course-content answer "
                "is grounded with a source citation, never made up."
            ),
        },
    },
    {
        "id": "who-for",
        "question": {
            "vi": "Cursus dùng cho ai?",
            "en": "Who is Cursus for?",
        },
        "answer": {
            "vi": (
                "Cursus dành cho sinh viên đại học muốn có một trợ lý học tập theo "
                "sát tiến độ môn học, và cho giảng viên muốn giám sát tiến độ lớp mà "
                "không phải tự tay nhắc từng sinh viên."
            ),
            "en": (
                "Cursus is for university students who want a study companion that "
                "tracks their course progress, and for instructors who want visibility "
                "into a whole class's progress without manually chasing each student."
            ),
        },
    },
    {
        "id": "no-homework",
        "question": {
            "vi": "Có làm hộ bài tập không?",
            "en": "Does it do my homework for me?",
        },
        "answer": {
            "vi": (
                "Không. Cursus có cơ chế bảo vệ liêm chính học thuật: khi phát hiện "
                "câu hỏi kiểu \"làm hộ bài\", nó sẽ từ chối hoặc chuyển hướng gợi mở "
                "kiểu Socratic (đặt câu hỏi dẫn dắt) thay vì đưa đáp án trực tiếp."
            ),
            "en": (
                "No. Cursus has an academic-integrity guardrail: when a question looks "
                "like \"do my assignment for me\", it either declines or redirects with "
                "Socratic-style guiding questions instead of handing over a direct answer."
            ),
        },
    },
    {
        "id": "citations",
        "question": {
            "vi": "Câu trả lời có trích dẫn nguồn không?",
            "en": "Do answers cite sources?",
        },
        "answer": {
            "vi": (
                "Có. Mỗi câu trả lời về kiến thức môn học đều kèm trích dẫn tới đúng "
                "tài liệu/mục đã dùng để trả lời, để bạn tự kiểm tra lại nếu cần."
            ),
            "en": (
                "Yes. Every course-content answer links back to the exact document and "
                "section it was drawn from, so you can double-check it yourself."
            ),
        },
    },
    {
        "id": "instructor-visibility",
        "question": {
            "vi": "Giảng viên có giám sát được không?",
            "en": "Can instructors monitor progress?",
        },
        "answer": {
            "vi": (
                "Có. Giảng viên thấy được tiến độ kế hoạch, phản tư và các câu hỏi bị "
                "hệ thống chặn của sinh viên trong lớp, để can thiệp kịp lúc khi cần."
            ),
            "en": (
                "Yes. Instructors can see their students' plan progress, reflections, "
                "and any questions the safety guardrail blocked, so they can step in "
                "when it matters."
            ),
        },
    },
    {
        "id": "try-it",
        "question": {
            "vi": "Dùng thử/giá thế nào?",
            "en": "How can I try it / what does it cost?",
        },
        "answer": {
            "vi": (
                "Bấm \"Trải nghiệm Cursus\" để vào thẳng bản demo, không cần đăng ký "
                "hay nhập thẻ thanh toán."
            ),
            "en": (
                "Click \"Try Cursus\" to jump straight into the demo -- no signup or "
                "payment card required."
            ),
        },
    },
]

_BY_ID = {item["id"]: item for item in FAQ_ITEMS}


def answer(question_id: str, lang: str = "vi") -> dict:
    """Pure lookup, no LLM/DB involved. Raises ValueError for an unknown id
    (the frontend only ever sends ids from `FAQ_ITEMS`, so this only fires
    against a stale/tampered client)."""
    question_id = (question_id or "").strip()
    if not question_id:
        raise ValueError("questionId is required")
    lang = "en" if lang == "en" else "vi"

    item = _BY_ID.get(question_id)
    if item is None:
        raise ValueError(f"unknown questionId: {question_id}")
    return {"answer": item["answer"][lang]}


def list_faq(lang: str = "vi") -> list[dict[str, str]]:
    """FAQ items for the widget's button list -- id + localized question text."""
    lang = "en" if lang == "en" else "vi"
    return [{"id": item["id"], "question": item["question"][lang]} for item in FAQ_ITEMS]
