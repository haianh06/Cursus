# Weekly Journal — Team093 (Group06) — Cursus

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp. **Cách điền:** viết vào cuối mỗi tuần (không phải cuối kỳ) — dùng `WORKLOG.md` tuần đó + `docs/decisions/ADR.md` làm nguồn, không cần nhớ lại từ đầu.

---

## Week 1: 01/08/2026 - 09/08/2026 (chuẩn bị + ngày 1 Gate 2, dựng lại từ git log + docs ngày 10/08/2026)

### Mục tiêu tuần này
- [x] Dựng bộ docs định hình sản phẩm (PRD/SRS/Execution Plan) thay cho bản v1 lỗi thời
- [x] Có auth flow + RBAC chạy được (nền tảng cho F1)
- [x] Kết nối được Google Gemini vào backend
- [ ] Chốt xong 1 stack frontend duy nhất (từng có 2 nhánh Next.js/Vite song song — đã gộp về Vite ngày 08/08, nhưng docs `00-Playbook.md` vẫn còn nhắc `types.ts`/`demo-service.ts` kiểu Next.js — **cần đối chiếu lại**)

### Đã hoàn thành
- Bộ docs `docs/planning/v2` (00-07) đầy đủ FR/NFR, traceability PLO, kiến trúc LangGraph, kịch bản demo chính + lỗi
- Auth (login/register/reset password/email verification) + JWT + RBAC middleware + session model (haianh06)
- Tích hợp Google Gemini vào env/backend, QA service có normalization + intent handling (haianh06)
- Gộp code về 1 stack Vite duy nhất, drop phần Next.js còn sót (haianh06, 08/08)
- Admin Console (F6 bảng curriculum, F7 KPI) dựng sớm hơn kế hoạch — theo `01-PRD.md` mục 8.1 các mục này thuộc Mốc 3, không phải Gate 2 Must (NguyenThanhBinh108, 09/08)
- Sửa 1 lỗi đáng chú ý: biểu đồ GV từng "bịa" sĩ số — đã fix, đúng nguyên tắc "không bịa số liệu" của sản phẩm (09/08)

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Có 2 nhánh frontend chạy song song (Next.js cũ + Vite mới), docs vẫn mô tả theo bản Next.js | Gộp về 1 stack Vite (commit `7aa2017`, 08/08) | Cần việc tiếp theo: đối chiếu lại `00-Cursus-Playbook.md` PHẦN 6 cho khớp code Vite thật, tránh Người C làm theo hướng dẫn sai stack |
| Model Gemini/embedding dùng trong docs (`gemini-1.5-*`, `text-embedding-004`) đã ngừng hoạt động thật (phát hiện 10/08) | Đổi sang `gemini-2.5-flash-lite`/`gemini-2.5-flash`/`gemini-embedding-001`, thêm ADR-006 nhắc re-verify định kỳ | Docs khớp lại với API thật — cần Người B xác nhận code backend cũng dùng đúng tên model mới, không chỉ sửa ở docs |
| "Hôm nay" trong `03-Execution-Plan.md` bị lệch 1 ngày so với ngày thật | Cập nhật lại mốc ngày (10/08/2026) | Lịch trình đọc đúng lại, chưa kiểm tra tiến độ thật so với mốc |

### Bài học
- Docs viết trước, code chạy sau dễ lệch nhau ở chi tiết kỹ thuật cụ thể (tên model, stack frontend) nếu không có bước đối chiếu định kỳ — nên thêm việc "đối chiếu docs vs code thật" vào cuối mỗi tuần, không chỉ đối chiếu docs với nhau.
- Team đã chủ động làm sớm hơn kế hoạch ở 1 số phần (Admin Console) — tốt cho tiến độ nhưng cần xác nhận không phải đang lệch khỏi ưu tiên Gate 2 Must (`03-Execution-Plan.md`) vì cắt giờ nhầm chỗ.

### Kế hoạch tuần sau
- [ ] Đối chiếu `00-Cursus-Playbook.md`/`03-Execution-Plan.md` với code Vite thật, sửa phần mô tả sai stack nếu có
- [ ] Xác nhận Người B đã đổi tên model Gemini trong code khớp với docs vừa cập nhật (10/08)
- [ ] Tiếp tục theo đúng lịch `03-Execution-Plan.md` ngày 10-14/08 (F2 Plan, F3 Q&A+Guardrail, Reflect, deploy)

---

## Week 2: 10/08/2026 - 16/08/2026

> **[Khung 22/08, chưa điền nội dung]** Tuần này có audit UI/UX toàn diện, hợp nhất backend/frontend từ nhánh `develop`, dựng lại risk-policy/guardrail nâng cao, xoá `docs/FRONTEND_SPEC.md` có chủ đích — tự điền chi tiết thật đã làm gì, không suy đoán hộ.

### Mục tiêu tuần này
- [ ] [Mục tiêu 1]

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

## Week 3: 17/08/2026 - 23/08/2026 (tuần nộp bài)

> **[Khung 22/08, chưa điền nội dung]** Tuần chốt trước deadline 23/08 — sprint P0 an ninh/eval (RBAC/IDOR sweep, LLM07/LLM08, trace wiring, Mock LMS, data deletion, risk policy versioning). Xem `docs/PROJECT_CONTEXT.md` mục "TRẠNG THÁI HIỆN TẠI" và `docs/archive/SESSION_REPORT_20260822.md` để nhớ lại chi tiết trước khi viết.

### Mục tiêu tuần này
- [ ] [Mục tiêu 1]

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

<!-- Tiếp tục copy block trên cho các tuần sau, nếu có -->
