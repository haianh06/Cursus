# Thumbnail Cursus — Bộ nguyên liệu & prompt sẵn dùng

> Mọi thông số dưới đây lấy trực tiếp từ repo (`frontend/src/index.css`, `frontend/index.html`, `frontend/public/`), không phải gợi ý chung chung. Dán nguyên khối "Brand block" vào bất kỳ model sinh ảnh nào là ra đúng nhận diện Cursus.

---

## 1. Chốt trước: thumbnail này dùng ở đâu

Bốn chỗ dự án đang cần ảnh bìa, và cả bốn **dùng chung một thiết kế**, chỉ khác tỷ lệ cắt:

| Dùng ở đâu | Kích thước | Deliverable | Trạng thái |
|---|---|---|---|
| Thumbnail video demo YouTube | **1280×720** (16:9), < 2 MB | #6 Video Demo | 📝 chưa có |
| Slide bìa Pitch Deck | 1920×1080 | #7 Pitch Deck | 📝 chưa có |
| OG image của Live URL | 1200×630 | #5 Live URL | ✅ đã có (`frontend/public/og-image.png`) |
| GitHub social preview | 1280×640 | #1 Source Code | 📝 chưa có |

**Cách làm tiết kiệm nhất:** thiết kế **một bản master 1920×1080**, để nội dung quan trọng nằm gọn trong vùng an toàn giữa khung (chừa mép trên/dưới ~8%), rồi export ra 4 kích thước. Không thiết kế lại 4 lần.

---

## 2. Nguyên tắc quyết định mọi thứ

Thumbnail YouTube hiển thị thật ở khoảng **210×118 px** trên feed điện thoại. Ở kích thước đó:

- Chữ nhỏ hơn ~60px (trên bản 1280×720) **biến mất hoàn toàn** → headline tối đa **4–6 từ**, cỡ 90–140px.
- Chi tiết nhỏ (bảng số liệu, dòng code, icon 24px) thành vệt xám → bỏ hết.
- Chỉ còn đọc được: **1 nhân vật + 1 câu chữ + 1 mảng màu**. Đừng cố nhồi thêm.
- Góc dưới phải bị **timestamp của YouTube đè lên** → không đặt logo hay chữ ở đó.

Và quan trọng nhất:

> **Không bắt AI vẽ chữ tiếng Việt.** Model sinh ảnh viết sai dấu gần như 100% ("Khöng bja", "trich nguön"). Quy trình đúng: **AI sinh phần nền + mascot → gắn chữ bằng Canva/Figma/PowerPoint.** Mọi prompt dưới đây đều đã có câu yêu cầu chừa chỗ trống cho chữ.

---

## 3. Brand block — dán vào MỌI prompt

Đây là khối mô tả nhận diện Cursus, copy nguyên văn:

```
BRAND PALETTE (use these exact hex values):
- Primary brand blue: #2468C9
- Deep navy ink: #090D16
- Warm off-white background: #FAF9F5
- Soft elevated surface: #F1EFEA
- Accent green (success/"Do"): #059669
- Indigo (planning/citation): #4F46E5
- Violet (reflection): #6D28D9
- Warm gold highlight: #D97706

MASCOT "CURI" (must match exactly):
A small chibi-proportioned 3D robot with a rounded matte off-white plastic body
and visible panel seams. Large round friendly black eyes with soft highlights,
wearing thin dark round eyeglasses. Mint-green over-ear headphones as ears.
A bright green hexagon emblem glowing softly on its chest. Soft blue accents at
the joints. Small warm smile. Stubby arms and legs. Clean studio lighting,
soft shadows, no harsh reflections.

STYLE: modern edtech SaaS, calm and premium, in the visual language of Linear /
Stripe / Notion. Warm off-white base, generous negative space, soft ambient
shadows. NOT neon, NOT cyberpunk, NOT dark-mode sci-fi.
```

**Tài sản đã có sẵn trong repo** (dùng làm ảnh tham chiếu / ghép trực tiếp, khỏi sinh lại):

| File | Là gì |
|---|---|
| `frontend/public/cursus-bot-cutout.png` | Mascot Curi 1024×1024, nền trắng — upload làm reference image |
| `frontend/public/favicon.svg` | Logo mark chữ "C" hở, gradient `#06b6d4 → #3b82f6 → #6366f1` |
| `frontend/public/og-image.png` | Bản OG hiện tại — tham chiếu tone chữ |
| `frontend/public/media/hero/cursus-hero-day-poster.webp` | Style minh hoạ 2D của landing page |

**Font:** Geist (headline) + Inter (phụ đề) — cả hai miễn phí trên Google Fonts, đúng font đang chạy trong `frontend/index.html`.

