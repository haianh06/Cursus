# Màn "Chi phí AI" — đặc tả triển khai đầy đủ (frontend ↔ backend)

> **Viết:** 27/08/2026 · **Nhánh:** `chung` · **Phạm vi:** vế "chi phí" của PLO 5
> **Mục đích của file này:** đủ để dựng lại toàn bộ tính năng chỉ từ file này + một ảnh chụp màn hình.
> Mọi con số ví dụ bên dưới là **response thật** lấy từ máy dev, không phải bịa cho tài liệu.

---

## 0. Đọc nhanh — tính năng này là gì

Admin mở một màn hình thấy: **mỗi tính năng AI trong hệ thống đã gọi LLM bao nhiêu lần,
tốn bao nhiêu token, tốn bao nhiêu tiền (ước tính), chạy chậm bao lâu, lỗi bao nhiêu phần trăm** —
tách theo từng tính năng, chọn được cửa sổ 7/30/90 ngày, kèm biểu đồ chi phí theo ngày.

Yêu cầu gốc: BTC Quy định chung mục 4 — *"theo dõi tối thiểu độ trễ, lỗi và chi phí"*.
Độ trễ và lỗi đã có từ trước; đây là mảnh **chi phí** còn thiếu.

Việc ghi dữ liệu đã làm xong từ trước (D1+D2, commit `431344e`). Tính năng này chỉ là
**đường đọc** — cộng thêm bảng giá và giao diện.

---

## 1. Luồng dữ liệu — từ lúc gọi LLM tới lúc lên màn hình

```
[11 service gọi LLM]
   plan_builder · planner · weekly_plan · reflection · reflection_engine
   reflection_suggestion · qa_answer · empathic_reply · quiz_generator
   practice_generator · rag_translate_query
        │
        │  tất cả đều đi qua đúng một cửa:
        ▼
   src/services/core/llm.py :: get_llm(feature=..., organization_id=..., user_id=...)
        │  gắn callback vào client LangChain
        ▼
   src/services/core/ai_usage_recorder.py :: AIUsageCallback
        │  on_chat_model_start / on_llm_start  → đánh dấu mốc thời gian theo run_id
        │  on_llm_end                          → ghi 1 dòng, success=True
        │  on_llm_error                        → ghi 1 dòng, success=False, token=0
        ▼
   bảng `ai_usage` (Postgres/SQLite)
        │
        ▼
   src/services/core/ai_usage_service.py :: build_ai_usage_report()
        │  gom SQL theo (feature, model) và (ngày, model)
        │  nhân đơn giá từ ai_pricing.py
        ▼
   src/api/admin_ai_usage.py :: GET /api/v1/admin/ai-usage?days=30
        │
        ▼
   frontend/src/lib/api.js :: getAdminAiUsage(days)
        │
        ▼
   frontend/src/components/admin/AdminAiUsage.jsx
```

**Điểm mấu chốt:** vì mọi lời gọi LLM đều đi qua `get_llm()`, chỉ cần gắn bộ đo ở **một chỗ**
là phủ hết 11 nơi. Đừng sửa 11 service.

---

## 2. Tầng dữ liệu — bảng `ai_usage`

Đã tồn tại từ migration `migrations/versions/20260912_ai_usage.py`. Khai báo ở
`src/db/models.py` (class `AIUsage`):

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | String, PK | |
| `created_at` | DateTime, **có index** | naive UTC (`default=datetime.utcnow`). Mọi truy vấn đều lọc theo kỳ nên bắt buộc có index |
| `organization_id` | String, **nullable**, có index | nullable vì vài chỗ gọi LLM không có ngữ cảnh người dùng |
| `user_id` | String, nullable | |
| `feature` | String, **có index** | nhãn tính năng: `"qa_answer"`, `"weekly_plan"`… — trục nhóm chính của báo cáo |
| `model` | String | tên model thật provider trả về |
| `input_tokens` | Integer, default 0 | |
| `output_tokens` | Integer, default 0 | |
| `latency_ms` | Integer, default 0 | |
| `success` | Boolean, default True | `False` khi lời gọi hỏng — vẫn ghi, vì một lần gọi hỏng vẫn tốn thời gian và vẫn là một lần gọi |

