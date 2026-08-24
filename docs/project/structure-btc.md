
# Project Structure — Phần của Ban Tổ Chức (BTC)

Tài liệu này mô tả toàn bộ cấu trúc thư mục/file **do ban tổ chức (BTC) AI20K cung cấp
sẵn** trong template gốc — chưa bị team chỉnh sửa nội dung.

Phân loại dựa trên đối chiếu với **Initial commit** (`4741ab8`) — commit đầu tiên
của repo, chính là snapshot nguyên bản của template BTC trước khi team commit bất kỳ
thay đổi nào. Mọi file nằm trong Initial commit được liệt kê ở đây. Toàn bộ được xác
minh bằng `git cat-file` / `git log --diff-filter=A`, không suy đoán theo tên file.

Xem phần mô tả các file/thư mục do team tự tạo/chỉnh sửa tại
[structure-team.md](structure-team.md).

## Mục lục

- [1.1 Cây thư mục](#11-cây-thư-mục)
- [1.2 File cấu hình cấp cao nhất](#12-file-cấu-hình-cấp-cao-nhất)
- [1.3 `src/` — Backend FastAPI + LangGraph skeleton](#13-src--backend-fastapi--langgraph-skeleton)
- [1.4 `tests/` — Bộ test mẫu](#14-tests--bộ-test-mẫu)
- [1.5 `scripts/` — Hệ thống AI Usage Logging](#15-scripts--hệ-thống-ai-usage-logging)
- [1.6 `.agents/`, `.claude/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/hooks/` — Hook config cho từng AI tool](#16-agents-claude-codex-cursor-gemini-githubhooks--hook-config-cho-từng-ai-tool)
- [1.7 `.github/workflows/` — CI/CD](#17-githubworkflows--cicd)
- [1.8 `docs/archive/guide/` — Giáo trình kỹ thuật 10 chương](#18-docsguide--giáo-trình-kỹ-thuật-10-chương)
- [1.9 `eval/`, `presentation/` — Template deliverable rỗng](#19-eval-presentation--template-deliverable-rỗng)
- [1.10 Các file Markdown template khác](#110-các-file-markdown-template-khác)

---

## 1.1 Cây thư mục

```
P-093/
├── .agents/                        # Rule + workflow cho Antigravity IDE
│   ├── rules/ai-log-hook.md
│   └── workflows/log.md
├── .ai-log/                        # Nơi ghi log AI usage (runtime, rỗng lúc clone)
│   └── .gitkeep
├── .claude/settings.json           # Hook Claude Code
├── .codex/hooks.json               # Hook OpenAI Codex CLI
├── .cursor/hooks.json              # Hook Cursor
├── .gemini/settings.json           # Hook Gemini CLI
├── .github/
│   ├── hooks/hooks.json            # Hook GitHub Copilot
│   └── workflows/ci.yml            # GitHub Actions CI
├── docs/
│   ├── architecture_diagram.md     # Template mermaid diagram rỗng
│   └── guide/                      # Giáo trình kỹ thuật 10 chương + sub-topics
├── eval/results/report.md          # Template báo cáo evaluation, rỗng
├── presentation/README.md          # Hướng dẫn chuẩn bị pitch deck/video demo
├── scripts/                        # Script cài đặt + vận hành AI Usage Logging
├── src/                            # Backend FastAPI + LangGraph skeleton
├── tests/                          # pytest suite mẫu
├── .dockerignore
├── .env.example
├── .gitignore
├── ARCHITECTURE.md                 # Template kiến trúc, rỗng — chưa điền
├── Dockerfile                      # Multi-stage build
├── JOURNAL.md                      # Template nhật ký phát triển, rỗng
├── Makefile                        # Task runner (run/test/lint/format/...)
├── README.md                       # README của template (hướng dẫn dùng cho học viên)
├── README_boilerplate.md           # README mẫu để đội copy đè thành README.md riêng
├── WORKLOG.md                      # Template worklog, rỗng
├── docker-compose.yml              # Orchestration 1 service "backend"
├── requirements.txt                # Dependencies Python
└── ruff.toml                       # Cấu hình lint/format Python
```

## 1.2 File cấu hình cấp cao nhất

| File                             | Vai trò & nội dung chính                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`Dockerfile`**         | Build image 2 stage:**Stage 1 (builder)** cài dependencies từ `requirements.txt` vào `/root/.local` bằng `pip install --user`; **Stage 2 (production)** copy package đã cài từ builder sang image `python:3.11-slim` sạch, tạo user `appuser` non-root, copy code, expose port `8000`, có `HEALTHCHECK` gọi `GET /health` mỗi 30s, entrypoint chạy `uvicorn src.main:app --host 0.0.0.0 --port 8000`.                                                           |
| **`docker-compose.yml`** | Khai báo**1 service duy nhất**: `backend` — build từ `Dockerfile` tại context hiện tại, map port `8000:8000`, đọc biến môi trường từ `.env`, mount volume `./data:/app/data`, `restart: unless-stopped`, healthcheck giống Dockerfile. Không có service database/vector store nào khác — team phải tự thêm nếu cần Postgres/Chroma riêng container.                                                                                                             |
| **`Makefile`**           | 6 target:`run` (uvicorn reload), `test` (`pytest tests/ -v`), `lint` (`ruff check src/ tests/`), `format` (`ruff format src/ tests/`), `typecheck` (`mypy src/`), `check` (chạy lint+format+test liên tiếp), `clean` (xoá `__pycache__`, `.pytest_cache`, `.ruff_cache`).                                                                                                                                                                                                   |
| **`requirements.txt`**   | 3 nhóm:**Core** (fastapi, uvicorn, pydantic, pydantic-settings, python-dotenv), **AI/LangChain** (langchain, langchain-openai, langgraph), **Dev tools** (ruff, pytest, pytest-asyncio, httpx). Nhóm **Database** (sqlalchemy, alembic, psycopg2-binary) và **Vector Store** (chromadb) bị **comment sẵn** — chỉ là gợi ý, chưa cài, team phải tự uncomment khi cần.                                                                                     |
| **`ruff.toml`**          | Target Python 3.11, độ dài dòng tối đa 120. Lint rule bật:`E` (pycodestyle error), `F` (pyflakes), `I` (import sort), `N` (naming), `W` (warning), `UP` (pyupgrade); tắt riêng `E501` (line-too-long, vì đã set line-length riêng). Format: quote kép, indent bằng space.                                                                                                                                                                                                      |
| **`.env.example`**       | Template biến môi trường: LLM key (`OPENAI_API_KEY`, có ghi chú thay bằng `ANTHROPIC_API_KEY`/`GOOGLE_API_KEY`), `DATABASE_URL` (mặc định Postgres, có option SQLite), `CHROMA_PERSIST_DIR` (vector store), app config (`APP_ENV`, `APP_PORT`, `CORS_ORIGINS`), 3 biến LangSmith cho AI tracing (`LANGCHAIN_API_KEY/PROJECT/TRACING_V2` — deliverable #4), và 3 biến do BTC cấp sẵn cho hệ thống chấm điểm (`AI_LOG_SERVER`, `AI_LOG_API_KEY`, `AI_LOG_DIR`). |
| **`.dockerignore`**      | Loại khỏi Docker build context:`.git`, `.env`, venv, cache Python, và toàn bộ `docs/`, `presentation/`, `eval/`, mọi file `*.md` (trừ ngoại lệ `requirements.txt` được include lại) — image production không mang theo tài liệu.                                                                                                                                                                                                                                             |
| **`.gitignore`**         | Chuẩn Python (`__pycache__`, `.venv`, `*.egg-info`) + `.env`, IDE files, `data/` (không commit dữ liệu), `node_modules/`/`.next/` (cho frontend), và đặc biệt: `.ai-log/*.jsonl` + `.ai-log/archive/` bị ignore nhưng **thư mục `.ai-log/` vẫn được track** nhờ `.gitkeep` — giữ cấu trúc, bỏ nội dung log thật.                                                                                                                                        |
| **`ARCHITECTURE.md`**    | Template kiến trúc —**chưa được điền**, toàn bộ là placeholder `[...]`. Có sẵn khung: System Overview, 2 sơ đồ mermaid mẫu (system diagram + agent flow), bảng Component (Frontend/Backend/Agent/DB/Vector Store), Data Flow, Deployment Architecture, Security checklist, bảng Design Decisions.                                                                                                                                                                               |
| **`.env` / secrets**     | Không commit (đã gitignore);`.env.example` là bản mẫu duy nhất trong repo.                                                                                                                                                                                                                                                                                                                                                                                                                         |

## 1.3 `src/` — Backend FastAPI + LangGraph skeleton

Đây là **code mẫu** BTC cung cấp để minh hoạ kiến trúc 3-layer (API → Agent → Service), toàn bộ logic là placeholder chưa nối LLM thật.

```
src/
├── main.py              # FastAPI app entrypoint
├── config.py            # Pydantic Settings — đọc .env
├── api/routes.py        # API endpoints
├── agents/
│   ├── graph.py         # LangGraph StateGraph (nodes + edges)
│   ├── state.py         # AgentState (TypedDict)
│   ├── nodes/example_node.py   # analyze_node, respond_node
│   └── tools/example_tool.py   # search_knowledge, calculate
├── models/schemas.py    # Pydantic request/response schema
└── services/llm.py      # Factory tạo ChatOpenAI client
```

| File                             | Nội dung                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py`                      | Khởi tạo`FastAPI` app với `lifespan` (in log start/stop ra console), gắn `CORSMiddleware` (origin đọc từ `settings.cors_origins`), include `router` từ `api/routes.py` với prefix `/api/v1`, và định nghĩa route `GET /health` trả `{"status": "ok", "env": ...}` — dùng cho Docker healthcheck.                                                                                                            |
| `config.py`                    | Class`Settings(BaseSettings)` của `pydantic-settings`, đọc từ file `.env`. Field gồm app config, LLM (`openai_api_key`, `model_name="gpt-4o-mini"`, `llm_temperature`), `database_url` (mặc định SQLite), `chroma_persist_dir`. Cache bằng `@lru_cache` qua hàm `get_settings()`.                                                                                                                               |
| `api/routes.py`                | 2 endpoint:`POST /chat` (nhận `ChatRequest`, gọi `agent.ainvoke()`, trả `ChatResponse`, bắt `Exception` chung → HTTP 500) và `GET /status` (trả trạng thái tĩnh `{"status": "ready", ...}`).                                                                                                                                                                                                                          |
| `agents/graph.py`              | `build_graph()` dựng `StateGraph(AgentState)` với 2 node `analyze` → `respond`, entry point là `analyze`, có 1 **conditional edge** (`should_continue`) route sang `END` nếu `state["error"]` có giá trị, ngược lại sang `respond`. Compile thành object `agent` module-level, dùng trực tiếp trong `routes.py`.                                                                                  |
| `agents/state.py`              | `AgentState(TypedDict, total=False)` — schema state dùng chung cho toàn graph: `query`, `context`, `analysis`, `response`, `error`, `metadata`.                                                                                                                                                                                                                                                                              |
| `agents/nodes/example_node.py` | `analyze_node`: chỉ nối chuỗi `f"Phân tích: {query}"` (có `# TODO` nhắc thêm logic thật, ví dụ gọi LLM/vector search). `respond_node`: build response từ `analysis`, hoặc trả lỗi nếu `state["error"]` có giá trị. **Không gọi LLM thật ở đâu cả.**                                                                                                                                              |
| `agents/tools/example_tool.py` | 2 tool ví dụ dùng decorator`@tool` của `langchain_core`: `search_knowledge` (placeholder, chưa nối RAG thật), `calculate` — **duy nhất có logic hoàn chỉnh thật sự**: tính biểu thức toán học an toàn bằng cách parse `ast` rồi chỉ evaluate qua bảng `_SAFE_OPERATORS` (không dùng `eval()` trực tiếp, tránh code injection). Cả 2 tool **chưa được bind vào graph/LLM nào**. |
| `models/schemas.py`            | `ChatRequest` (field `message`, validate `min_length=1, max_length=5000`) và `ChatResponse` (`response`, `analysis`).                                                                                                                                                                                                                                                                                                            |
| `services/llm.py`              | `get_llm()` — factory tạo `ChatOpenAI` từ `langchain_openai`, đọc model/key/temperature từ `Settings`. Hàm này **không được import/gọi ở bất kỳ đâu khác** trong codebase (kể cả `example_node.py`) — là điểm nối LLM thật mà team cần tự implement.                                                                                                                                            |

## 1.4 `tests/` — Bộ test mẫu

```
tests/
├── conftest.py                 # Fixtures dùng chung
├── test_agents/test_graph.py   # Test LangGraph agent
└── test_api/test_routes.py     # Test API endpoints
```

- `conftest.py`: fixture `client` (async `httpx.AsyncClient` chạy trực tiếp trên `app` qua `ASGITransport`, không cần server thật) và `mock_llm` (mock sẵn để tránh gọi OpenAI thật khi test, hiện chưa có test nào dùng đến vì chưa có LLM call thật để mock).
- `test_graph.py`: 2 test gọi `agent.ainvoke()` trực tiếp, kiểm tra output có key `response`/`query`.
- `test_routes.py`: 3 test — health check trả 200, chat với message rỗng trả 422 (validation), status endpoint trả 200.
- Toàn bộ 5 test **pass được vì logic phía sau là placeholder** — không có LLM call thật nên không cần mock network.

## 1.5 `scripts/` — Hệ thống AI Usage Logging

Đây là toàn bộ cơ chế BTC dùng để **thu thập log prompt** của học viên (deliverable #4), không phải logic ứng dụng.

| File                                     | Vai trò                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `log_hook.py`                          | Logger dùng chung cho hook của Claude Code/Cursor/Codex/Gemini/Copilot — đọc JSON payload từ stdin, tự nhận diện tool nào gọi (qua`--tool=` arg hoặc heuristic dựa trên shape payload), chuẩn hoá về 1 format chung, append vào `.ai-log/session.jsonl`. Chỉ log khi có payload thật (`prompt`, `tool_input`,...), bỏ qua event rỗng.                                                                                                                                                                                                                  |
| `log_antigravity.py`                   | Riêng cho Antigravity IDE (không có hook API như các tool khác) — quét trực tiếp file transcript trên đĩa (`~/.gemini/antigravity-ide/brain/<conv>/.../transcript.jsonl`), trích các dòng `USER_INPUT` + `USER_EXPLICIT` trong khối `<USER_REQUEST>`, lọc theo repo hiện tại (đối chiếu `Cwd` trong tool call với working directory) và theo cửa sổ thời gian (`--hours`, mặc định 24h), rồi ghi vào `.ai-log/session.jsonl` với `entry_id` để tránh log trùng khi chạy lại. Chạy tự động qua git pre-push hook.          |
| `log_manual.py`                        | Logger thủ công cho tool**không có hook tự động** (ChatGPT, Gemini Web, Claude.ai...) — interactive hoặc CLI args (`--tool`, `--prompt`, `--model`, `--result`), ghi cùng format vào `.ai-log/session.jsonl`.                                                                                                                                                                                                                                                                                                                                              |
| `submit_log.py`                        | Chạy trong git pre-push hook — đẩy`.ai-log/session.jsonl` lên `AI_LOG_SERVER` (đọc từ `.env`) qua HTTP POST, có `Authorization: Bearer <AI_LOG_API_KEY>`. Cơ chế an toàn: rename file thành `session.pending.<timestamp>.jsonl` trước khi đọc (tránh race condition với hook đang ghi tiếp), giới hạn `BATCH_LIMIT=500` entry/lần gửi, thành công thì archive vào `.ai-log/archive/YYYY-MM-DD.jsonl`, thất bại thì gộp lại pending file để thử lại lần push sau — **không bao giờ chặn `git push`** dù server lỗi. |
| `setup_hooks.sh` / `setup_hooks.ps1` | Chạy 1 lần sau khi clone — tự sinh file`.git/hooks/pre-push` (gọi `log_antigravity.py --auto` rồi `submit_log.py`, luôn `exit 0` để không chặn push), tạo `.ai-log/.gitkeep`.                                                                                                                                                                                                                                                                                                                                                                                   |
| `_pyrun.sh` / `_pyrun.cmd`           | Launcher cross-platform tìm Python khả dụng (`python3` → `python` → `py -3` → dò các đường cài Windows phổ biến), bỏ qua Windows Store stub giả. Dùng làm lớp trung gian trong mọi lệnh hook (`bash scripts/_pyrun.sh scripts/log_hook.py ...`) để hook chạy được bất kể máy học viên cài Python kiểu gì.                                                                                                                                                                                                                                  |

## 1.6 `.agents/`, `.claude/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/hooks/` — Hook config cho từng AI tool

Mỗi thư mục là file cấu hình **theo đúng format riêng** của từng AI coding tool, tất cả cùng trỏ về `scripts/log_hook.py` với `--tool=<tên>` khác nhau, chạy ở các event tương ứng (submit prompt / stop / kết thúc session):

| Thư mục                        | Tool                                       | Event hook                                                                                                  |
| -------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `.claude/settings.json`        | Claude Code                                | `UserPromptSubmit`, `PostToolUse`, `Stop`                                                             |
| `.cursor/hooks.json`           | Cursor                                     | `beforeSubmitPrompt`, `stop`                                                                            |
| `.codex/hooks.json`            | OpenAI Codex CLI                           | `UserPromptSubmit`, `Stop`                                                                              |
| `.gemini/settings.json`        | Gemini CLI                                 | `BeforeAgent`, `AfterModel`, `SessionEnd`                                                             |
| `.github/hooks/hooks.json`     | GitHub Copilot                             | `userPromptSubmitted`, `sessionEnd`                                                                     |
| `.agents/rules/ai-log-hook.md` | Antigravity (rule, không phải hook JSON) | Chỉ thị AI**không** được tự gọi script log thủ công — logging đã tự động qua pre-push |
| `.agents/workflows/log.md`     | Antigravity (workflow)                     | Hướng dẫn log thủ công**chỉ** cho web tool không có hook (ChatGPT, Claude.ai...)              |

## 1.7 `.github/workflows/` — CI/CD

`ci.yml` — GitHub Actions job `lint-and-test`, chạy trên `push` vào `main`/`develop` và `pull_request` vào `main`. Các bước: checkout → setup Python 3.11 (cache pip) → `pip install -r requirements.txt` → `ruff check src/ tests/` → `pytest tests/ -v --tb=short` (với env giả `APP_ENV=test`, `OPENAI_API_KEY=test-key`). **Không có** bước build/push Docker image hay deploy — chỉ dừng ở lint + test.

## 1.8 `docs/archive/guide/` — Giáo trình kỹ thuật 10 chương

Giáo trình giảng dạy của BTC (không phải tài liệu thiết kế sản phẩm), gồm `chapter-01.md` → `chapter-10.md` và các sub-topic:

`anti-patterns/`, `architecture/`, `bmad/`, `book-media/free-accounts/` (ảnh hướng dẫn tạo tài khoản free Cohere/Gemini/Groq/HuggingFace/LangSmith/Mistral/Render/Vercel), `code-style/`, `cost-management.md`, `deliverables/`, `devops/`, `free-accounts.md`, `langgraph/`, `patterns/` (RAG), `resources/`, `setup/`, `testing/`, `troubleshooting.md`.

`docs/architecture_diagram.md` là template mermaid diagram mẫu — generic, **chưa customize** cho dự án cụ thể (khác với `ARCHITECTURE.md` ở root, cũng là template rỗng riêng).

## 1.9 `eval/`, `presentation/` — Template deliverable rỗng

- `eval/results/report.md`: template báo cáo evaluation — bảng metric (accuracy, latency, satisfaction, coverage) toàn placeholder, mục test results/user feedback/demo results/action items đều trống.
- `presentation/README.md`: hướng dẫn chuẩn bị pitch deck (10 slide) + video demo (checklist 4 mục) cho Demo Day — chưa có file `pitch_deck.pptx`/`video_demo.mp4` thật nào.

## 1.10 Các file Markdown template khác

- `README.md`: README của **template**, hướng dẫn học viên VinUni AI20K cách dùng (quick start, cấu trúc dự án, 10 chương giáo trình, checklist 10 deliverables, tech stack gợi ý, cơ chế AI logging). Không mô tả sản phẩm cụ thể của team. **Cập nhật 11/08/2026: đã được viết đè thành README thật của Cursus** — nội dung gốc BTC (nguyên văn, không sửa) được giữ lại làm bản đối chiếu tại [`docs/reference/btc-template/README.md`](../reference/btc-template/README.md), theo yêu cầu của nhóm trưởng: giữ mọi file BTC gốc dưới dạng ví dụ/tham chiếu thay vì xoá hẳn khi viết đè.
- `README_boilerplate.md`: README mẫu để đội **copy đè lên `README.md`** và điền thông tin sản phẩm thật. **Cập nhật 11/08/2026:** việc điền đã xong; file mẫu gốc (nguyên văn BTC) được giữ lại tại [`docs/reference/btc-template/README_boilerplate.md`](../reference/btc-template/README_boilerplate.md) thay vì xoá khỏi repo.
- `JOURNAL.md`, `WORKLOG.md`: template nhật ký phát triển / worklog, rỗng, chưa có entry nào (deliverable #8, #9).