---

## 4. Cấu trúc một prompt tốt (template 7 khối)

Sinh ảnh ra kết quả ổn định khi prompt đi theo thứ tự này:

```
[1] Định dạng + tỷ lệ      → "16:9 YouTube thumbnail, 1280x720"
[2] Chủ thể chính          → Curi đang làm gì
[3] Bối cảnh / đạo cụ      → panel UI, syllabus, lịch tuần
[4] Bố cục + VÙNG CHỪA CHỮ → "left 45% must stay clean and empty"
[5] Bảng màu (dán hex)     → Brand block ở mục 3
[6] Ánh sáng + phong cách  → soft studio light, flat premium SaaS
[7] Loại trừ               → "no text, no letters, no watermark…"
```

Khối [4] là khối quyết định thumbnail dùng được hay không — thiếu nó thì AI vẽ kín khung, không còn chỗ đặt headline.

---

## 5. Bốn prompt sẵn dùng

Viết bằng tiếng Anh vì model sinh ảnh hiểu tiếng Anh ổn định hơn nhiều.

### 🅰️ Prompt A — "Curi và câu trả lời có trích nguồn" ⭐ khuyến nghị

Đây là hướng bám sát nhất giá trị lõi của sản phẩm: **AI không bịa, có trích nguồn.**

```
A 16:9 YouTube thumbnail, 1280x720, for an educational AI product called Cursus.

SUBJECT: On the RIGHT side of the frame, a small chibi-proportioned 3D robot
mascot with a rounded matte off-white plastic body and visible panel seams.
Large round friendly black eyes with soft highlights, wearing thin dark round
eyeglasses. Mint-green over-ear headphones as ears. A bright green hexagon
emblem glowing softly on its chest. Soft blue accents at the joints, small warm
smile, stubby arms. It is gesturing confidently toward a floating translucent
user-interface card beside it.

PROPS: The floating UI card is a clean white rounded rectangle with a soft
shadow, showing three simple stacked task rows and, below them, two small
rounded indigo "source citation" chips. Behind it, one semi-transparent open
textbook page floats, connected to the card by a thin glowing indigo line —
suggesting the answer is traced back to a real document. Keep every element
large and simple; no readable text anywhere.

COMPOSITION: The LEFT 45% of the frame must remain completely clean and empty —
a smooth warm off-white surface with nothing on it, reserved for a headline that
will be added later. Do not place any object, shadow, or decoration there.

PALETTE: primary brand blue #2468C9, deep navy ink #090D16, warm off-white
background #FAF9F5, indigo #4F46E5 for the citation chips, accent green #059669,
soft elevated surface #F1EFEA.

STYLE: modern edtech SaaS, calm and premium, in the visual language of Linear
and Stripe. Soft ambient studio lighting from the upper left, gentle drop
shadows, generous negative space, crisp clean edges. NOT neon, NOT cyberpunk,
NOT dark sci-fi.

EXCLUDE: no text, no letters, no numbers, no typography, no watermark, no logo,
no busy background patterns, no glowing circuit boards, no brain imagery, no
binary code, no lens flare, no stock-photo humans.
```

**Chữ gắn sau vào khoảng trống bên trái:**
> **KHÔNG BỊA.**
> **CÓ TRÍCH NGUỒN.**

---

### 🅱️ Prompt B — "Trước / Sau" (dễ đọc nhất ở cỡ nhỏ)

Kể nguyên câu chuyện problem → solution chỉ bằng bố cục. Rất mạnh trên feed YouTube.

```
A 16:9 YouTube thumbnail, 1280x720, split vertically into two contrasting halves
by a clean soft diagonal seam.

LEFT HALF — "before": a chaotic desk seen from above, cluttered with overlapping
sticky notes, scattered loose papers, a tangle of open notebooks and an
overflowing stack of textbooks. Desaturated muted grey-beige tones, slightly
cooler and flatter lighting, a subtle feeling of overwhelm. Keep shapes large
and simple, nothing readable.

RIGHT HALF — "after": the same desk, now calm and ordered. A single clean white
floating UI card with three neatly stacked task rows and a soft green completion
checkmark. Beside it stands a small chibi 3D robot mascot: rounded matte
off-white body, large round friendly eyes, thin dark round eyeglasses,
mint-green over-ear headphones, a glowing bright green hexagon on its chest,
small warm smile. Warm off-white lighting, airy and organised.

COMPOSITION: keep the upper-centre band of the frame free of detail so a
headline can be added later. Nothing important in the bottom-right corner.

PALETTE: right half uses warm off-white #FAF9F5, brand blue #2468C9, accent
green #059669, deep navy ink #090D16. Left half is a muted desaturated version
of the same warm neutrals.

STYLE: modern edtech SaaS illustration, calm and premium, soft ambient shadows,
crisp clean edges, generous negative space. NOT neon, NOT cyberpunk.

EXCLUDE: no text, no letters, no numbers, no typography, no watermark, no arrows,
no human faces, no glowing circuit boards, no lens flare.
```