> **Vì sao không tái dùng `RAGTrace` / `LLMUsageEvent`:** ADR-017 đã đóng hai bảng đó.
> `LLMUsageEvent.message_id` là FK NOT NULL trỏ `messages.id`, mà `plan_builder` /
> `reflection_engine` không sinh `Message` nào để gắn vào. Bảng `ai_usage` cố ý
> **không có cột nào bắt buộc trỏ tới hàng khác**.

### ⚠️ Bẫy về múi giờ

`created_at` lưu **naive UTC**. Mốc so sánh trong truy vấn cũng phải naive:

```python
since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)   # ĐÚNG
since = datetime.now(UTC) - timedelta(days=days)                        # SAI — lệch tzinfo
```

Lệch tzinfo **không gây lỗi cú pháp**, chỉ lặng lẽ lọc sai kỳ. Không ai phát hiện được.

---

## 3. Bảng giá — `src/services/core/ai_pricing.py`

File mới. Đây là **chỗ duy nhất** chứa đơn giá.

```python
PRICING_AS_OF: str | None = "27/08/2026"
PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"

# model -> (USD mỗi 1 triệu input token, USD mỗi 1 triệu output token)
PRICES_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-embedding-001": (0.15, 0.0),   # embedding không sinh output token
}
```

### API của module

| Hàm | Trả về |
|---|---|
| `normalize_model(model)` | bỏ tiền tố `"models/"`, hạ chữ thường |
| `price_for(model)` | `(input, output)` hoặc **`None`** nếu chưa khai báo |
| `estimate_cost_usd(model, input_tokens, output_tokens)` | `float` hoặc **`None`** |
| `priced_models()` | danh sách model đã có giá |

### 🔴 Ba quy tắc bất biến — vi phạm là hỏng cả tính năng

**(1) Model không có trong bảng giá thì KHÔNG đoán giá.** Trả `None`.
Con số sai mà trông như số thật còn tệ hơn không có số. Ràng buộc gốc:
`docs/archive/planning-v2/roles/CHUNG_admin.md` mục 2 ý 2 — *"Không tự bịa số liệu"*.

**(2) `None` khác `0.0`.** `0.0` = "đã tính, ra 0 đồng". `None` = "không đủ dữ kiện để tính".
Trộn hai thứ này làm tổng chi phí thấp hơn thực tế mà không có dấu hiệu gì.

**(3) Vì sao là file riêng chứ không nhét vào `config.py`:** ADR-002 ghi bài học của chính
dự án này — *"không hardcode tên/giá model quá lâu mà không có kế hoạch re-verify"*.
Dòng `gemini-1.5-*` trong bản docs đầu tiên đã chết thật chỉ vài tháng sau.
File riêng có `PRICING_AS_OF` ngay đầu file tự nói cho người đọc biết số liệu cũ tới mức nào.

### Ghi chú khi đọc con số

- Đây là giá **bậc trả phí**. Nếu project chạy free tier thì hoá đơn thật là **$0** —
  con số trên màn hình đo *mức tiêu thụ quy theo giá niêm yết*, không phải hoá đơn.
- Google niêm yết hai bậc cho dòng 3.x (tới 31/12/2026 và từ 01/01/2027). Bảng trên lấy
  **bậc hiện tại**. Qua năm phải sửa — đó là lý do `PRICING_AS_OF` tồn tại.
- `gemini-1.5-flash` và `gemini-2.0-flash-lite` (hai fallback khai trong `config.py`)
  **không còn trên trang giá**. Cố ý để trống.

---

## 4. Tầng tổng hợp — `src/services/core/ai_usage_service.py`

### Hằng số

```python
ALLOWED_DAYS = (7, 30, 90)     # không nhận số tuỳ ý, tránh days=100000 quét toàn bảng
DEFAULT_DAYS = 30
```

`days` ngoài danh sách → **rơi về 30**, không báo lỗi 400.

