# Cursus — tình hình hiện tại và kế hoạch hoàn thiện

> Bản đọc-để-quyết-định, không có code. Bản chi tiết kỹ thuật kèm code nằm ở
> `docs/superpowers/plans/2026-08-26-dong-bo-3-role.md`.
> Ngày: 26/08/2026 · Nhánh `haidang2425`.

---

## Phần 1 — Sản phẩm đang có những thành phần gì

Cursus gồm **5 khối**, không phải 3 role như thường nghĩ:

| Khối | Là gì | Ai dùng | Tình trạng |
|---|---|---|---|
| **Sinh viên** | Vòng lặp Plan → Do → Reflect, hỏi đáp AI có trích nguồn, luyện tập, tự học | Student | 🟢 Đầy đủ, chạy thật |
| **Giảng viên** | Bảng điều khiển lớp, cảnh báo rủi ro, duyệt guardrail, quiz, nhật ký buổi học | Instructor | 🟡 Chức năng đủ, nhưng 1 hàng đợi rỗng vĩnh viễn |
| **Admin** | Quản trị chương trình, người dùng, chính sách AI, quan sát toàn trường | Admin | 🟡 Quan sát tốt, quản trị còn thiếu 1 mảng lớn |
| **Lõi AI** | Guardrail, RAG, sinh kế hoạch, chấm rủi ro | chạy ngầm | 🟢 Ổn, trừ 1 lỗ tài liệu chưa duyệt |
| **EduSync (Mock LMS)** | Hệ thống ngoài để chứng minh tích hợp | cả 3 role xem, chỉ Admin đồng bộ | 🟢 Vừa được nâng cấp 3 ngày qua |

**Con số thực tế hôm nay:**

- Test: **522 đạt · 4 hỏng · 7 bỏ qua**. 4 cái hỏng đều do 12 file dữ liệu môn học mới thêm dùng sai định dạng — không phải lỗi chức năng.
- Đang có **~2.100 dòng code chưa commit** trong máy, gần như toàn bộ là phần Admin.
- 20 commit gần nhất: ~18 cái là EduSync. Ba ngày qua core không có commit nào.

---

## Phần 2 — Role Admin của bạn đang đứng ở đâu

Admin nối với 2 role kia bằng **4 kiểu khác nhau**. Đây là cách nhìn quan trọng nhất, vì "đồng bộ hay chưa" có 4 câu trả lời khác nhau tuỳ kiểu.

### Kiểu 1 — ĐỌC: xem lại thứ role khác đã làm

Sinh viên → Admin: **13/20 loại dữ liệu đọc được.** Rất tốt.
Giảng viên → Admin: **2/8 loại.** Rất yếu.

### Kiểu 2 — ĐẶT: Admin chỉnh, role khác tự tuân theo

**Đây là mảng bạn làm chắc nhất.** 6/6 chạy thật, không cần sửa gì:

- Chỉnh trọng số rủi ro → cảnh báo của giảng viên đổi theo (có preview, publish, rollback, lưu phiên bản)
- Bật/tắt luật guardrail → câu hỏi sinh viên bị chặn hay không đổi theo
- Đặt học kỳ + lịch thi → kế hoạch và task "ôn thi" của sinh viên đổi theo
- Nạp tài liệu môn → câu trả lời AI cho sinh viên trích nguồn từ đó
- Cấu hình tổ chức, đồng bộ EduSync

### Kiểu 3 — NHẬN VIỆC: hoạt động role khác đẩy việc vào hàng đợi Admin

Hàng đợi có 4 loại việc. **2 loại chạy, 2 loại không bao giờ có việc nào** — vì không nơi nào trong hệ thống tạo ra dữ liệu cho chúng.

### Kiểu 4 — CẤP PHÁT: Admin tạo cái khung role khác hoạt động bên trong

**Chưa có gì. 0%.** Và đây chính là gốc của cảm giác "3 role không đồng bộ".