**Chữ gắn sau vào dải trống phía trên:**
> **TỪ DEADLINE DỒN → KẾ HOẠCH TUẦN**

---

### 🅲 Prompt C — "Vòng Plan → Do → Reflect" (hợp slide bìa & OG image)

Tối giản, trang trọng, hợp Pitch Deck hơn YouTube.

```
A 16:9 hero image, 1920x1080, minimal and premium, for an AI study-companion
product.

SUBJECT: Centred composition. Three large softly-glowing rounded nodes arranged
in a wide circular loop, connected by smooth tapering arrows that flow clockwise.
The first node is indigo #4F46E5 and holds a simple calendar glyph. The second
node is green #059669 and holds a simple checkmark glyph. The third node is
violet #6D28D9 and holds a simple circular-arrow glyph. The glyphs are minimal,
geometric and iconic — no text, no labels.

At the centre of the loop, small and calm, stands a chibi 3D robot mascot:
rounded matte off-white body with visible panel seams, large round friendly
eyes, thin dark round eyeglasses, mint-green over-ear headphones, a glowing
bright green hexagon emblem on its chest, small warm smile.

COMPOSITION: keep a clean empty band across the bottom third of the frame for a
headline and subtitle to be added later. Symmetrical, balanced, lots of breathing
room around the loop.

PALETTE: warm off-white background #FAF9F5, deep navy ink #090D16, brand blue
#2468C9, indigo #4F46E5, green #059669, violet #6D28D9.

STYLE: flat vector-leaning illustration with subtle depth, modern SaaS design
system aesthetic in the visual language of Linear and Stripe. Soft ambient
shadows, no gradients heavier than a gentle tint. NOT neon, NOT 3D-render heavy,
NOT cyberpunk.

EXCLUDE: no text, no letters, no numbers, no typography, no watermark, no
brain imagery, no neural networks, no circuit boards, no glowing particles.
```

**Chữ gắn sau vào dải trống dưới:**
> **CURSUS** — Plan · Do · Reflect
> *Trợ lý học tập AI có trích nguồn*

---

### 🅳 Prompt D — "Bàn học ấm" (đồng bộ 100% với landing page)

Dùng khi muốn thumbnail trông y hệt hero art đang chạy trên web — điểm cộng về tính nhất quán khi giám khảo mở cả video lẫn Live URL.

```
A 16:9 illustration, 1280x720, in a soft flat 2D storybook style with thin dark
linework and warm muted colours.

SCENE: A cosy student bedroom desk in warm afternoon light. A university student
in a green hoodie and glasses sits at a wooden desk, seen from behind at a
three-quarter angle, working on an open laptop. On the laptop screen is a clean
minimal weekly planner grid with soft blue accents. Beside the laptop sits a
tiny white robot figurine companion with round blue eyes and a soft smile.
Around the desk: potted plants with trailing leaves, a small stack of books, a
warm brass desk lamp, a mug, a wooden shelf, and a window on the right showing
soft sunlight over a distant city.

COMPOSITION: keep the LEFT THIRD of the frame — the plain wall area — clean and
uncluttered, reserved for a headline to be added later. Warm and calm mood.

PALETTE: warm cream wall #FAF9F5, muted terracotta and olive-green accents, soft
blue #2468C9 on the screen elements, deep navy ink #090D16 for the linework.

STYLE: soft flat 2D vector illustration, thin consistent dark outlines, gentle
cel shading, warm muted palette, cosy and inviting. NOT photorealistic, NOT 3D
render, NOT anime.

EXCLUDE: no text, no letters, no readable screen content, no watermark, no
harsh shadows, no neon.
```

**Chữ gắn sau vào mảng tường trống bên trái:**
> **HỌC CÓ KẾ HOẠCH.**
> **KHÔNG HỌC MÒ.**

---

## 6. Chữ overlay — chọn 1, đừng ghép

Headline phải nói **điểm khác biệt**, không nói **tên loại sản phẩm**. "Trợ lý học tập AI" thì ai cũng có; "không bịa, có trích nguồn" mới là thứ chỉ Cursus dám ghi.