### `build_ai_usage_report(db, *, organization_id, days) -> dict`

**Thuật toán:**

1. Gom SQL theo **`(feature, model)`**, không phải chỉ theo `feature`.
   *Vì sao:* đơn giá phụ thuộc model. Một tính năng có thể chạy trên model chính lẫn
   model fallback trong cùng một kỳ — cộng token của hai model rồi nhân **một** đơn giá là ra số sai.
2. Gập các nhóm `(feature, model)` về từng `feature` ở Python, cộng dồn chi phí đã tính riêng.
3. Sắp xếp theo chi phí giảm dần. Feature **chưa có đơn giá xếp sau** nhóm đã tính được —
   không biết chúng đứng đâu trong thứ tự đó thì đừng xếp bừa.
4. Đếm riêng `unattributed_calls`.
5. Dựng chuỗi ngày qua `_build_daily_series()`.

### `_rate(numerator, denominator)`

```python
if denominator <= 0:
    return None      # KHÔNG phải 0.0
```

Cùng nguyên tắc với `admin_overview_service._metric()`: không có mẫu số thì không có tỷ lệ.
Trả `0.0` sẽ hiện "tỷ lệ lỗi 0%" cho một hệ thống chưa từng gọi LLM lần nào —
một lời khẳng định không có gì chống lưng.

### `_build_daily_series(...)`

Trả về **đủ mọi ngày trong kỳ, kể cả ngày không có lần gọi nào** (`calls: 0`).

> **Vì sao quan trọng:** nếu chỉ trả ngày có dữ liệu, biểu đồ sẽ bóp các cột sát nhau,
> và một khoảng lặng ba ngày trông y hệt ba ngày liên tiếp đều đặn.
> **Số vẫn đúng, nhưng hình nói dối.**

Tương thích 2 hệ CSDL: `func.date()` chạy được cả SQLite lẫn Postgres, nhưng
**SQLite trả chuỗi còn Postgres trả `datetime.date`** — phải xử lý cả hai:

```python
key = row.day if isinstance(row.day, str) else row.day.isoformat()
```

### `_method_note(...)`

Dòng giải thích cách đo, **bắt buộc hiện cạnh mọi số liệu** ở Admin Console
(`CHUNG_admin.md` mục 2 ý 1). Nội dung **đổi theo tình trạng dữ liệu thật**, không phải
câu cố định — câu cố định sẽ nói sai ngay khi bảng giá còn trống.

Ghép từ các mảnh:
- luôn có: *"Chi phí là ƯỚC TÍNH, tính bằng số token đã ghi nhân đơn giá niêm yết theo model, không phải số tiền lấy từ hoá đơn nhà cung cấp."*
- nếu `total_calls == 0`: thêm *"Chưa có lần gọi LLM nào trong kỳ này."*
- nếu có lần gọi thiếu đơn giá **và** bảng giá đã có ít nhất một model: thêm số lượng
- nếu có lần gọi không gắn tổ chức: thêm số lượng

---

## 5. Tầng route — `src/api/admin_ai_usage.py`

```python
router = APIRouter(
    prefix="/admin",
    tags=["admin-ai-usage"],
    dependencies=[
        Depends(require_roles(models.UserRole.ADMIN)),
        Depends(require_permission(Resource.KPI, Permission.READ)),
    ],
)

@router.get("/ai-usage")
def get_admin_ai_usage(
    days: int = Query(DEFAULT_DAYS),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return build_ai_usage_report(db, organization_id=current_user.organization_id, days=days)
```

Route **mỏng**, không tính toán gì — theo đúng cách `admin_overview.py` tách route khỏi service.

Đăng ký ở `src/main.py`:

```python
from src.api.admin_ai_usage import router as admin_ai_usage_router
...
app.include_router(admin_ai_usage_router, prefix="/api/v1")
```

### Phân tách theo tổ chức — và cái bẫy đi kèm

Bảng lọc theo `organization_id == current_user.organization_id`.
Nhưng cột này **nullable** — `qa_answer_service` không giữ session người dùng nên ghi `NULL`.

