# Cursus — Đánh giá Production Readiness cho bộ docs 01-05

> Không gõ lại nguyên văn 5 file cũ (lãng phí thời gian lúc này) — file này liệt kê **chính xác còn thiếu gì** để 5 file đó (PRD, SRS, Execution Plan, Terminology, Competitive Analysis) đạt chuẩn "production" thật, không chỉ chuẩn "đồ án". Dùng làm checklist cho Mốc 3 (23/08 — nộp bài cuối, 9 ngày sau Gate 2), không phải việc của Gate 2.

---

## 1. Đánh giá từng file

| File | Đã ổn | Còn thiếu để "production" thật |
|---|---|---|
| `01-Cursus-PRD.md` | Scope, persona, MoSCoW theo mốc, risk register có cả rủi ro cạnh tranh | Chưa có: chính sách xoá dữ liệu (data retention/deletion), chưa có SLA/uptime commitment |
| `02-Cursus-SRS.md` | FR/NFR chi tiết, đã sửa mâu thuẫn NFR-1 vs KPI 1.000 SV, **đã có** rate limiting cụ thể (mục 1.2b — 60/300 req/phút/SV), **đã có** observability cụ thể (NFR-10 — Sentry), **đã có** fallback khi LLM provider lỗi (mục 4.1 — OpenAI dự phòng) | Chưa có: migration/backup strategy cho Postgres |
| `03-Cursus-Execution-Plan.md` | Lịch trình theo mốc rõ ràng | Chưa có: kế hoạch CI/CD (test tự động chạy khi nào), chưa có code review process |
| `04-Cursus-Terminology.md` | Giải thích thuật ngữ đầy đủ, dễ onboard người mới | Không cần production hoá — đây là tài liệu học, giữ nguyên |
| `05-Cursus-Competitive-Analysis.md` | Cập nhật theo dữ liệu mới nhất, có câu trả lời sẵn khi bị hỏi | Cần review định kỳ (thị trường AI edtech đổi nhanh — nên đặt lịch review lại trước mỗi lần pitch quan trọng) |

---

## 2. Checklist tính năng cần có để gọi là "chuẩn production" (không phải để demo, mà để dùng thật)

### Bắt buộc có (nếu sản phẩm ra khỏi giai đoạn đồ án, dùng thật)
- [x] **Auth thật + bảo mật:** ĐÃ CÓ (12/08/2026) — invite-only registration cho cả 3 role (không còn self-registration mở), rate limiting đăng nhập chống brute-force, refresh token + access token ngắn hạn (không phải JWT sống 24h cố định). Google OAuth chỉ xác thực tài khoản đã tồn tại. Chi tiết: `10-Cursus-Auth-Onboarding-Sandbox-Spec.md`.
- [ ] **Multi-tenant RLS enforcement thật ở tầng DB:** đã tạo `organizations`/`organization_memberships` + RLS policy trên 4 bảng gốc, nhưng role kết nối DB hiện tại (`postgres`, Supabase pooler) có `BYPASSRLS` — RLS chưa có tác dụng thật, enforcement thật đang ở tầng ứng dụng. Cần tạo role Postgres quyền hạn chế (không `BYPASSRLS`) và đổi `DATABASE_URL` sang role đó. Chi tiết + cách kiểm tra: `11-Cursus-ERD-Multitenancy.md` mục 4.
- [x] **Xoá dữ liệu theo yêu cầu** — ĐÃ CÓ FR (10/08/2026): `FR-1.3` ở `02-SRS.md` mục 3.1 (API `DELETE /api/v1/students/{student_id}/data`, hard delete, Mốc 3 Must, `01-PRD.md` mục 8.2). Trước đó chỉ là cam kết trong PRD, chưa có cơ chế thực thi — đã đóng gap.
- [ ] **Backup & Disaster Recovery:** backup Postgres tự động hàng ngày, có kế hoạch khôi phục khi mất dữ liệu — **khả thi ngay với ngân sách hiện có**, chỉ cần nâng Supabase lên Pro ($25/tháng, xem `06` mục 2.2), không cần tự xây backup script.
- [x] **Rate limiting & chống lạm dụng** — ĐÃ CÓ ở `02-SRS.md` mục 1.2b (60 req/phút/SV nhóm AI, 300 req/phút/SV nhóm CRUD, `slowapi`).
- [x] **Observability** — ĐÃ CÓ ở `02-SRS.md` NFR-10 (Sentry + structured logging + alert email).
- [ ] **CI/CD:** test tự động chạy khi push code (GitHub Actions — công cụ đã chọn ở `06` mục 1.5, còn thiếu file workflow YAML thật).
- [x] **Xử lý khi LLM provider lỗi/timeout** — ĐÃ CÓ: fallback provider ở `02-SRS.md` mục 4.1, kịch bản demo lỗi ở `00-Cursus-Playbook.md` PHẦN 5B.
- [ ] **Điều khoản sử dụng & Chính sách quyền riêng tư** — văn bản pháp lý thật nếu có SV thật dùng ngoài phạm vi đồ án.
- [ ] **Zalo OA hoặc kênh thông báo ngoài app** — chỉ khả thi khi team/dự án có tư cách pháp nhân (GPKD) để xác minh — xem lý do đã kiểm chứng ở `00-Cursus-Playbook.md`.

