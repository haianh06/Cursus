# Spec thiết kế lại Admin — dựa trên nhánh `chung`, để code trên nhánh này

> Nguồn: đọc trực tiếp toàn bộ 6 router backend (2.981 dòng), 9 migration, 24 component frontend của `origin/chung` (worktree tách riêng, không đụng nhánh này) + `docs/Cursus_Admin_Role_Guide_2026-08-23.docx` do chính chung viết. Đây là **spec chức năng** (cần có gì, luồng ra sao) — **không phải bản thiết kế để copy y hệt**. Phần 5 nói rõ chỗ nào nên làm khác chung, vì chính code của chung cũng có vài điểm chưa nhất quán (đã ghi rõ).

---

## 1. Kiến trúc thông tin (IA) — 9 màn hình cần có

Đổi từ 8-tab-trong-1-trang (`AdminConsole.jsx` hiện tại) sang **route-based**, chia 2 nhóm điều hướng:

```
QUAN SÁT                         QUẢN TRỊ
├ Tổng quan                      ├ Chương trình học
├ Người dùng                     ├ Tài khoản & lời mời
└ Yêu cầu dữ liệu                ├ Chính sách AI & rủi ro
                                 └ Cấu hình & hệ thống
```

Cộng 2 route con (không nằm trong sidebar, chỉ vào được qua "Xem hồ sơ"):
- `/admin/students/:id` — Student 360 (1 tóm tắt + 8 tab dữ liệu gốc)
- `/admin/instructors/:id` — Instructor 360 (chỉ tổng hợp, không có tab raw)

**Nhận xét cần sửa khi làm lại (chung tự để lại vấn đề này):** nhóm "Quản trị" chỉ có 4 mục sidebar nhưng thực chất render ra **9 component khác nhau** — riêng "Cấu hình & hệ thống" gộp tới 5 màn hình con (Settings form + Academic Calendar + Analytics + Access Audit + Audit Log) cuộn chung 1 trang dài, chỉ nối bằng anchor link. **Nên tách mỗi cái thành sub-tab/route riêng thay vì cuộn dài** — đây là điểm chung tự nhận là "gộp cho tiện route, không phải chủ đích UX tốt".

## 2. Mô hình quyền & audit cần có (khác hẳn nhánh hiện tại)

### 2.1 Permission matrix chi tiết hơn role-gate hiện tại

Hiện tại: chỉ có `require_roles(ADMIN)` — vào được là làm được hết.

Cần có: 1 lớp quyền theo `(Resource, Permission)` chồng lên role-gate. `Permission`: `READ, READ_SENSITIVE, WRITE, DELETE, APPROVE, MANAGE`. `Resource`: `PLAN, CHAT, REFLECTION, ASSIGNMENT, COURSE, CURRICULUM, KPI, RISK, RISK_CASE, INTERVENTION, SESSION, SUBMISSION, STUDENT_DOCUMENT, AUDIT, USER, SETTING, AI_POLICY, DATA_REQUEST, SYSTEM_HEALTH`.

**Điểm quan trọng nhất:** Admin **KHÔNG** có quyền `READ` thường trên PLAN/CHAT/REFLECTION/SUBMISSION/STUDENT_DOCUMENT/RISK/INTERVENTION/SESSION — chỉ có `READ_SENSITIVE`. Nghĩa là **không có đường đọc dữ liệu sinh viên nào "rẻ", mọi lần đọc đều bắt buộc qua cơ chế audit** ở mục 2.2. Đây là nguyên tắc thiết kế cốt lõi, không phải chi tiết phụ.

### 2.2 Mô hình "direct full read" — audit trước, trả dữ liệu sau