- Gộp dòng `NULL` vào bảng của một tổ chức = **rò dữ liệu chéo tổ chức**. Không được làm.
- Bỏ hẳn chúng = tổng chi phí thiếu một mảng mà không ai biết.

→ Giải pháp: lọc theo tổ chức như bình thường, **cộng thêm** trường `unattributed_calls`
và nói ra trong `method_note`.

---

## 6. Hợp đồng API — response thật

`GET /api/v1/admin/ai-usage?days=7`

```json
{
  "days": 7,
  "generated_at": "2026-08-27T16:07:01.823772+00:00",
  "by_day": [
    { "date": "2026-08-25", "calls": 0, "est_cost_usd": null },
    { "date": "2026-08-26", "calls": 0, "est_cost_usd": null },
    { "date": "2026-08-27", "calls": 5, "est_cost_usd": 0.026135 }
  ],
  "totals": {
    "calls": 5,
    "input_tokens": 5427,
    "output_tokens": 5884,
    "avg_latency_ms": 22418,
    "error_rate": 0.0,
    "est_cost_usd": 0.026135,
    "calls_without_price": 0
  },
  "by_feature": [
    {
      "feature": "qa_answer",
      "calls": 5,
      "input_tokens": 5427,
      "output_tokens": 5884,
      "avg_latency_ms": 22418,
      "error_rate": 0.0,
      "est_cost_usd": 0.026135,
      "calls_without_price": 0,
      "models": ["gemini-3.6-flash"]
    }
  ],
  "unattributed_calls": 0,
  "pricing": {
    "as_of": "27/08/2026",
    "source": "https://ai.google.dev/gemini-api/docs/pricing",
    "models_priced": ["gemini-3.6-flash", "gemini-embedding-001"]
  },
  "method_note": "Chi phí là ƯỚC TÍNH, tính bằng số token đã ghi nhân đơn giá niêm yết theo model, không phải số tiền lấy từ hoá đơn nhà cung cấp."
}
```

### Trường nào có thể là `null` — và phải hiển thị thế nào

| Trường | `null` khi | UI hiện |
|---|---|---|
| `totals.est_cost_usd` | không có lần gọi nào tính được giá | `—` |
| `totals.avg_latency_ms` | `calls == 0` | `—` |
| `totals.error_rate` | `calls == 0` | `—` |
| `by_feature[].est_cost_usd` | model của feature đó chưa có giá | chữ *"chưa có đơn giá"* |
| `by_day[].est_cost_usd` | ngày đó không tính được giá | cột cao 0 |
| `pricing.as_of` | chưa đối chiếu bảng giá lần nào | đổi hẳn sang câu khác |

**Tuyệt đối không** biến `null` thành `0` ở tầng frontend.

---

## 7. Frontend

### File đụng tới

| File | Việc |
|---|---|
| `frontend/src/components/admin/AdminAiUsage.jsx` | **mới** — toàn bộ panel + biểu đồ |
| `frontend/src/components/admin/adminRoutes.js` | thêm `aiUsage: '/admin/ai-usage'` |
| `frontend/src/components/admin/adminNavigationConfig.js` | thêm mục nav vào nhóm `observe` |
| `frontend/src/components/admin/AdminNavigation.jsx` | thêm icon `Coins` vào `ITEM_ICONS` |
| `frontend/src/components/admin/AdminConsole.jsx` | thêm `<Route path="ai-usage">` |
| `frontend/src/lib/api.js` | thêm `getAdminAiUsage(days)` |
| `frontend/src/locales/vi.js` · `en.js` | 16 khoá mới |

### Nối dây

```js
// adminRoutes.js
aiUsage: '/admin/ai-usage',

// adminNavigationConfig.js — nhóm 'observe', ngay sau 'analytics'
{ to: ADMIN_PATHS.aiUsage, labelKey: 'admin.navAiUsage' },

// AdminNavigation.jsx
import { Coins } from 'lucide-react';
[ADMIN_PATHS.aiUsage]: Coins,

// AdminConsole.jsx
<Route path="ai-usage" element={
  <AdminPage title={t('admin.navAiUsage')} subtitle={t('admin.subtitleAiUsage')}>
    <AdminAiUsage />
  </AdminPage>
} />

// api.js
export function getAdminAiUsage(days = 30) {
  return request(`/admin/ai-usage?days=${encodeURIComponent(days)}`);
}
```