| Phương án | Chữ | Hợp với | Số từ |
|---|---|---|---|
| **1** ⭐ | **KHÔNG BỊA.**<br>**CÓ TRÍCH NGUỒN.** | Prompt A | 4 |
| 2 | **AI ĐỌC ĐÚNG**<br>**SYLLABUS CỦA BẠN** | Prompt A, D | 5 |
| 3 | **TỪ DEADLINE DỒN**<br>**→ KẾ HOẠCH TUẦN** | Prompt B | 5 |
| 4 | **PLAN · DO · REFLECT** | Prompt C | 3 |
| 5 | **HỌC CÓ KẾ HOẠCH.**<br>**KHÔNG HỌC MÒ.** | Prompt D | 5 |

**Quy cách chữ (bản 1280×720):**

- Headline: **Geist Bold / Extrabold**, 100–130px, màu `#090D16`
- Nhấn 1 cụm bằng brand blue `#2468C9` — đúng cách og-image hiện tại đang làm
- Phụ đề (nếu có): **Inter Medium**, 38–44px, màu `#334155`
- Logo Cursus: góc **trên-trái**, cao ~56px (tránh góc dưới-phải vì timestamp)
- Dòng danh tính nhỏ góc trên-phải: `Group06 · Team093 · AI20K Build Phase`, Inter 24px, `#64748b`

---

## 7. Negative prompt dùng chung

Dán vào ô negative prompt (Midjourney: sau `--no`):

```
text, letters, words, typography, numbers, watermark, signature, logo,
garbled text, glowing neural network, brain, circuit board, binary code,
matrix rain, neon, cyberpunk, dark background, lens flare, bokeh particles,
stock photo people, extra fingers, distorted hands, cluttered composition,
busy background, low contrast, jpeg artifacts
```

Midjourney thêm tham số: `--ar 16:9 --style raw --stylize 150`

---

## 8. Nên dùng model nào

| Model | Điểm mạnh cho việc này |
|---|---|
| **Gemini / Nano Banana** ⭐ | Nhận ảnh tham chiếu — upload `cursus-bot-cutout.png` rồi bảo "giữ đúng con robot này" → mascot khớp 100%. Team đã có `GOOGLE_API_KEY` sẵn trong `.env`. |
| **Ideogram** | Model duy nhất viết chữ tương đối đúng — nhưng vẫn đừng giao tiếng Việt có dấu cho nó. |
| **Midjourney v7** | Đẹp nhất về mặt thẩm mỹ, nhưng khó ép chừa vùng trống; cần thêm `--ar 16:9` và vài lần lặp. |
| **ChatGPT / GPT Image** | Bám prompt dài rất tốt, hiểu yêu cầu "chừa 45% bên trái" chuẩn nhất. |

Gắn chữ sau: **Canva** (nhanh, có sẵn Geist/Inter) hoặc **Figma** (chuẩn pixel, export được cả 4 kích thước từ 1 frame).

---

## 9. Checklist nghiệm thu

Trước khi coi là xong, kiểm 7 mục:

- [ ] Thu nhỏ ảnh về **210×118 px** — vẫn đọc được headline và nhận ra mascot?
- [ ] Chuyển sang **đen trắng** — chữ còn tách khỏi nền không? (kiểm tra tương phản thật)
- [ ] Góc **dưới-phải** trống (chỗ YouTube đè timestamp)?
- [ ] Headline **≤ 6 từ**, dấu tiếng Việt đúng, không lỗi font?
- [ ] Màu chủ đạo là **`#2468C9` + `#FAF9F5`** — cùng hệ với Live URL và og-image?
- [ ] Mascot khớp với `cursus-bot-cutout.png` (kính tròn, tai nghe xanh mint, lục giác xanh ngực)?
- [ ] File **< 2 MB**, định dạng JPG hoặc PNG?

---

## 10. Việc cần làm, theo thứ tự

1. Chọn 1 trong 4 prompt (khuyến nghị **A** cho video demo, **C** cho slide bìa).
2. Upload `frontend/public/cursus-bot-cutout.png` làm ảnh tham chiếu mascot.
3. Sinh 4 biến thể, chọn bản có vùng trống sạch nhất.
4. Đưa vào Figma/Canva ở khung **1920×1080**, gắn headline + logo + dòng team.
5. Export: `1280×720` (YouTube), `1920×1080` (deck), `1280×640` (GitHub), `1200×630` (OG — cân nhắc thay bản cũ cho đồng bộ).
6. Lưu vào `presentation/` và cập nhật `README.md` mục 10 Deliverables.

---

*Nguồn dữ liệu nhận diện: `frontend/src/index.css` (design tokens), `frontend/index.html` (font + OG meta), `frontend/public/` (mascot, logo, hero art). Cập nhật file này nếu design system đổi.*