Với mọi lần Admin đọc dữ liệu gốc của 1 sinh viên cụ thể:
1. Chạy loader lấy dữ liệu (trong transaction).
2. Ghi 1 audit event (loại `ADMIN_SENSITIVE_READ`, có actor/subject/resource_type/resource_id/số bản ghi trả về) — **commit audit TRƯỚC**.
3. Nếu ghi audit lỗi → rollback toàn bộ, **không trả một phần dữ liệu nào**, trả lỗi 503 riêng (không phải lỗi chung chung).
4. Chỉ khi audit commit thành công mới trả dữ liệu về.

Resource-id dùng 2 kiểu: đọc cả danh sách (vd "toàn bộ conversation của SV X") dùng 1 id ổn định `collection:{resource}:{student_id}` để gom nhóm trong audit trail; đọc 1 bản ghi cụ thể (vd 1 conversation) dùng đúng id bản ghi đó — để biết chính xác bản ghi nào đã bị mở.

**Không dùng case/session/TOTP như bản đầu của chung (ADM-00→13) — chung đã tự bỏ ngày 23/08** vì cho là phức tạp không cần thiết cho quy mô hiện tại. Gate chỉ còn: role ADMIN + quyền `READ_SENSITIVE` đúng resource + audit ghi được. **Nên cân nhắc kỹ trước khi bê nguyên quyết định này** — chung tự nêu rủi ro: "tài khoản Admin duy nhất chỉ được bảo vệ bằng mật khẩu, không còn lớp nào chặn được nếu tài khoản bị chiếm." Nếu nhánh này vẫn giữ MFA (đang giữ), có thể **giữ direct-read nhưng KHÔNG bỏ MFA** — 2 quyết định độc lập, chung gộp chung nhưng không bắt buộc phải theo cả 2.

### 2.3 Quy tắc chung áp dụng cho MỌI thay đổi (curriculum, guardrail, risk threshold, settings)

**Không sửa đè — mọi thay đổi là 1 phiên bản mới:** Preview (chưa đổi gì) → Publish (tạo version mới, có thể truy vết) → History (ai/khi nào) → Restore/Rollback (tạo hành động MỚI, không xoá lịch sử cũ). Đây là đúng pattern versioning risk-policy đã có sẵn trong nhánh này (mục 14.1 `PROJECT_CONTEXT.md`) — chung áp dụng thêm cho **guardrail rules** và **curriculum document lifecycle**, chưa có ở nhánh hiện tại.

### 2.4 DTO allow-list, không dump JSON thô

Mọi dữ liệu gốc trả về UI phải qua danh sách field được khai báo rõ ràng theo từng loại resource (xem mục 3.3) — field lạ/không khai báo bị lặng lẽ bỏ qua, không hiện ra màn hình. Không có nút save/edit/delete trực tiếp trên dữ liệu gốc — muốn xoá phải qua luồng Data Request (mục 3.5).

## 3. Chi tiết từng màn hình — nội dung cần có

### 3.1 Tổng quan (`/admin/overview`)

Thứ tự đọc: trạng thái hệ thống → việc cần làm → tín hiệu → nhật ký thay đổi.