> `AdminTopbarSearch.jsx` dựng chỉ mục tìm kiếm **từ chính `NAV_GROUPS`** — thêm mục nav là
> tự động vào ô tìm kiếm lệnh, không phải khai báo thêm chỗ nào.

### Cấu trúc `AdminAiUsage.jsx`

Bám sát mẫu `AdminAnalytics.jsx` (82 dòng) — **không phát minh pattern mới**:

```jsx
const WINDOWS = [7, 30, 90];

// null/undefined -> '—', giữ nguyên phân biệt "chưa đo được" vs "bằng 0"
function orDash(value, format) {
  return value === null || value === undefined ? '—' : format(value);
}

const formatInt     = (v) => v.toLocaleString();
const formatMs      = (v) => `${v.toLocaleString()} ms`;
const formatPercent = (v) => `${(v * 100).toFixed(1)}%`;
const formatUsd     = (v) => `$${v.toFixed(4)}`;   // 4 chữ số, xem ghi chú bên dưới
```

**Vì sao 4 chữ số thập phân:** chi phí mỗi lần gọi nằm sâu dưới 1 cent. Để 2 chữ số thì
mọi thứ đều hiện `$0.00`. 4 chữ số đọc được số nhỏ mà không ngụ ý độ chính xác mà ước tính
không có.

**Bố cục từ trên xuống:**

1. Tiêu đề + nhóm 3 nút chọn cửa sổ (`aria-pressed`)
2. Hàng 4 ô số: Lần gọi · Chi phí ước tính · Độ trễ TB · Tỷ lệ lỗi
3. Biểu đồ cột chi phí theo ngày
4. Bảng theo tính năng — hoặc empty state nếu `by_feature` rỗng
5. Dòng `unattributed_calls` (chỉ hiện khi > 0)
6. Dòng `method_note` + tình trạng bảng giá

**State và tải dữ liệu:** `useState(days)` + `useCallback(load, [days, lang])` +
`useEffect([load, requestVersion])`. Lỗi → khối `role="alert"` có nút thử lại tăng
`requestVersion`. Đang tải → `<p aria-live="polite">`.

### Biểu đồ — SVG thuần, không thư viện

Repo **không có** `recharts`/`chart.js`/`d3`/`nivo`. Một panel không đáng thêm dependency.

```jsx
const width = 720, height = 120;
const gap = series.length > 45 ? 1 : 2;
const slot = width / series.length;
const barWidth = Math.max(slot - gap, 1);

const value = row.est_cost_usd ?? 0;
const barHeight = value > 0 ? Math.max((value / peak) * (height - 8), 2) : 0;
```

Ba quyết định thiết kế, **giữ nguyên nếu dựng lại**:

1. **Cột, không phải đường.** Dữ liệu có thể chỉ có 1 ngày; đường nối qua 1 điểm ra một chấm
   lơ lửng, đọc như hỏng. Một cột thì đọc đúng.
2. **Sàn 2px cho ngày có gọi.** Ngày có gọi nhưng chi phí cực nhỏ vẫn phải nhìn thấy được,
   nếu không thì "có dùng" và "không dùng" trông giống hệt nhau.
3. **`peak <= 0` → không vẽ**, hiện câu *"Chưa đủ dữ liệu để vẽ biểu đồ theo ngày."*

Mỗi cột có `<title>` làm tooltip gốc của trình duyệt: `2026-08-27 — $0.0261 · 5 lần gọi`.

### Design token — không hardcode màu

Chỉ dùng token của design system: `text-fg`, `text-fg-secondary`, `text-fg-muted`,
`border-line`, `bg-[var(--bg-elevated)]`, `text-accent`, `fill-[var(--accent)]`, `text-danger`.

