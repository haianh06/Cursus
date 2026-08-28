# Kế hoạch làm tiếp — bản dễ đọc

> Viết ngày 26/08/2026, tại `HEAD = cc74d64`. Test đang xanh: 576 passed · 0 failed.
> Bản chi tiết kèm code nằm ở `docs/superpowers/plans/2026-08-26-dong-bo-3-role.md`.
> Bản đối chiếu từng ô: `docs/CHECKLIST_DONG_BO_ROLE.md`.

---

## Nói ngắn gọn: còn lại những gì

Phần khó nhất **đã xong**. Ba role đã nối lại được với nhau: AI chặn câu hỏi thì
giảng viên thấy, Admin quản trị được lớp học, mọi hành động nhạy cảm đều để lại dấu vết.

Còn lại đúng **4 việc code** + **2 việc không phải code**:

| | Việc | Nó cho ai thấy gì |
|---|---|---|
| 🔴 | Xoay lại mật khẩu/khoá API bị lộ | Không ai thấy gì. Nhưng đang là lỗ hổng thật |
| 🟢 | Đưa code lên `main` | Cả nhóm cùng đứng trên một nền |
| ⭐ | Đo chi phí & tốc độ của AI | Trả lời được câu "mỗi câu hỏi tốn bao nhiêu tiền, mất bao lâu" |
| | Cho Admin xem "AI nhớ gì về sinh viên" | Xử lý được yêu cầu trích xuất dữ liệu |
| | Nút "xin bản sao / xin xoá dữ liệu của tôi" | Tab Admin đang rỗng sẽ có việc thật |
| | Hồ sơ giảng viên đầy đủ hơn | Admin biết GV dạy gì, tạo quiz gì, mở chặn câu nào |

Nếu chỉ làm được **hai việc**, làm việc số 1 và số 3.

---

## Buổi 1 — Xoay credential *(không phải code, ~30 phút)*

**Vấn đề:** file `.env.bak` từng bị commit lên GitHub. Cả hai nhánh đã xoá file rồi,
nhưng **git nhớ mọi thứ** — ai clone repo về vẫn đọc được nội dung cũ. Repo này đang public.

**Việc cần làm:** vào từng dịch vụ, tạo khoá mới, thay vào `.env` trên máy và trên server:

- [ ] Google API key (Gemini)
- [ ] Mật khẩu Postgres / Supabase
- [ ] Mật khẩu Redis
- [ ] Tài khoản SMTP gửi mail

**Xong thì biết:** chạy lại app, mọi thứ vẫn hoạt động với khoá mới.

> Đây là việc duy nhất trong cả kế hoạch mà **để lâu sẽ tệ hơn**, không phải chỉ chậm hơn.

---

## Buổi 2 — Đưa code lên `main` *(~30 phút)*

**Vấn đề:** nhánh `main` chưa cập nhật từ 16/08. Code hiện tại đi trước nó **324 commit**.
Ai nhìn vào `main` sẽ thấy một sản phẩm cũ 10 ngày.

**Tin tốt:** tôi đã chạy thử merge khô — **0 conflict**. Đây là việc rẻ nhất trong danh sách.

**Việc cần làm:**
- [ ] Mở Pull Request `haidang2425` → `main`
- [ ] Ghi mô tả PR gồm 3 điều: Admin quản trị được lớp học · guardrail đã nối vào hàng đợi GV · merge xong nhánh develop
- [ ] Merge

**Xong thì biết:** `main` chạy được, test xanh.

---

## Buổi 3 — Đo chi phí và tốc độ AI ⭐ *(việc quan trọng nhất còn lại)*

### Vì sao đây là việc quan trọng nhất

Đề bài chấm điểm ở mục **PLO 5**: *"giám sát cơ bản — độ trễ / lỗi / chi phí"*.
Ba vế đó hiện là:

| Vế | Tình trạng |
|---|---|
| lỗi | ✅ ổn — có log, có trạng thái job, có cờ báo suy giảm |
| độ trễ | 🟠 nửa vời — chỉ đo cả request HTTP, không tách riêng phần gọi AI |
| chi phí | ❌ **trống hoàn toàn** |

Đây là vế duy nhất đang trống trong toàn bộ tiêu chí chấm.

### Vì sao nó dễ hơn nghe

Toàn bộ **11 chỗ gọi AI** trong hệ thống đều đi qua đúng **một cửa**:
`get_llm()` ở `src/services/core/llm.py` — file này chỉ có 30 dòng.

```
practice_generator · empathic_reply · planner · plan_builder · qa_answer
reflection · reflection_engine · reflection_suggestion · weekly_plan
quiz_generator · rag
```