- **Dòng trạng thái:** chấm màu (xanh=ổn/vàng=cần chú ý) + nhãn + "cập nhật lúc".
- **Nhịp toàn trường:** 4 số liệu dạng thẻ — SV hoạt động, GV hoạt động, số môn, số lớp.
- **Việc cần xử lý (Work Queue):** gộp từ **5 nguồn** — `RISK_SIGNAL` (→ Student 360 tab Rủi ro), `GUARDRAIL_EVENT` (→ Student 360 tab Hội thoại), `DATA_REQUEST` (→ trang Yêu cầu dữ liệu), `INGEST_JOB` (→ Chương trình học), `ACCESS_ANOMALY` (→ Cấu hình, mục lịch sử truy cập). Mỗi dòng: chip độ ưu tiên (CRITICAL/HIGH/MEDIUM/LOW, có màu), loại việc, subject id, tóm tắt (rút gọn, đầy đủ ở tooltip), thời gian dạng "vừa xong/X phút/X giờ/X ngày", nút "Mở". Mặc định chỉ hiện 5 dòng, có nút "xem tất cả N" mở phân trang 10 dòng/trang. **Việc không xác định được subject_id hoặc loại lạ → điều hướng về chính trang Tổng quan, không tạo link vỡ.**
- **Khối tín hiệu:** phân rã số việc theo loại; 2 tỉ lệ (vd tỉ lệ rủi ro chưa xử lý, tỉ lệ kích hoạt lời mời) — **mỗi tỉ lệ phải có numerator/denominator/khung thời gian/phương pháp đo, thu gọn trong 1 khối "chi tiết" bấm mới mở** (không cạnh tranh sự chú ý với work queue). **Không có mẫu số → hiện "chưa đo được", không bịa 0%.**
- **Thay đổi quan trọng gần đây:** danh sách audit event — ai đổi gì, tài nguyên nào, lúc nào.
- Giới hạn cần biết: mỗi nguồn queue tối đa 100 bản ghi, không cảnh báo khi chạm trần — nên cải thiện khi làm lại (ít nhất hiện cảnh báo "còn nhiều hơn N").

### 3.2 Người dùng (`/admin/people`)

Tìm theo tên/email + lọc theo vai trò (Student/Instructor/Admin) + phân trang. Bảng: Tên+Email, Vai trò, Trạng thái (Đang hoạt động/Đã khoá), tóm tắt học vụ, nút "Xem hồ sơ 360" (chỉ có với Student/Instructor, dòng Admin không có, vì tài khoản Admin là singleton không cần xem 360 chính mình).

### 3.3 Student 360 (`/admin/students/:id`) — màn hình phức tạp nhất

**Tab Tóm tắt (mặc định):** identity (tên/email/vai trò/trạng thái), 2 thẻ tổng hợp (Hoạt động, Rủi ro), danh sách lớp đã ghi danh nếu có. Dòng nhắc rõ: đây chỉ là số liệu, muốn xem dữ liệu gốc phải chọn tab.

**8 tab dữ liệu gốc, mỗi tab gọi 1 hoặc nhiều resource qua cơ chế mục 2.2:**

| Tab | Resource(s) gọi | Ghi chú |
|---|---|---|
| Kế hoạch & công việc | plans, tasks, progress-events, reminders | 4 resource, gọi song song |
| Bài tập & bài nộp | assignments, submissions | assignments dùng quyền READ thường (là tài liệu môn học, không phải dữ liệu riêng SV) |
| Phản tư | reflections | |
| Hội thoại | conversations (+ chi tiết từng conversation khi mở transcript) | Transcript đóng mặc định, mở mới tải; tin nhắn bị guardrail chặn có nhãn riêng |
| Rủi ro & can thiệp | risk, interventions | |
| Phiên tự học | sessions | |
| Tài liệu sinh viên | documents | |
| Lịch sử truy cập | (dùng API access-audit riêng, không phải raw-read) | Ai đã xem dữ liệu SV này, lúc nào — chỉ metadata, không có nội dung |

Mỗi loại resource cần 1 spec hiển thị riêng (field nào hiện, nhãn gì) — xem danh sách field đầy đủ ở Phụ lục A bên dưới. Nguyên tắc: field lạ/không khai báo → không hiện ra, không phải lỗi.

**Bắt buộc:** không có save/edit/delete trên màn hình này. Chuyển sinh viên khác hoặc đổi tab phải xoá sạch dữ liệu cũ trước khi tải dữ liệu mới (tránh hiện nhầm dữ liệu người này sang người khác trong lúc đang tải).

### 3.4 Instructor 360 (`/admin/instructors/:id`)

Đơn giản hơn Student 360 — không có tab raw. Chỉ: identity, 3 thẻ tổng hợp (Sĩ số, Khối lượng rủi ro, Số lần can thiệp), danh sách lớp phụ trách. Có dòng chú thích rõ: đây là số liệu tổng hợp, KHÔNG dùng để suy ra dữ liệu của 1 sinh viên cụ thể trong lớp — cố tình không có link đi sâu xuống từng sinh viên từ đây.