Nhờ vậy dark mode tự chạy. **Đã đo thật** khi bật `html.dark`:
nền ô số `rgb(26,28,32)`, chữ bảng `rgb(209,213,219)`, viền `rgba(255,255,255,.1)`.

### Responsive

Bảng bọc trong `<div className="overflow-x-auto">` → **bảng tự cuộn, trang không cuộn ngang**.
Đã đo thật:

| Khổ | Kết quả |
|---|---|
| 375px (mobile) | `scrollWidth 375 = clientWidth 375` → trang không trượt ngang; bảng 480px cuộn trong khung 341px |
| 768px (tablet, **spec ghi bắt buộc**) | bảng 718px vừa khít khung 718px |

Đây là hai thứ ô **UX/UI ≥7** thật sự chấm (*"Responsive + dark mode"*,
`08-Cursus-Deliverables-Checklist.md`).

### Khoá i18n (thêm vào cả `vi.js` và `en.js`)

| Khoá | vi |
|---|---|
| `admin.navAiUsage` | Chi phí AI |
| `admin.subtitleAiUsage` | Chi phí, độ trễ và tỷ lệ lỗi của mỗi tính năng gọi AI |
| `admin.aiUsageTitle` | Chi phí AI theo tính năng |
| `admin.aiUsageWindow7` / `30` / `90` | 7 ngày / 30 ngày / 90 ngày |
| `admin.aiUsageTotalCalls` | Lần gọi |
| `admin.aiUsageTotalCost` | Chi phí ước tính |
| `admin.aiUsageAvgLatency` | Độ trễ trung bình |
| `admin.aiUsageErrorRate` | Tỷ lệ lỗi |
| `admin.aiUsageColFeature` … `ColCost` | Tính năng · Lần gọi · Token vào · Token ra · Độ trễ TB · Lỗi · Chi phí ước tính |
| `admin.aiUsageEmpty` | Chưa có lần gọi AI nào trong kỳ này. Dùng thử Trợ lý hoặc tạo một kế hoạch tuần rồi quay lại. |
| `admin.aiUsageNoPrice` | chưa có đơn giá |
| `admin.aiUsageUnattributed` | `{count}` lần gọi không gắn tổ chức, không nằm trong bảng trên. |
| `admin.aiUsagePricingAsOf` | Bảng giá đối chiếu ngày `{date}`. |
| `admin.aiUsageNoPricingConfigured` | Chưa khai báo đơn giá cho model nào, nên cột chi phí còn trống — điền vào `src/services/core/ai_pricing.py`. |
| `admin.aiUsageChartLabel` | Chi phí ước tính theo ngày |
| `admin.aiUsageChartEmpty` | Chưa đủ dữ liệu để vẽ biểu đồ theo ngày. |
| `admin.aiUsageChartCalls` | `{count}` lần gọi |

Nội suy bằng `.replace('{count}', …)` — đúng cách file locale này vốn làm, không thêm thư viện i18n.

---

## 8. Test — `tests/test_api/test_admin_ai_usage.py`

10 test. Mỗi cái khoá một hành vi, không phải test cho có:

| Test | Khoá điều gì |
|---|---|
| `requires_admin_role` | non-admin → 403 |
| `empty_table_returns_zeros_not_an_error` | bảng rỗng → 200, `by_feature: []`, `error_rate: None`, không phải 500 hay bảng trắng |
| `groups_by_feature_and_counts_errors` | gom đúng, `avg_latency_ms` là trung bình có trọng số, `error_rate` đúng |
| `model_without_a_declared_price_reports_null_cost_not_zero` | **quy tắc `None` ≠ `0.0`** |
| `cost_is_computed_when_the_model_has_a_price` | 1M in + 1M out với giá (10, 30) → đúng `40.0` |
| `rows_outside_the_window_are_excluded` | lọc `days` đúng ở cả hai chiều |
| `calls_without_an_organization_are_counted_separately` | dòng `NULL` không lọt vào bảng, nhưng vẫn được đếm |
| `invalid_days_falls_back_to_the_default_window` | `days=100000` → 30, không lỗi |
| `daily_series_covers_every_day_including_empty_ones` | chuỗi ngày đủ 7 phần tử, có ngày `calls: 0` |
| `daily_series_prices_each_day_when_the_model_has_a_price` | chi phí theo ngày tính đúng |

