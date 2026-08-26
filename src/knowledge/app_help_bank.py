"""Curated help entries for "how do I use Cursus" questions — distinct from
`faq_bank.py`, which answers COURSE-CONTENT questions (syllabus concepts).
These answer APP-USAGE questions (how a feature works, where to find it).

Same role in the pipeline as `faq_bank.py`: never returned to the student
verbatim as a final answer. `AppHelpService.match()` finds candidate entries,
and the chat orchestrator hands them to the LLM as grounding context — the
LLM still writes the final answer, in the student's own phrasing and mixed
with whatever academic/state context is also relevant to the question.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpEntry:
    id: str
    route: str  # frontend route this feature lives on, for a "đi tới" pointer
    keywords: tuple[str, ...]
    summary: str
    min_hits: int = 1


HELP_ENTRIES: tuple[HelpEntry, ...] = (
    HelpEntry(
        id="home_dashboard",
        route="/student",
        keywords=(
            "trang chu", "dashboard", "man hinh chinh", "tong quan",
            "home page", "overview",
        ),
        summary=(
            "Trang chủ (Dashboard) tóm tắt: tuần học hiện tại, kế hoạch tuần này (nếu có) "
            "và loại kế hoạch đang dùng, bài tập sắp tới, tiến độ hoàn thành task, khối lượng "
            "giờ học đã lên kế hoạch so với giờ rảnh, và mức cảnh báo rủi ro hiện tại."
        ),
    ),
    HelpEntry(
        id="planner",
        route="/student/planner",
        keywords=("planner", "ke hoach tuan", "len ke hoach", "weekly plan", "lap ke hoach hoc tap"),
        summary=(
            "Planner tạo kế hoạch học tập cho 1 tuần: chia nhỏ deadline bài tập hoặc mục tiêu "
            "tự đặt thành các task theo ngày, ước lượng thời lượng từng task. Kế hoạch chỉ có "
            "hiệu lực sau khi sinh viên xem lại và bấm xác nhận — chưa xác nhận vẫn là bản nháp. "
            "Cursus có 3 nguồn tạo kế hoạch (theo bài tập/theo mục tiêu tự đặt/theo lịch học trên lớp); "
            "hệ thống tự chọn 1 kế hoạch đại diện cho mỗi tuần và hiển thị rõ đó là loại nào."
        ),
    ),
    HelpEntry(
        id="reflection",
        route="/student/reflection",
        keywords=(
            "phan tu", "reflection", "danh gia tuan", "viet phan tu",
            "yeu cau ho tro", "request help",
        ),
        summary=(
            "Phản tư (Reflection) là nơi sinh viên tự đánh giá cuối tuần: mức độ hoàn thành kế "
            "hoạch, khó khăn gặp phải, mức độ căng thẳng, và có thể chọn các điều chỉnh cho tuần "
            "sau (ví dụ giảm tải, hoặc chọn 'Yêu cầu hỗ trợ' để giảng viên chủ động liên hệ). "
            "Nội dung Phản tư mặc định KHÔNG hiển thị cho giảng viên trừ khi sinh viên tự bật "
            "chia sẻ trong Cài đặt riêng tư."
        ),
    ),
    HelpEntry(
        id="practice",
        route="/student/practice",
        keywords=("practice", "luyen tap", "flashcard", "on tap", "cau hoi luyen tap"),
        summary=(
            "Luyện tập (Practice) cung cấp flashcard/câu hỏi ôn tập theo môn học, được tạo tự "
            "động rồi giảng viên duyệt trước khi công khai cho sinh viên."
        ),
    ),
    HelpEntry(
        id="semester_setup",
        route="/student/semester-setup",
        keywords=(
            "semester setup", "thiet lap hoc ky", "chon lich hoc", "khai bao lich hoc",
            "thoi khoa bieu dau ky",
        ),
        summary=(
            "Thiết lập học kỳ (Semester Setup) là bước đầu kỳ để sinh viên khai báo lịch học "
            "trên lớp và khoảng thời gian rảnh trong tuần — dữ liệu này là nền để Planner và "
            "Timetable tính giờ học khả dụng và xếp lịch tự học không trùng giờ học."
        ),
    ),
    HelpEntry(
        id="lecture_plan",
        route="/student/lecture-plan",
        keywords=("lecture plan", "ke hoach theo lich hoc", "on bai theo buoi hoc"),
        summary=(
            "Kế hoạch theo lịch học (Lecture Plan) tạo task ôn tập/chuẩn bị bài theo từng buổi "
            "học trên lớp thay vì theo deadline bài tập — dùng khi sinh viên muốn bám sát tiến "
            "độ giảng dạy hơn là chỉ chạy theo deadline."
        ),
    ),
    HelpEntry(
        id="quizzes",
        route="/student/quizzes",
        keywords=("quiz", "bai kiem tra", "lam bai trac nghiem", "nop bai quiz"),
        summary=(
            "Quizzes hiển thị các bài kiểm tra trắc nghiệm/tự luận ngắn do giảng viên tạo cho "
            "môn học, có thời gian làm bài giới hạn; sau khi nộp có thể xem điểm và nhận xét."
        ),
    ),
    HelpEntry(
        id="today_plan",
        route="/student/today",
        keywords=("hom nay", "today", "viec can lam hom nay", "lich hom nay"),
        summary=(
            "Màn hình 'Hôm nay' rút gọn kế hoạch tuần xuống chỉ các task/lịch của riêng ngày "
            "hôm nay, để sinh viên không cần lướt cả kế hoạch tuần mỗi lần mở app."
        ),
    ),
    HelpEntry(
        id="self_study_session",
        route="/student/self-study/:blockId",
        keywords=(
            "tu hoc", "pomodoro", "phien tap trung", "self study", "bam gio hoc",
        ),
        summary=(
            "Phiên tự học (Self-Study/Pomodoro) là màn hình tập trung cho 1 khối thời gian tự "
            "học cụ thể trong lịch tuần — có bấm giờ kiểu Pomodoro, đánh dấu hoàn thành task, "
            "ghi số phút thực tế đã học so với dự kiến."
        ),
    ),
    HelpEntry(
        id="settings_privacy",
        route="/student/settings",
        keywords=(
            "cai dat", "settings", "rieng tu", "privacy", "chia se phan tu",
            "xoa du lieu", "quyen rieng tu",
        ),
        summary=(
            "Cài đặt (Settings) gồm thông tin tài khoản và Cài đặt riêng tư — nơi sinh viên tự "
            "bật/tắt việc chia sẻ tóm tắt Phản tư cho giảng viên xem (mặc định TẮT), và có thể "
            "yêu cầu xoá dữ liệu cá nhân khỏi hệ thống."
        ),
    ),
    HelpEntry(
        id="risk_warning",
        route="/student",
        keywords=(
            "canh bao rui ro", "risk warning", "tai sao bi canh bao", "rui ro hoc tap",
            "vi sao co canh bao",
        ),
        summary=(
            "Cảnh báo rủi ro xuất hiện khi hệ thống phát hiện dấu hiệu sinh viên có thể tụt lại: "
            "trễ nhiều deadline liên tiếp, tỉ lệ hoàn thành task thấp/giảm liên tục nhiều tuần, "
            "sắp đến hạn nộp mà chưa bắt đầu, không hoạt động nhiều ngày, hoặc tự báo mức căng "
            "thẳng rất cao trong Phản tư. Đây là cảnh báo dựa trên số liệu thật, không phải suy "
            "đoán — giảng viên có thể thấy cảnh báo này để chủ động hỗ trợ."
        ),
    ),
    HelpEntry(
        id="chat_assistant",
        route="/student/companion",
        keywords=(
            "tro ly", "chatbot", "hoi tro ly", "assistant lam duoc gi", "cach dung tro ly",
        ),
        summary=(
            "Trợ lý Cursus có thể trả lời câu hỏi về nội dung môn học (có trích dẫn nguồn), câu "
            "hỏi về tình trạng học tập hiện tại của chính sinh viên (kế hoạch, rủi ro, phản tư, "
            "lịch tuần), và câu hỏi về cách dùng các tính năng của app này. Trợ lý không làm hộ "
            "bài tập được tính điểm, nhưng gợi ý hướng làm và đặt câu hỏi Socratic để sinh viên "
            "tự nghĩ tiếp."
        ),
    ),
)