### 3.5 Yêu cầu dữ liệu (`/admin/data-requests`)

Hàng đợi yêu cầu do sinh viên gửi (truy cập/xuất/chỉnh sửa/xoá dữ liệu của chính họ). Mỗi dòng: chip trạng thái (Đang chờ/Đang xử lý/Hoàn tất/Từ chối), loại yêu cầu, subject, thời điểm gửi, và **các nút hành động ngay trong dòng**:
- Đang chờ → "Bắt đầu xử lý" hoặc "Từ chối" (cả 2 cần ghi chú lý do ≥10 ký tự).
- Đang xử lý + loại XOÁ → "Xem trước" (hiện số bản ghi sẽ xoá theo từng nhóm + 1 mã băm của đúng tập kết quả đó) → "Xác nhận xoá" (gửi kèm mã băm; nếu dữ liệu đổi giữa lúc xem trước và xác nhận, server phải từ chối, bắt xem trước lại).
- Đang xử lý + loại khác → "Hoàn tất" trực tiếp (không cần preview).

**Nguyên tắc quan trọng:** xoá là hành động không thể hoàn tác duy nhất trong Admin — đây là hành động DUY NHẤT bắt buộc phải xem-trước-rồi-mới-xác-nhận bằng mã băm khớp đúng tập dữ liệu, không chỉ là nút bị disable ở giao diện mà là ràng buộc phía backend.

### 3.6 Chương trình học (`/admin/governance/curriculum`) — màn hình lớn nhất

**Bảng môn học:** Mã, Tên, Kỳ, Nguồn (kèm "đồng bộ gần nhất" nếu có), số chunk, trạng thái nạp (đang xử lý/đã nạp/lỗi/chưa nạp — mỗi trạng thái icon+màu riêng), hành động (tải file lên, "Xem tài liệu" mở rộng dòng, xoá môn có xác nhận 2 bước).

**Mỗi tài liệu có 2 trạng thái độc lập song song:**
- Trạng thái nạp: Đang xử lý / Đã nạp / Lỗi / Chưa nạp.
- Trạng thái xuất bản: Bản nháp → Sẵn sàng duyệt → Đã xuất bản → Đã lưu trữ.

Hành động cho phép theo đúng trạng thái xuất bản: Bản nháp → [kiểm định, thay thế, xoá]; Sẵn sàng duyệt → [kiểm định, xuất bản, thay thế, xoá]; Đã xuất bản → [lưu trữ, xem lịch sử]; Đã lưu trữ → [xem lịch sử]. **Chỉ 1 phiên bản được "đã xuất bản" tại 1 thời điểm cho mỗi dòng tài liệu — ràng buộc này nên nằm ở DB, không chỉ ở code.**

**6 tiêu chí kiểm định trước khi 1 tài liệu được coi là hợp lệ để xuất bản:**
1. `official_scope` — thuộc phạm vi curriculum chính thức.
2. `admin_source` — nguồn khớp giữa record/metadata/provenance.
3. `sha256`/`checksum_matches_file` — checksum đúng định dạng và khớp file.
4. `readable_file` — đọc được, UTF-8 hợp lệ.
5. `has_chunks`/`chunk_limit` — có ít nhất 1 chunk, không vượt giới hạn.
6. `course_provenance` — mã môn trong metadata khớp mã môn thật.

**Upload/thay thế/xoá tài liệu là bất đồng bộ** (nhận file → trả về ngay "đang xử lý" → xử lý nền → frontend tự hỏi lại định kỳ tới khi xong hoặc hết số lần thử) — không có kênh real-time, chấp nhận polling ở quy mô này.

**Khoá thao tác theo tài liệu:** chỉ 1 hành động được chạy trên 1 tài liệu tại 1 thời điểm (không thể vừa kiểm định vừa xoá cùng lúc 1 tài liệu).