Chạy: `python -m pytest tests/test_api/test_admin_ai_usage.py -q`

---

## 9. Cách chạy và tự kiểm

```bash
# backend
python -m uvicorn src.main:app --port 8000
# frontend
npm run dev --prefix frontend
```

Đăng nhập Admin → sidebar nhóm **Theo dõi** → **Chi phí AI**.

### Bảng rỗng thì làm sao có dữ liệu

Bảng chỉ có dòng khi **thật sự có lời gọi LLM**. Và không phải câu hỏi nào cũng gọi LLM:

`qa_answer_service._needs_llm()` chỉ đẩy sang LLM khi câu hỏi cần tổng hợp
(`tại sao`, `so sánh`, `phân tích`, `giải thích chi tiết`…). Câu tra cứu đơn giản dùng
trích xuất từ tài liệu — **đúng thiết kế**, theo NFR-8 model routing (task đơn giản → không đốt LLM).

Muốn sinh dữ liệu thật, hỏi câu dạng phân tích:

```
"Tại sao cần nắm vững con trỏ trước khi học cấu trúc dữ liệu?"
"So sánh cách đánh giá giữa bài tập cá nhân và bài tập nhóm trong môn này."
```

---

## 10. Hạn chế đã biết

1. **Chi phí là ước tính, không phải hoá đơn.** Token × giá niêm yết. Free tier → hoá đơn thật $0.
2. **Không phải model nào cũng có giá.** Hai fallback trong `config.py` không còn trên trang giá
   Google → hiện *"chưa có đơn giá"*, cố ý không đoán.
3. **Độ trễ đo được có vẻ bị thổi phồng.** Số thật đo được là ~22 giây/lần gọi, bất thường với
   Gemini flash. Nghi `.env` bật `LANGCHAIN_TRACING_V2=true` với khoá không hợp lệ nên mỗi lần
   gọi đều ăn một `403 Forbidden` từ `api.smith.langchain.com`. **Chưa chứng minh được** —
   cần đo lại với tracing tắt.
4. **Free tier giới hạn 20 request/ngày** cho `gemini-3.6-flash`. Rủi ro thật cho buổi quay demo.
5. **Không lưu nội dung prompt/response**, chỉ số đếm. Muốn debug từng lời gọi thì đây không phải chỗ —
   và theo `CHUNG_admin.md` mục 3, Admin Console **cố ý** chỉ ở mức tổng quan vận hành,
   không đi sâu tới mức trace từng request như LangSmith.

---

## 11. Phụ lục — các thay đổi khác trong cùng đợt

| Commit | Nội dung |
|---|---|
| `7f9d7d5` | `RUNNING.md` §2.3 đang bảo chạy `python seed.py` — lệnh đó chắc chắn `NameError` vì `mock_data/` đã bị xoá nguyên thư mục (Phase 1, 20/08). Trỏ sang `seed_demo_accounts.py` + `scripts/seed_curriculum.py` |
| `7ce40a5` | Gỡ tab "Yêu cầu dữ liệu" khỏi nav (không ai tạo được `DataRequest` nên tab luôn trắng; phần `DELETE` lại xoá cả `Enrollment`/`Submission` — rộng hơn spec FR-1.3 cho phép). Route/model/migration **giữ nguyên**. Ghi ADR-021 |
| `ba55e26` | Màn Chi phí AI |
| `7d9633f` | Mục **Known Limitations** trong `README.md` (6 mục) + đóng phạm vi Nhóm C trong `ADMIN_BAN_DO_KET_NOI.md` |
| `57ecfff` | Thêm backend vào `.claude/launch.json` |
| `82df542` | Điền bảng giá Gemini |
| `a256e09` | Biểu đồ chi phí theo ngày |