---

## Phần 3 — Đã liên kết hết chưa? Chức năng đã lấy được dữ liệu chưa?

### 6 mạch đang chạy thật

1. Admin đặt lịch thi → sinh viên nhận task ôn thi
2. Admin chỉnh chính sách rủi ro → giảng viên thấy cảnh báo theo ngưỡng mới
3. Admin nạp tài liệu → sinh viên nhận câu trả lời có trích nguồn
4. Sinh viên xin bộ luyện tập → giảng viên duyệt → sinh viên nhận
5. Sinh viên bật chia sẻ phản tư → giảng viên đọc được (mặc định tắt, đúng nguyên tắc đồng ý)
6. Admin xem hồ sơ 360° của sinh viên (mỗi lần đọc đều ghi nhật ký trước khi trả dữ liệu — chỗ này làm rất đúng)

### 5 mạch bị đứt

**① Sinh viên bị chặn câu hỏi → giảng viên duyệt: không có gì chảy qua.**

Khi AI chặn một câu "làm hộ bài", hệ thống chỉ ghi một dòng log rồi thôi — **không lưu lại sự việc đó vào cơ sở dữ liệu**. Hàng đợi duyệt của giảng viên đọc đúng chỗ, nhưng chỗ đó vĩnh viễn trống. Hiện nó chỉ có dữ liệu khi chạy script tạo dữ liệu mẫu.

Đây là mạch nghiêm trọng nhất, vì nó chạm 2 trong 6 ràng buộc bắt buộc của đề bài: chống lạm dụng "làm hộ bài", và giảng viên tham gia vào vòng quyết định.

**② Giảng viên bấm "Đã can thiệp" → sinh viên không nhận được gì.**

Không thông báo, không tin nhắn, không hiển thị ở đâu bên phía sinh viên. Vòng lặp đóng lại bên trong màn hình của giảng viên.

**③ Tab "Yêu cầu dữ liệu" có màn hình xử lý nhưng không có đường vào.**

Admin có đủ 6 thao tác (xem, duyệt, từ chối, hoàn tất, xem trước khi xoá, xác nhận xoá) — nhưng **không ai trong hệ thống tạo được một yêu cầu**. Không có nút nào cho sinh viên hay giảng viên gửi. Tab này chỉ chạy được nếu ai đó chèn tay vào cơ sở dữ liệu.

**④ Tài liệu chưa duyệt đã vào câu trả lời cho sinh viên.**

Bạn có quy trình 4 bước: Tải lên → Kiểm định → Xuất bản → Lưu trữ. Nhưng thực tế **vừa tải lên là sinh viên trích dẫn được ngay**, chưa cần bấm Kiểm định hay Xuất bản. Bộ lọc phía đọc chỉ loại tài liệu đã Lưu trữ, quên loại bản nháp.

**⑤ Thông báo từ Admin gửi giảng viên: có bên đọc, không có bên gửi.**

Màn hình giảng viên có panel "Thông báo từ Phòng đào tạo", đọc từ một bảng dữ liệu có sẵn. Nhưng không có route nào để Admin ghi vào bảng đó. Panel đó rỗng vĩnh viễn.

---

## Phần 4 — Gốc của "3 role không đồng bộ"

Đây là phần quan trọng nhất, và nó nằm trong lãnh địa của bạn.

### Ai đang tạo ra "lớp học"?

Lớp học và danh sách sinh viên trong lớp là **xương sống** của cả hệ thống. Giảng viên chỉ nhìn thấy sinh viên trong lớp mình phụ trách; mọi cảnh báo, mọi hàng đợi duyệt đều lọc theo đó.

Hai thứ này hiện được tạo ở 6 nơi khác nhau — **không nơi nào là Admin**. Nơi tạo chính là **wizard khai học kỳ của chính sinh viên**.

### Và ai được gán làm giảng viên của lớp đó?