**Hộp thoại xác nhận cho publish/archive/rollback:** modal thật (không dùng `window.confirm` của trình duyệt), bẫy focus trong modal, textarea lý do bắt buộc 5-500 ký tự, nút Xác nhận chỉ bật khi lý do hợp lệ, lỗi hiện ngay trong modal và tự nhận focus.

### 3.7 Tài khoản & lời mời (`/admin/governance/access`)

**Quản lý tài khoản:** Khoá/mở khoá (yêu cầu lý do ≥5 ký tự) — khoá tài khoản phải **lập tức thu hồi mọi quyền truy cập dữ liệu nhạy cảm đang có hiệu lực** của người đó. Đổi vai trò/phạm vi lớp (yêu cầu lý do ≥10 ký tự, nghiêm hơn) — đổi thành Giảng viên bắt buộc gán ít nhất 1 lớp. **Không cho đổi vai trò thành Admin qua đường này** (chỉ có đúng 1 tài khoản Admin trong hệ thống — ràng buộc DB). Admin không tự khoá được chính mình. Dòng Admin trong bảng không có nút hành động, chỉ có nhãn "được bảo vệ".

**Quản lý lời mời:** Tạo lời mời (chỉ Student/Instructor, không mời được Admin) — Giảng viên bắt buộc có ít nhất 1 lớp. Token kích hoạt chỉ hiện **đúng 1 lần** ngay sau khi tạo (hoặc gửi lại) — phải nhắc người dùng copy ngay. Trạng thái gửi email: Đã gửi/Email đang tắt/Gửi thất bại (không hiện lỗi kỹ thuật thô, chỉ 1 mã lỗi an toàn). Có thể: thu hồi, gửi lại (đổi token mới), sửa phạm vi lớp (khi còn đang chờ).

### 3.8 Chính sách AI & rủi ro (`/admin/governance/ai-policy`)

**Guardrail:** danh sách rule, cờ "có rule nào đang tắt" hiện cảnh báo persistent nếu true. Rule "khoá cứng" (core-locked, vd chặn prompt injection) không cho tắt qua UI dù preview hay publish. Đổi 1 rule: nhập lý do → xem trước → công bố phiên bản mới → lịch sử/khôi phục.

**Risk policy:** 4 số cấu hình (ngưỡng ngày trễ, ngưỡng tỉ lệ hoàn thành, 2 trọng số) — **2 trọng số bắt buộc cộng đúng bằng 1.0** (kiểm tra cả client lẫn server). Xem trước cho biết bao nhiêu sinh viên đổi mức rủi ro, bao nhiêu bị bỏ qua, trước khi công bố.

### 3.9 Cấu hình & hệ thống (`/admin/governance/settings`)

Nên tách thành các sub-tab riêng thay vì 1 trang cuộn dài (xem ghi chú mục 1):
- **Cấu hình chung:** bật/tắt tự sinh cảnh báo rủi ro, học kỳ mặc định.
- **Học kỳ & lịch thi:** đặt học kỳ hiện hành (tên/ngày bắt đầu/số tuần học/số tuần thi); lịch thi theo môn (PE/FE, ngày, ca — hỗ trợ nhiều ca/môn, chặn 1 sinh viên trùng 2 ca thi cùng ngày). **Chung để màn này KHÔNG có bước xác nhận/lý do khi xoá lịch thi — nên sửa khi làm lại, thêm xác nhận + lý do giống các màn khác.**
- **Phân tích toàn trường:** số liệu môn/tài liệu/chunk/rủi ro, luôn kèm ghi chú phương pháp đo, không giả vờ đã đo được cái chưa đo.
- **Lịch sử truy cập nhạy cảm:** nhóm theo phiên/mục đích — ai xem dữ liệu SV nào, lúc nào, được phép hay bị từ chối — chỉ metadata, không có nội dung.
- **Nhật ký hệ thống:** toàn bộ audit event (không chỉ raw-read) — lọc theo loại sự kiện, actor, thời gian, tài nguyên. **Danh sách loại sự kiện lọc phải sinh ra từ đúng danh sách event type thật của backend, không hardcode tay** — chung tự để sót vài loại trong list lọc của họ.

