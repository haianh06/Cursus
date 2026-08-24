---
name: cursus-engineering-guide
description: Dùng skill này khi task liên quan đến kiến trúc hệ thống, xây dựng agent AI/RAG, guardrail, code style, devops/deploy, testing, hoặc khi gặp lỗi cần troubleshoot. Kích hoạt khi thấy từ khoá "kiến trúc", "architecture", "agent", "RAG", "guardrail", "LangGraph", "pattern", "anti-pattern", "code style", "deploy", "devops", "test", "lỗi", "troubleshoot", "chi phí", "cost".
---

# Bản đồ kiến thức kỹ thuật Cursus (docs/guide)

`docs/guide/` là tài liệu tham khảo kỹ thuật CHUNG (best practice, không phải quyết định riêng của Cursus). Dùng để nâng chất lượng code/kiến trúc, KHÔNG dùng để ghi đè quyết định đã chốt trong `docs/planning/v2` (ví dụ: nếu guide gợi ý 1 DB khác nhưng `06-Cursus-Ha-tang-Supabase-Scale2000.md` đã chốt Supabase — làm theo Supabase).

## Điều hướng theo loại task

| Đang làm gì | Mở thư mục/file nào trong `docs/guide/` |
|---|---|
| Thiết kế kiến trúc tổng thể 1 module mới | `@docs/guide/architecture/` |
| Cần biết cách làm ĐÚNG cho 1 vấn đề đã có sẵn giải pháp chuẩn | `@docs/guide/patterns/` |
| Nghi ngờ đang code theo hướng sai/dễ gây lỗi | `@docs/guide/anti-patterns/` — đọc trước khi merge, tự đối chiếu code vừa viết |
| Build agent AI (Q&A có trích nguồn, guardrail chặn làm hộ bài, luồng Plan→Do→Reflect) | `@docs/guide/langgraph/` kết hợp `@docs/guide/patterns/` |
| Băn khoăn về style code (đặt tên, cấu trúc file, convention) | `@docs/guide/code-style/` |
| Cần biết chuẩn "coi như xong" của 1 hạng mục | `@docs/guide/deliverables/` |
| Deploy, CI/CD, môi trường | `@docs/guide/devops/` |
| Setup môi trường dev lần đầu | `@docs/guide/setup/` |
| Viết test / chiến lược test | `@docs/guide/testing/` |
| Câu hỏi về chi phí vận hành | `@docs/guide/cost-management.md` |
| Cần dịch vụ free tier để demo/test | `@docs/guide/free-accounts.md` |
| Gặp lỗi lạ, không biết bắt đầu debug từ đâu | `@docs/guide/troubleshooting.md` |
| Không chắc bắt đầu từ đâu trong bộ 10 chapter | `@docs/guide/chapter-01.md` rồi đọc tuần tự — đây là mạch chính, các thư mục còn lại là phụ lục tra cứu nhanh |

## Nguyên tắc dùng guide

1. Chỉ load ĐÚNG phần liên quan tới task hiện tại — không đọc cả 10 chapter mỗi lần, tốn context vô ích (progressive disclosure).
2. Nếu nội dung guide mâu thuẫn với quyết định đã chốt trong `docs/planning/v2`, **quyết định trong planning/v2 luôn thắng** — guide chỉ là kiến thức nền, không phải chỉ thị riêng cho Cursus.
3. Nếu 1 pattern trong guide đòi hỏi dependency/công nghệ chưa có trong stack đã chốt (xem AGENTS.md mục 1), hỏi user trước khi thêm, không tự ý áp dụng.
