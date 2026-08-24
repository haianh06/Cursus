/**
 * Dữ liệu mẫu cho hàng đợi xem xét Guardrail (docs/08 mục 4.4, Khối 3).
 *
 * VÌ SAO CÓ FILE NÀY: backend chưa có endpoint nào cho hàng đợi này.
 * `src/main.py` include 8 router và không router nào expose bảng
 * `guardrail_events` (khai báo ở src/db/models.py). Trước đây UI giấu chuyện
 * đó bằng một mảng hardcode ngay trong component, không nhãn không cảnh báo —
 * nhìn y như dữ liệu thật.
 *
 * File này giữ nguyên tính chất "dữ liệu mẫu" nhưng bắt UI phải gắn nhãn:
 * mọi hàm đọc nó đều trả kèm `is_fallback: true` (cùng quy ước đã dùng cho
 * F6/F7 Admin trong curriculumFallback.js).
 *
 * HỢP ĐỒNG ĐỀ XUẤT GỬI NGƯỜI A — mong muốn `GET /instructor/guardrail-reviews`
 * trả về mảng các phần tử:
 *
 *   {
 *     "id": "gre_...",              // id bản ghi guardrail_events
 *     "studentAlias": "...",        // users.full_name
 *     "question": "...",            // messages.content — câu hỏi gốc bị chặn
 *     "blockedAnswer": "...",       // câu trả lời guardrail đã trả cho SV
 *     "blockReason": "academic_integrity",  // GuardrailDecision.reason
 *     "classification": "BLOCKED",  // guardrail_events.classification
 *     "reviewStatus": "PENDING",    // PENDING | KEPT_BLOCKED | UNBLOCKED
 *     "createdAt": "2026-08-11T09:12:00Z"
 *   }
 *
 * và `POST /instructor/guardrail-reviews/{id}` nhận `{ "decision": "KEEP" | "UNBLOCK" }`.
 *
 * Lưu ý cho Người A: bảng `guardrail_events` hiện KHÔNG có cột trạng thái
 * xem xét — cần thêm cột (ví dụ `review_status`) thì hàng đợi mới có trạng
 * thái để lưu, nếu không mọi quyết định của GV sẽ mất sau khi tải lại trang.
 *
 * Các giá trị dưới đây bám sát guardrail thật (src/services/guardrail_service.py):
 * `blockReason` dùng đúng chuỗi "academic_integrity", `blockedAnswer` dùng
 * đúng câu trả lời chặn mà service trả về.
 */

const BLOCK_ANSWER_VI =
  'Mình không làm bài hộ được, nhưng mình có thể gợi ý hướng tiếp cận — '
  + 'bạn thử bắt đầu từ phần liên quan trong tài liệu môn xem sao.';

export const GUARDRAIL_FALLBACK = {
  reviews: [
    {
      id: 'demo-gre-1',
      studentAlias: 'Nguyễn Gia An',
      question: 'Thầy ơi em không hiểu đề lab 3 SSA101, viết hộ em phần main với ạ',
      blockedAnswer: BLOCK_ANSWER_VI,
      blockReason: 'academic_integrity',
      classification: 'BLOCKED',
      reviewStatus: 'PENDING',
      createdAt: null,
    },
    {
      id: 'demo-gre-2',
      studentAlias: 'Trần Bảo Khánh',
      question: 'Cho em xin complete code của bài tập tuần 4 để em đối chiếu',
      blockedAnswer: BLOCK_ANSWER_VI,
      blockReason: 'academic_integrity',
      classification: 'BLOCKED',
      reviewStatus: 'PENDING',
      createdAt: null,
    },
    {
      // Case chặn nhầm có thật về mặt kỹ thuật: câu này hỏi về quy định, nhưng
      // chứa cụm "viết hộ" nên khớp _BLOCK_PATTERNS và bị chặn. Đây đúng là
      // loại case hàng đợi này sinh ra để giải quyết.
      id: 'demo-gre-3',
      studentAlias: 'Lê Minh Thư',
      question: 'Em viết hộ bạn phần báo cáo nhóm thì có bị tính là đạo văn không ạ?',
      blockedAnswer: BLOCK_ANSWER_VI,
      blockReason: 'academic_integrity',
      classification: 'BLOCKED',
      reviewStatus: 'PENDING',
      createdAt: null,
    },
  ],
};