## 4. Toàn bộ luồng backend cần có

### 4.1 Router/endpoint cần có (mô tả hành vi, không phải để copy nguyên path)

**Curriculum (courses + documents + academic term):**
- Danh sách môn (kèm ingest status, tự động đánh dấu job "stuck" thành failed nếu quá hạn).
- Thêm môn từ catalog, ẩn/khôi phục môn (soft-delete).
- CRUD tài liệu: liệt kê, xem nội dung, tải lên (multipart, giới hạn dung lượng, kiểm tra định dạng), thay thế, xoá — 3 việc sau đều bất đồng bộ (202 + job nền).
- Retry dọn dẹp file khi 1 lần xoá thất bại giữa chừng.
- Kiểm định tài liệu (chạy 6 tiêu chí mục 3.6, không lưu gì, chỉ trả báo cáo).
- Publish / Archive / Rollback tài liệu (đều bắt buộc `change_reason`).
- Liệt kê phiên bản 1 tài liệu + đánh dấu bản đang active.
- CRUD học kỳ hiện hành + lịch thi từng môn.
- Số liệu phân tích tổng hợp (kèm method_note giải thích cách đo, đánh dấu rõ cái nào "chưa đo được").

**Người dùng & lời mời:**
- Danh sách người dùng (kèm lần hoạt động gần nhất, danh sách lớp).
- Khoá/mở khoá (chặn tự khoá mình; khoá xong thu hồi ngay quyền truy cập nhạy cảm đang có).
- Đổi vai trò/phạm vi lớp (chặn đổi thành Admin; đổi thành Giảng viên bắt buộc có lớp).
- Tạo/thu hồi/gửi lại/sửa phạm vi lời mời — token chỉ trả về đúng 1 lần lúc tạo/gửi lại (lưu DB dưới dạng hash, không lưu token thật); gửi email tách biệt khỏi việc tạo bản ghi (tạo bản ghi luôn thành công, gửi email có thể thất bại độc lập, lỗi gửi không bao giờ lộ chi tiết kỹ thuật).

**Chính sách AI & rủi ro:**
- Guardrail: liệt kê rule + lịch sử phiên bản; xem trước bật/tắt 1 rule (không lưu); công bố (bắt buộc lý do, chặn nếu rule khoá cứng); khôi phục toàn bộ về mặc định (tạo phiên bản mới); rollback về 1 phiên bản cũ (tạo phiên bản mới trỏ về snapshot cũ, không sửa lịch sử).
- Risk policy: cùng pattern preview/publish/history/rollback, cộng ràng buộc 2 trọng số cộng = 1.

**Quan sát & 360 & đọc dữ liệu gốc:**
- Tổng quan (số liệu + work queue gộp 5 nguồn + tín hiệu + nhật ký thay đổi).
- Tìm kiếm/danh bạ người dùng (không cache ở tầng HTTP — dữ liệu định danh).
- Tóm tắt 360 (Student/Instructor) — không phải raw, chỉ số liệu tổng hợp.
- 13 route đọc dữ liệu gốc theo đúng cơ chế mục 2.2 (audit trước, trả sau, fail-closed) — mỗi route ứng với 1 loại dữ liệu (plans/tasks/assignments/submissions/reflections/conversations(+chi tiết 1 conversation)/documents/risk/interventions/sessions/progress-events/reminders).
- Lịch sử truy cập nhạy cảm (theo phiên/subject) + chi tiết từng event trong 1 phiên.

