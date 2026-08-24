# Cursus — 10 Deliverables THẬT của BTC + Thang điểm 50

> Tách ra từ `07-Cursus-Production-Readiness-Checklist.md` ngày 10/08/2026 — file `07` là **đánh giá kỹ thuật** (docs còn thiếu gì để "chuẩn production"), file này là **tra cứu nhanh lúc gấp deadline** (nộp đúng file, đúng vị trí, biết đang thiếu gì). Hai việc khác bản chất, tách để không phải kéo qua phần đánh giá kỹ thuật dài mỗi lần chỉ cần tra 1 dòng deliverable.

---

## 1. 10 Deliverables THẬT của BTC (thay cho giả định "8 hạng mục" bản trước)

> **Phát hiện quan trọng (giữ nguyên từ bản gốc):** repo đã có sẵn `docs/guide/deliverables/checklist.md` do BTC cung cấp — đây là danh sách CHÍNH THỨC, khác với "8 hạng mục hồ sơ bàn giao" mà các file khác từng dùng làm giả định chung chung (Mã nguồn/hướng dẫn cài đặt/dữ liệu mẫu/tài khoản demo/kiến trúc/test/ADR/video — không sai về tinh thần, nhưng không khớp đúng tên & vị trí file BTC yêu cầu). Từ nay dùng đúng 10 mục dưới đây.

| # | Deliverable | Vị trí file trong repo | Trạng thái hiện tại |
|---|---|---|---|
| 1 | Source Code | `src/` (BTC đã scaffold FastAPI+LangGraph skeleton), `frontend/` (Vite+React) | **Cập nhật 11/08/2026, vẫn chưa xử lý:** branch `haidang2425` (HEAD) chỉ có `src/` skeleton rỗng + frontend hoàn chỉnh; backend thật đầy đủ (auth/RBAC/JWT/session, QA/Plan/Instructor/Student/Canvas API) đang nằm trên branch `chung`/`develop`, **chưa merge** — đây là "Job #0" ưu tiên số 1, xem kế hoạch tích hợp chi tiết ở `09-Cursus-Team-Assignment.md` mục 1 |
| 2 | README.md | `/README.md` (Problem → Solution → Tech Stack → Setup → Team) | **Đã điền 11/08/2026** — README thật của Cursus. Bản gốc BTC + `README_boilerplate.md` gốc không bị xoá, giữ nguyên văn ở `docs/reference/btc-template/` để đối chiếu |
| 3 | Architecture Diagram | `/docs/architecture_diagram.md` (Mermaid, render trên GitHub) | Còn là template rỗng — dùng sơ đồ LangGraph đã có ở `02-SRS.md` mục 1.4 làm gốc |
| 4 | AI Logs | Hệ thống hook tự động (`.claude/`, `.cursor/`, `.codex/`, `.gemini/`, `.github/hooks/`) + `AI20K-Log-Bridge` (extension cho ChatGPT/Claude.ai web) | **Đã xác nhận hoạt động** — `.ai-log/session.jsonl` đang ghi log thật, có archive các ngày trước |
| 5 | Live URL / Deploy | — | Theo kế hoạch `03` — Gate 2 Must #15 |
| 6 | Video Demo | Upload YouTube/Drive, tối đa 5 phút | Kịch bản đã có ở `00` PHẦN 5 — cần quay thật |
| 7 | Pitch Deck | `/presentation/pitch_deck.pptx` (10 slide, theo structure trong `presentation/README.md`) | Chưa làm — thêm vào Mốc 3 |
| 8 | Weekly Journal | `/JOURNAL.md` (mục tiêu/hoàn thành/khó khăn/bài học MỖI TUẦN) | **Đã bắt đầu điền 10/08/2026** (Week 1, dựng từ git log thật) — tiếp tục cập nhật cuối mỗi tuần, không dồn cuối |
| 9 | Worklog | `/WORKLOG.md` (ai làm gì, kết quả gì — MỖI NGÀY) | **Đã bắt đầu điền 10/08/2026** (dựng lại 01/08→10/08 từ git log thật) — từ nay mỗi người tự thêm dòng cuối ngày, không suy ngược từ git log nữa |
| 10 | Evaluation Evidence | `/eval/results/report.md` (metrics, test results, user feedback) | Còn template — điền từ báo cáo RAGAS/guardrail đã có ở `02-SRS.md` FR-9.1/9.3 |

## 2. Thang điểm BTC chấm (tối đa 50, mục tiêu ≥35)

| Tiêu chí | Điểm sàn tối thiểu | Cách đạt (map vào docs đã có) |
|---|---|---|
| Product/Business | ≥8 | README đầy đủ + metrics (`01-PRD.md` mục 6) + user feedback |
| System Design | ≥7 | Architecture doc + Mermaid diagram (dùng `02-SRS.md` mục 1.4) |
| **UX/UI Design** | ≥7 | **Responsive + dark mode** — đã đưa vào checklist bắt buộc ở `00-Cursus-Playbook.md` PHẦN 1B (mục cuối) |
| DevOps | ≥6 | Docker (BTC đã có sẵn) + CI/CD (còn thiếu file workflow thật, xem `07` mục 2) + logging (Sentry đã có ở NFR-10) |
| Code Quality | ≥7 | Type hints + tests + `ruff` pass (BTC đã cấu hình sẵn `ruff.toml`, `Makefile check`) |

---

## 3. Cách dùng file này

Không làm gì với file này trước Gate 2 (14/08) trừ mục 1 dòng "AI Logs"/"Weekly Journal"/"Worklog" — 3 mục này cần cập nhật liên tục ngay từ bây giờ, không chờ tới Mốc 3. Các mục còn lại tra cứu khi chuẩn bị nộp bài — mỗi mục xong thì cập nhật cột "Trạng thái hiện tại", mục nào không kịp thì ghi vào "Known Limitations" trong hồ sơ bàn giao.

---

*Đọc cùng `07-Cursus-Production-Readiness-Checklist.md` (đánh giá kỹ thuật docs) và `03-Cursus-Execution-Plan.md` (lịch trình).*
