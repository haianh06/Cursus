"""Curated small-talk bank for smalltalk_service.py's semantic bypass.

Each entry lists a few phrasings of the same intent plus one canonical
answer. chat_cache_service._CANNED_ANSWERS already handles the *exact*
strings after normalization (zero cost, no embedding call); this bank exists
for everything else that means the same thing but doesn't match exactly --
"chao ban khoe khong", "dao nay the nao" and so on -- matched by embedding
cosine similarity instead of a literal string.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmallTalkEntry:
    id: str
    variants: tuple[str, ...]
    answer: str


SMALLTALK_ENTRIES: tuple[SmallTalkEntry, ...] = (
    SmallTalkEntry(
        id="greeting",
        variants=(
            "Chào bạn",
            "Chào Cursus",
            "Chào bạn, khỏe không?",
            "Dạo này bạn thế nào?",
            "Alo Cursus ơi",
            "Hi there",
            "Hello, how are you?",
        ),
        answer="Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    ),
    SmallTalkEntry(
        id="thanks",
        variants=(
            "Cảm ơn bạn nhiều nhé",
            "Cảm ơn Cursus",
            "Cảm ơn vì đã giúp mình",
            "Thank you so much",
            "Thanks a lot",
        ),
        answer="Không có gì đâu, còn cần mình giúp gì nữa không?",
    ),
    SmallTalkEntry(
        id="who_are_you",
        variants=(
            "Bạn là ai vậy",
            "Cursus là cái gì",
            "Giới thiệu về bản thân bạn đi",
            "Tell me about yourself",
            "What are you exactly",
        ),
        answer="Mình là Cursus — trợ lý học tập giúp bạn hiểu tài liệu môn học, lập kế hoạch tuần và tự đánh giá.",
    ),
    SmallTalkEntry(
        id="capabilities",
        variants=(
            "Bạn giúp được những gì cho mình",
            "Cursus làm được gì",
            "Mình có thể hỏi bạn những chuyện gì",
            "What can you help me with",
            "What do you do exactly",
        ),
        answer=(
            "Mình giúp được: giải thích nội dung môn học theo tài liệu đã học, "
            "gợi ý cách bắt đầu bài tập (không làm hộ), và điều hướng tới kế "
            "hoạch tuần hoặc phần tự đánh giá."
        ),
    ),
    SmallTalkEntry(
        id="how_are_you",
        variants=(
            "Bạn có khỏe không",
            "Hôm nay bạn thế nào",
            "How are you doing today",
            "How's it going",
        ),
        answer="Mình ổn, cảm ơn bạn đã hỏi thăm! Mình có thể giúp gì cho việc học của bạn hôm nay?",
    ),
)