### Nên có (cải thiện chất lượng, không chặn việc ra mắt)
- [ ] Đa ngôn ngữ (đã ghi Out-of-Scope trong PRD, giữ nguyên quyết định).
- [ ] Mobile app native (đã ghi Out-of-Scope, giữ nguyên).
- [ ] A/B testing framework thật (thay vì mô phỏng 2 kịch bản độc lập như hiện tại) — chỉ làm được khi có SV thật dùng sản phẩm.
- [ ] Tích hợp LTI 1.3 thật vào FLM (đã ghi Out-of-Scope, đây là bước lớn nhất nếu thương mại hoá thật).

### Không cần cho production của riêng sản phẩm này (over-engineering nếu làm)
- Kubernetes/microservices — quy mô hiện tại (1 trường, vài nghìn SV) chưa cần.
- Multi-region deployment — chỉ phục vụ SV FPT, không cần.

---

## 4. 10 Deliverables THẬT của BTC + thang điểm 50

**Đã tách sang file riêng:** `08-Cursus-Deliverables-Checklist.md` (10/08/2026) — vì đây là bản chất "tra cứu nhanh lúc gấp" khác với phần đánh giá kỹ thuật dài ở mục 1-2 trên. Dark mode đã đóng gap (thêm vào `00-Cursus-Playbook.md` PHẦN 1B từ trước).

---

## 5. Cách dùng file này

Không làm gì với file này trước Gate 2. Sau Gate 2 (14/08), khi bước vào 9 ngày hoàn thiện cuối cùng (Mốc 3, hạn 23/08), dùng bảng "Bắt buộc có" ở mục 2 làm checklist review cùng cả team — mỗi mục làm xong thì tick, mục nào không kịp thì ghi vào "Known Limitations" trong hồ sơ bàn giao (đúng tinh thần đã làm với LTI 1.3 và Zalo OA — không giấu giới hạn, nói rõ và có kế hoạch). Riêng deliverable cụ thể (10 mục + thang điểm) tra ở `08-Cursus-Deliverables-Checklist.md`.

---

*Đọc cùng `00-Cursus-Playbook.md` (việc cần làm ngay), `01-Cursus-PRD.md` đến `05-Cursus-Competitive-Analysis.md` (nội dung gốc vẫn giữ nguyên, không cần viết lại — chỉ bổ sung theo checklist này khi tới Mốc 3), `08-Cursus-Deliverables-Checklist.md` (10 deliverable + thang điểm).*