**Yêu cầu dữ liệu (DSAR):**
- Danh sách yêu cầu.
- Chuyển trạng thái (bắt đầu xử lý / từ chối / hoàn tất) — đều yêu cầu ghi chú lý do.
- Xem trước xoá (đếm bản ghi sẽ xoá theo nhóm, sinh mã băm của đúng tập đó).
- Xác nhận xoá (bắt buộc kèm đúng mã băm vừa xem trước — nếu dữ liệu đổi giữa 2 bước, từ chối, bắt xem trước lại).

**Cấu hình:** đọc/ghi 2 cấu hình toàn hệ thống (tự sinh cảnh báo rủi ro, học kỳ mặc định) — chỉ thêm cấu hình mới nếu có hành vi thật đọc nó (chung tự nêu bài học: từng có 1 cấu hình `demo_mode` không ai đọc, phải gỡ bỏ vì "nói dối người vận hành về thứ nó điều khiển").

### 4.2 Bảng dữ liệu cần có (mô tả mục đích, không bắt buộc đặt tên/cấu trúc y hệt)

- Bảng lưu quyền truy cập nhạy cảm đang hiệu lực (nếu vẫn muốn giữ khái niệm session/case) HOẶC bỏ hẳn nếu chọn direct-read đơn giản như chung — đây là quyết định kiến trúc cần chốt trước khi code, không phải chi tiết kỹ thuật.
- Mở rộng bảng audit log: thêm trạng thái trước/sau (JSON), lý do thay đổi, request/correlation id — mọi hành động ghi audit đều nên tận dụng các cột này thay vì chỉ ghi 1 dòng text.
- Bảng lời mời: có trạng thái gửi email, lần gửi cuối, số lần gửi lại, lỗi gửi gần nhất (dạng mã an toàn, không phải exception thô).
- Bảng chính sách risk theo phiên bản (đã có sẵn ở nhánh này theo mục 14.1 — tái dùng, không tạo lại).
- Bảng chính sách guardrail theo phiên bản (nếu nhánh này chưa có versioning cho guardrail — cần kiểm tra lại trước khi thêm).
- Mở rộng bảng tài liệu (`documents`): phạm vi (chính thức/riêng SV/cách ly), trạng thái xuất bản, nhóm phiên bản, thông tin xuất xứ, checksum, ai/khi nào kiểm định/xuất bản/lưu trữ — **ràng buộc DB: chỉ 1 bản ghi "đã xuất bản" cho mỗi nhóm phiên bản tại 1 thời điểm.**
- Ràng buộc DB: chỉ 1 tài khoản có vai trò Admin trong toàn hệ thống.
- Bảng yêu cầu dữ liệu (loại, trạng thái, ghi chú, bản tóm tắt xem-trước, bản tóm tắt kết quả) + bảng chính sách lưu trữ dữ liệu theo loại (mặc định ở trạng thái CHƯA duyệt cho tới khi Admin chủ động bật).

## 5. Vấn đề UX của chính chung — nên sửa khi làm lại, không nên copy nguyên