Khi sinh viên tự khai môn, hệ thống chọn giảng viên bằng cách: **lấy giảng viên đầu tiên tìm thấy trong tổ chức.** Không theo môn, không theo phân công, không theo gì cả.

### Chuỗi hậu quả

```
Sinh viên tự khai môn học trong wizard
   → hệ thống tạo lớp, gán cho một giảng viên bất kỳ
      → giảng viên đó thấy sinh viên này trong danh sách lớp và danh sách cảnh báo
         → giảng viên can thiệp cho sinh viên mình không hề dạy
            → Admin không có màn hình nào để sửa lại
```

Đây là lý do thật đằng sau câu hỏi "các role có đồng bộ với nhau không". Không phải do backend rời rạc — mà do **không ai đang giữ vai trò phân công**.

### Admin còn thiếu gì nữa trong nhóm này

| Việc lẽ ra Admin phải làm được | Hiện tại |
|---|---|
| Tạo và sửa lớp học | Không có |
| Gán giảng viên cho lớp | Không có — kể cả khi mời giảng viên mới cũng không chọn lớp được |
| Thêm/bớt sinh viên khỏi lớp | Không có |
| Đặt lại mật khẩu cho người dùng | Không có (tài liệu ghi là có — sai) |
| Gửi thông báo tới giảng viên | Không có |

---

## Phần 5 — Admin đang không nhìn thấy những gì

### Về giảng viên (thiếu 6/8 mảng)

Hiện Admin **không trả lời được** những câu rất cơ bản:

- *"Giảng viên X tháng này có dạy đủ buổi không?"* — nhật ký buổi học không hiện ở đâu
- *"Ai đã mở chặn câu hỏi nào?"* — quyết định mở chặn **không vào nhật ký hệ thống**. Đáng chú ý: hệ thống trả về một trường tên là "auditMetadata" khi giảng viên bấm mở chặn, nhìn như đã ghi nhật ký nhưng thực tế không ghi gì cả.
- *"Quiz nào đang phát hành cho sinh viên?"* — không thấy
- *"Giảng viên đã duyệt bao nhiêu bộ luyện tập?"* — không thấy

Ngoài ra, **can thiệp lẻ của giảng viên cũng không được ghi nhật ký** — chỉ khi can thiệp hàng loạt mới có.

### Về sinh viên (thiếu 7/20 mảng)

Đáng chú ý nhất: **bộ nhớ cá nhân mà AI ghi nhớ về sinh viên** hiện Admin không xem được, kể cả khi xử lý yêu cầu trích xuất dữ liệu cá nhân. Đây là dữ liệu nhạy cảm nhất trong hệ thống.

Và khi **sinh viên tự xoá dữ liệu cá nhân**, hệ thống xoá thật nhưng **không ghi lại là chuyện đó đã xảy ra**. Nếu sau này có khiếu nại, không có gì để đối chiếu.

### Về chi phí và hiệu năng AI