Bịt được cái cửa đó là đo được cả 11 chỗ cùng lúc. Và thư viện Google **đã trả sẵn
số token** trên mỗi lần trả lời — hiện đang bị vứt đi ngay tại chỗ nhận.

### Việc cần làm

- [ ] **Bảng mới `ai_usage`** — mỗi dòng là một lần gọi AI:
      *khi nào · tổ chức nào · người nào · tính năng gì · model gì · token vào · token ra · mất bao nhiêu ms · thành công hay không*
- [ ] **Bọc `get_llm()`** để tự ghi vào bảng đó mỗi lần gọi
- [ ] **Một route cho Admin đọc số**: `GET /admin/ai-usage?days=30`

### Hai cái bẫy — đọc trước khi code

**Bẫy 1 — đừng dùng lại 2 bảng cũ.** Trong database đã có sẵn `RAGTrace` và
`LLMUsageEvent`, nhìn thì đúng việc. **Đừng đụng vào.** ADR-017 đã đóng chúng có lý do:
cột `message_id` bắt buộc phải có, mà nửa số chỗ gọi AI không sinh ra `Message` nào;
và `LLMUsageEvent` **không có cột thời gian** nên không chia được chi phí theo tuần/tháng.
Bảng mới phải có `created_at`, `organization_id`, và `message_id` cho phép rỗng.

**Bẫy 2 — 8 trong 11 chỗ dùng `.with_structured_output(...)`.** Cách gọi này trả về
một object đã bóc sẵn, **số token bị mất trên đường**. Nếu chỉ đọc `response.usage_metadata`
thì 8/11 chỗ sẽ ghi ra số 0 mà không báo lỗi gì cả — kiểu bug tệ nhất.
Cách chắc ăn: dùng **callback handler** của LangChain gắn vào lúc tạo client
(`callbacks=[...]`), vì nó nhận được số token ở tầng dưới, không phụ thuộc cách gọi.

### Xong thì thấy gì

Kể cả chưa kịp dựng màn hình, chỉ cần một câu SQL là trả lời được khi bảo vệ:
*"tuần qua hệ thống gọi AI 1.240 lần, tốn 2,1 triệu token, trung bình 830ms một câu,
tính năng tốn nhất là sinh kế hoạch tuần."*

> **Ưu tiên có dữ liệu trước, màn hình sau.** Nếu hết thời gian, thiếu UI vẫn bảo vệ được;
> thiếu dữ liệu thì không.

---

## Buổi 4 — Cho Admin xem "AI nhớ gì về sinh viên"

**Vấn đề:** hệ thống có bảng `StudentMemoryEntry` — nơi AI ghi nhớ thói quen, sở thích
học tập của từng sinh viên. Admin hiện **không xem được**, kể cả khi sinh viên yêu cầu
"cho tôi biết hệ thống lưu gì về tôi".

**Việc cần làm** — thêm 3 đường đọc vào hồ sơ sinh viên 360°:
- [ ] `GET /admin/students/{id}/memory` — bộ nhớ AI *(làm cái này trước)*
- [ ] `GET /admin/students/{id}/quizzes`
- [ ] `GET /admin/students/{id}/practice-sets`

Cả ba phải đi qua `_audited_read` — tức là **ghi nhật ký trước khi trả dữ liệu**,
đúng như 14 route Student 360 hiện có.

**Làm bộ nhớ AI trước**, vì buổi 5 cần đến nó.

---

## Buổi 5 — Nút "xin bản sao / xin xoá dữ liệu của tôi"

**Vấn đề:** Admin đã có sẵn một màn hình xử lý yêu cầu dữ liệu khá đầy đủ —
xem · duyệt · từ chối · hoàn tất · xem trước khi xoá · xác nhận xoá.
Nhưng **không ai tạo được yêu cầu**. Bảng `DataRequest` chưa từng có một dòng nào
sinh ra từ hệ thống thật.

Kết quả: đem đi demo là một tab rỗng. Muốn nó có dữ liệu phải insert tay vào database.

**Việc cần làm:**
- [ ] Route mới `POST /me/data-requests` — sinh viên/giảng viên tự gửi
      *(kiểu: xin bản sao, hoặc xin xoá)*
- [ ] `GET /me/data-requests` — xem yêu cầu của mình đang ở trạng thái nào
- [ ] Nút gửi trong `SettingsScreen.jsx`

**Xong thì thấy:** sinh viên bấm nút → yêu cầu hiện ngay trong tab Admin → Admin xử lý
được từ đầu đến cuối. Một vòng tròn khép kín để quay demo.

---

## Buổi 6 — Hồ sơ giảng viên đầy đủ hơn *(có thì tốt, thiếu vẫn bảo vệ được)*