1. **3 kiểu xác nhận khác nhau cho cùng 1 loại hành động (huỷ được/không huỷ được):** Curriculum dùng modal tự làm có bẫy focus; Guardrail/Risk Policy dùng `window.confirm()` của trình duyệt (không đẹp, không đa ngôn ngữ được, không bẫy focus); Users/DataRequests/Curriculum-xoá-đơn-giản dùng xác nhận 2 bước inline. **→ chọn đúng 1 pattern (khuyến nghị: modal tự làm, tái dùng `ConfirmDialog.jsx` đã có sẵn ở nhánh này) và áp dụng nhất quán cho mọi hành động không-huỷ-được.**
2. **Component loading/error/empty dùng không nhất quán** — có màn dùng chung 1 wrapper, có màn tự viết riêng (Invitations, Users, Curriculum, Analytics, Calendar, AuditLog, GuardrailRules, RiskPolicy đều tự roll riêng). **→ dùng đúng 1 component chung cho mọi màn hình admin** (nhánh này đã có sẵn pattern tương tự qua `EmptyState`/`ErrorState`/`Skeleton`).
3. **Lịch thi xoá không xác nhận, không lý do** — trong khi mọi hành động khác đều bắt buộc cả hai. Bất nhất, nên nâng lên cùng chuẩn.
4. **Danh sách lọc loại sự kiện trong Nhật ký hệ thống bị hardcode tay, thiếu vài loại thật có trong backend.** → nên sinh danh sách này từ enum/constant dùng chung với backend.
5. **"Cấu hình & hệ thống" gộp 5 màn hình khác nhau vào 1 trang cuộn dài** chỉ vì tiện route — nên tách route/tab riêng.
6. **Text hiển thị dữ liệu mẫu (`localizeAdminRawContent`) gắn cứng với bộ seed data cụ thể của chung** — nếu port sang nhánh này, KHÔNG copy nguyên hàm này, phải viết lại theo đúng dữ liệu demo thật của nhánh này.

## 6. Việc chung tự nhận chưa xong (không nên coi là "đã hoàn thiện 100%")

Trích nguyên văn dịch từ tài liệu của chính họ: *"Admin đã đủ để xem và thao tác trên môi trường dev theo scope hiện tại, nhưng chưa nên gọi là production-ready."* Cụ thể: ADM-14 đang verify lại (tài liệu cũ còn mô tả sai luồng MFA/case cũ); staging E2E thiếu bằng chứng + chưa có người ký duyệt; **chính họ ghi "Merge develop: Chưa hoàn tất"**; kill-switch cấu hình cũ không còn tác dụng chặn; 1 nguồn tín hiệu (`ACCESS_ANOMALY`) luôn rỗng do đổi kiến trúc; còn nợ dọn bảng `mfa_*`/case/session cũ trong schema.

---

## Phụ lục A — Field cần hiện theo từng loại dữ liệu gốc (Student 360)

| Loại | Field chính cần hiện |
|---|---|
| plans | (theo cấu trúc WeeklyPlan hiện có của nhánh này) |
| tasks | tiêu đề, trạng thái, thời gian ước tính/thực tế, ngày dự kiến |
| assignments | tiêu đề, mã môn, mã lớp, hạn nộp, điểm tối đa, loại đánh giá, mô tả |
| submissions | (theo cấu trúc Submission hiện có) |
| reflections | nội dung phản tư, tuần, thời điểm |
| conversations | người gửi, thời điểm, nội dung, nhãn "đã bị chặn" nếu guardrail chặn |
| documents | tên file, thời điểm lưu |
| progress-events | loại sự kiện, thời điểm, task liên quan |
| reminders | nội dung, thời điểm |
| risk | loại rủi ro, mức độ, thời điểm sinh, thời điểm xử lý, hành động khuyến nghị |
| interventions | (theo cấu trúc Intervention hiện có) |
| sessions | phiên tự học — thời điểm bắt đầu/kết thúc |
| access-audit | quyết định (cho phép/từ chối), loại tài nguyên, id tài nguyên, thời điểm |

*(Ghi chú: bảng này lấy đúng danh sách field chung liệt kê trong `adminRawPresentation.js` — khi code lại cần đối chiếu field nào thật sự tồn tại trong model của nhánh này, không phải model của chung, vì 2 bên có thể lệch cấu trúc DB.)*

## Phụ lục B — Nguồn

- `origin/chung` @ `5c6ea39` — đọc qua worktree tạm (đã dọn, không ảnh hưởng nhánh này).
- `docs/Cursus_Admin_Role_Guide_2026-08-23.docx` (do chung viết, trích bằng `python-docx`).
- Xem thêm `docs/AUDIT_NHANH_CHUNG_ADMIN_23AUG.md` (báo cáo audit tổng quan, viết trước file này) cho phần đánh giá khả năng merge/tương thích migration.