Đề bài yêu cầu ở 3 chỗ (ràng buộc #6, quy định chung mục 4, và PLO 5 — một trong 8 năng lực bị chấm điểm): *"giám sát cơ bản: độ trễ / lỗi / chi phí"*.

Tách 3 vế ra:

| Vế | Tình trạng |
|---|---|
| **Lỗi** | 🟢 Khá ổn — có log, có trạng thái job, có cờ báo suy giảm, có 4 chỉ báo LLM thành công/thất bại |
| **Độ trễ** | 🟡 Chỉ đo được ở tầng HTTP, ghi ra log, không tách được phần AI, không tổng hợp được |
| **Chi phí** | 🔴 Không có số liệu nào |

Lưu ý: load test 1.000 sinh viên hiện chạy với khoá API giả, tức là **không gọi AI thật lần nào** — nó đo web server và cơ sở dữ liệu, không chứng minh được vế "chi phí/độ trễ token".

---

## Phần 6 — Kế hoạch hoàn thiện, chia 5 đợt

Mỗi đợt tự nó đã là sản phẩm chạy được. Dừng sau bất kỳ đợt nào cũng không để lại trạng thái dở dang.

### Đợt 0 — Dọn nhà (làm trước tiên)

Commit 2.100 dòng Admin đang nằm trong máy. Không phải việc mới — nhưng nếu chồng thay đổi mới lên đống chưa commit, sau này không phân biệt được lỗi nào của ai.

**Công sức:** nhỏ · **Đổi gì cho người dùng:** không gì · **Vì sao vẫn làm trước:** an toàn cho mọi đợt sau

---

### Đợt 1 — Nối lại 5 mạch đứt ⭐ ưu tiên cao nhất

| Việc | Mở ra điều gì |
|---|---|
| Ghi lại mỗi lần AI chặn câu hỏi | Hàng đợi duyệt của giảng viên có việc thật · ô tương ứng trong hàng đợi Admin có số · có số liệu "bao nhiêu câu bị chặn" cho báo cáo |
| Chỉ tài liệu đã Xuất bản mới vào câu trả lời | Quy trình 4 bước của Admin trở thành thật, không còn là hình thức |
| Ghi nhật ký 3 hành động đang mất dấu | Admin thấy được: ai mở chặn, ai can thiệp, ai tự xoá dữ liệu |
| Route gửi thông báo tới giảng viên | Panel bên giảng viên hết rỗng |

**Công sức:** nhỏ — phần lớn là vài dòng ở đúng chỗ
**Giá trị:** cao nhất trong toàn bộ kế hoạch. Chạm trực tiếp 2 ràng buộc bắt buộc của đề bài.

> ⚠️ **Một thứ tự bắt buộc bên trong đợt này:** phải gắn "cuộc hội thoại thuộc lớp nào" **trước khi** bật ghi câu hỏi bị chặn. Nếu làm ngược, mọi câu hỏi bị chặn của mọi sinh viên sẽ hiện cho **mọi** giảng viên trong trường — biến một bản vá thành một lỗ rò dữ liệu.

---

### Đợt 2 — Admin quản trị lớp học ⭐ gốc của "không đồng bộ"

| Việc | Kết quả |
|---|---|
| Màn hình quản trị lớp: tạo, sửa, xoá | Admin lần đầu làm chủ được cấu trúc lớp |
| Gán / đổi giảng viên phụ trách | Sửa được việc gán sai |
| Thêm / bớt sinh viên khỏi lớp | Danh sách lớp phản ánh đúng thực tế |
| Bỏ cơ chế "gán giảng viên bất kỳ" | Lớp chưa phân công sẽ **không gán ai**, và tự xuất hiện trong hàng đợi việc của Admin |
| Chọn lớp khi mời giảng viên mới | Giảng viên vào hệ thống là có lớp ngay |
| Đặt lại mật khẩu người dùng | Đúng với thứ tài liệu đang mô tả |

**Công sức:** lớn nhất trong kế hoạch — 1 màn hình mới đầy đủ + backend
**Giá trị:** đây là đợt làm cho câu "3 role đồng bộ" trở thành đúng

> Một mẹo tiết kiệm: thay vì xây thêm màn hình cảnh báo "lớp chưa có giảng viên",
> dùng luôn hàng đợi việc bạn đã có sẵn. Lớp thiếu giảng viên trở thành một dòng
> việc trong hàng đợi, bấm vào là tới đúng chỗ xử lý.

---

### Đợt 3 — Admin nhìn thấy nhiều hơn

| Việc | Trả lời được câu hỏi gì |
|---|---|
| Hồ sơ giảng viên 360° đầy đủ | "GV này dạy đủ buổi chưa, tạo quiz gì, mở chặn câu nào" |
| Hồ sơ sinh viên: thêm bộ nhớ AI, quiz, luyện tập | "Hệ thống đang nhớ gì về sinh viên này" — cần cho yêu cầu trích xuất dữ liệu |
| Đường vào cho yêu cầu dữ liệu cá nhân | Tab "Yêu cầu dữ liệu" có việc thật để xử lý |

**Công sức:** vừa · **Giá trị:** vừa — chủ yếu là hoàn thiện năng lực quan sát

---

### Đợt 4 — Đo chi phí và độ trễ AI

Bắt đầu ghi lại: mỗi lần gọi AI tốn bao nhiêu token, mất bao lâu, có thành công không. Rồi một màn hình Admin đọc số đó.

**Công sức:** vừa — nhỏ hơn tưởng, vì thư viện đang dùng **đã trả sẵn số token** trên mỗi phản hồi, chỉ là hiện đang bị vứt đi ngay tại chỗ nhận.

**Giá trị:** đây là vế duy nhất của PLO 5 đang trống. Ưu tiên **có dữ liệu trước, màn hình sau** — có dữ liệu rồi thì kể cả chưa kịp làm giao diện, một câu truy vấn cũng đủ trả lời khi bảo vệ.

> Lưu ý kỹ thuật: **đừng dùng lại 2 bảng cũ trong cơ sở dữ liệu** (`RAGTrace`, `LLMUsageEvent`).
> Chúng đã bị đóng có lý do ghi trong ADR-017, và thiếu cột thời gian nên không chia
> theo kỳ được. Làm bảng mới.

---

### Đợt 5 — Dọn dẹp cuối

- Sửa 4 test đỏ (chuẩn hoá 12 file dữ liệu môn học mới)
- Dịch 6 nhãn menu bên giảng viên đang là tiếng Việt cứng — bật EN không đổi
- Trạng thái hệ thống của tổ chức A đang bị đỏ vì job hỏng của tổ chức B

**Công sức:** nhỏ · **Giá trị:** cần cho lúc nộp bài và demo

---

## Phần 7 — Nếu thời gian hẹp

**Làm Đợt 0 → 1 → 2 rồi dừng.** Đó là 3 đợt trả lời trực tiếp câu hỏi "3 role đã đồng bộ chưa". Đợt 3-5 là hoàn thiện, đẹp có thì tốt, thiếu vẫn bảo vệ được.

Nếu chỉ làm được **đúng 5 việc**:

1. Ghi lại mỗi lần AI chặn câu hỏi *(mở lại cả một vòng lặp giữa 3 role)*
2. Chỉ tài liệu đã Xuất bản mới vào câu trả lời *(một dòng sửa)*
3. Màn hình quản trị lớp + gán giảng viên *(gốc của vấn đề đồng bộ)*
4. Ghi nhật ký 3 hành động đang mất dấu
5. Bắt đầu ghi số liệu chi phí AI *(dữ liệu trước, giao diện sau)*

---

## Phần 8 — Những thứ cố ý để ngoài kế hoạch

| Việc | Vì sao để ngoài |
|---|---|
| **Cách ly dữ liệu ở tầng cơ sở dữ liệu (RLS)** | Cần thao tác trên Supabase Dashboard, có kế hoạch riêng. Hiện việc cách ly giữa các tổ chức hoàn toàn dựa vào code — chạy đúng, nhưng một chỗ quên lọc là rò |
| **Báo cho sinh viên biết đã được can thiệp** | Đây là **quyết định sản phẩm**, không phải kỹ thuật: có nên cho sinh viên biết mình đang bị đánh dấu rủi ro không? Cần chốt trước khi code |
| **Cho Admin xem ghi chú riêng của giảng viên về sinh viên** | Quyết định về quyền riêng tư, không nên gộp lẫn vào việc kỹ thuật |
| **5 bảng dữ liệu chết trong schema** | Có bảng nhưng không ai đọc/ghi. Xoá hay dùng đều cần quyết định riêng — không gấp |