**Vấn đề:** hồ sơ sinh viên 360° có **15 đường** để nhìn. Hồ sơ giảng viên chỉ có **1**.
Admin gần như không thấy giảng viên làm gì.

**Việc cần làm** — thêm 4 mảng:
- [ ] Nhật ký buổi học đã dạy
- [ ] Quiz đã tạo / đã publish
- [ ] Bộ luyện tập đã duyệt cho sinh viên
- [ ] Quyết định guardrail — đã mở chặn câu nào

---

## Trước lúc demo — 3 thứ phải thử tay

Đợt merge vừa rồi chỉ được kiểm trên SQLite. Ba thứ sau **chưa ai thử thật**:

- [ ] Chạy lại toàn bộ trên **Postgres** *(rủi ro thấp — không có migration mới, nhưng SQLite không phải bằng chứng)*
- [ ] **Đăng nhập SSO sang EduSync** — đây là chỗ đáng nghi nhất. Nhánh develop vừa sửa
      CSRF và cookie, mà SSO thì sống bằng cookie
- [ ] **Đăng nhập Google thật** — mới chỉ test được đường demo không mật khẩu

---

## Một cái bẫy trong repo — nhớ trước khi chạy seeder

`scripts/seed_curriculum.py` có dòng xoá file (`path.unlink()`). Chạy nó trong thư mục
chính sẽ **xoá 8 file dữ liệu môn học đang được git theo dõi**
(COV111, COV121, COV131, DTR103, EXE401, PRN212, PRU221m, SBA301).

Không phải lỗi do merge — nó có sẵn. Nếu cần chạy seeder, commit trước đã.

---

## Bốn câu cần người quyết, không cần lập trình viên

Đây không phải việc kỹ thuật. Ai đó phải chốt trước khi có thể code:

| Câu hỏi | Vì sao phải hỏi |
|---|---|
| **Có nên cho sinh viên biết mình đang bị đánh dấu rủi ro không?** | Giảng viên bấm "đã can thiệp" nhưng sinh viên không nhận được gì. Muốn nối lại thì phải trả lời câu này trước — nó là quyết định về mặt giáo dục, không phải kỹ thuật |
| **Admin có được xem ghi chú riêng của giảng viên về sinh viên không?** | Quyết định về quyền riêng tư |
| **12 môn học kia (SWT301, PEN, TMI_ELE...) có thật sự muốn thêm vào không?** | 12 file dữ liệu đó đang bị hệ thống bỏ qua vì không phải syllabus thật, chỉ là bản tóm tắt tự sinh. Nếu muốn thêm thật thì phải bóc syllabus thật cho chúng — hiện mới chỉ là **hoãn lại**, chưa xong |
| **Cách ly dữ liệu ở tầng database (RLS) có làm không?** | Hiện tổ chức A không thấy dữ liệu tổ chức B là nhờ code lọc — chạy đúng, nhưng quên một chỗ là rò. Làm chặt ở tầng database cần thao tác trên Supabase Dashboard và sửa 40+ endpoint. Kế hoạch riêng đã có sẵn ở `docs/decisions/rls-migration-plan.md` |

---

## Còn về các nhánh của bạn bè

| Nhánh | Còn bao nhiêu chưa gộp | Khó cỡ nào |
|---|---|---|
| `main` | — | **Dễ nhất, 0 conflict.** Làm ở buổi 2 |
| `thanhbinh` | 13 commit | 35 chỗ đụng — frontend giảng viên/sinh viên |
| `chung` | 96 commit | 111 chỗ đụng — admin kiểu cũ (tab) vs kiểu mới (route) |
| `haianh` | 8 commit | **321 chỗ đụng** — nhánh này đổi tên cả thư mục `src/` thành `backend/`, nên gần như mọi file đều lệch chỗ |

**Nên làm sớm:** hỏi haianh06 xem có giữ hướng đổi tên `src/` → `backend/` không.
Càng để lâu, 321 chỗ đụng đó càng nhiều thêm. Đây là câu hỏi 5 phút, không phải việc code.

---

## Tóm lại — thứ tự

```
1. Xoay credential          ← làm ngay, không phải code
2. PR lên main              ← rẻ nhất, 0 conflict
3. Đo chi phí AI            ← ⭐ thứ duy nhất còn lại bị chấm điểm
4. Bộ nhớ AI của sinh viên
5. Nút xin dữ liệu          ← cần buổi 4 xong trước
6. Hồ sơ giảng viên
```

**Hết thời gian ở đâu cũng dừng được** — mỗi buổi tự nó đã là một sản phẩm chạy được,
không để lại trạng thái dở dang.

**Nếu rất gấp:** làm 1 → 2 → 3 rồi dừng.
