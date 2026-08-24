# Project Context and Handover Document

This file is the persistent source of truth and handover document across AI development sessions for the AI Learning Companion.

## 1. Project Identity
* **Project Name**: AI Learning Companion
* **Target Users**: FPT University Software Engineering students (MVP focus on 1st and 2nd year students).
* **Secondary Users**: Instructors (Academic supervisors).
* **Core Cycle**: Plan → Do → Reflect.
* **Current Phase**: Frontend MVP Implementation.
* **Current Milestone**: Completed Slice 1 (Foundation) & Slice 2 (Auth & Sync).

---

## 2. MVP Scope

### In Scope
* **Mock Canvas Synchronization**: Imports syllabus, course details, assignments, and deadlines automatically.
* **Weekly Plan Generation**: Builds target learning goals and schedules tasks for a given week using the Planner Agent.
* **Assignment Decomposition**: Automatically slices large programming assignments into progressive daily tasks.
* **Study Session Tracker**: Starts and stops study timers for tasks, calculating actual study durations.
* **Course Document RAG**: Searches textbooks or notes using ChromaDB vector database, returning text snippets and source file citations.
* **Academic Integrity Guardrails**: Identifies direct assignment code requests, replacing them with Socratic prompts and guidance hints.
* **Weekly Reflections**: Evaluates completion metrics, comparing target vs actual study logs, updating student memory.
* **Instructor Dashboard**: Computes class-wide completion rates and lists students under delay warnings.

### Out of Scope
* Automatic grading of student code assignments.
* Direct integration with real Canvas credentials/OAuth (MVP uses tokens & simulated canvas synchronization).
* Multi-tenant hosting for external universities.

---

## 3. Approved Architecture

`STATUS: APPROVED FOR SLICE 1 AND SLICE 2`

* **Frontend Stack**: Next.js 16+ with TypeScript (App Router at `frontend/`).
* **Backend Stack**: FastAPI with Python 3.12.
* **Database**: SQLite (local development with WAL enabled) and PostgreSQL (production).
* **Vector Store**: Local ChromaDB (Persistent storage under data directories).
* **Agent Orchestration**: LangGraph (StateGraph managing routing state).
* **Authentication**: Next.js BFF Session wrapper storing JWT access tokens in an HTTP-only secure cookie, forwarding credentials to FastAPI.

---

## 4. Contract Status

| Contract Artifact | Status | Description |
|---|---|---|
| MVP Scope Contract | Approved | Core capabilities and out-of-scope boundaries. |
| System Design | Approved | Multi-layered folder design (API -> Services -> DB). |
| Database Design | Approved | Declarative ORM models. |
| API Contract | Approved | API endpoint paths, methods, payloads, and role access. |
| Agent Contracts | Approved | Inputs, Outputs, and State variables mapping for nodes. |
| Repository Structure | Approved | Standard file layouts. |
| Delivery Plan | Approved | Phase timelines and slice delivery. |

---

## 5. Repository Map

* **`src/main.py`**: FastAPI entry point.
* **`src/db/models.py`**: SQLAlchemy ORM models.
* **`src/api/`**: Segregated FastAPI routers.
* **`frontend/`**: Next.js workspace containing the complete Client BFF application.
  - `frontend/app/(public)/`: Public auth screens (Login, Register).
  - `frontend/app/(authenticated)/`: Protected dashboards and course directories.
  - `frontend/app/api/auth/`: BFF authentication cookie routes handlers.
  - `frontend/app/api/v1/`: BFF Proxy wildcard routes handlers forwarding commands to FastAPI backend.
  - `frontend/lib/api/client.ts`: Unified API fetch client.
  - `frontend/middleware.ts`: Next.js middleware guards.
* **`tests/`**: Unit and integration test suites.

---

## 6. Work Completed

### Milestone 1 — Database & Core APIs (Mock Canvas & Task Tracking)
* **Status**: Completed and passing.

### Milestone 2 — RAG, Socratic Guardrails & Weekly Reflections
* **Status**: Completed and passing.

### Milestone 3 — Instructor Dashboard & At-Risk Alert Engine
* **Status**: Completed and passing.

### Milestone 4 — Frontend Foundation & Authentication & Course Synchronization (Slice 1 & 2)
* **Files Created/Modified**:
  - Initialized Next.js App Router workspace at `frontend/`.
  - Created client API wrappers in `frontend/lib/api/client.ts`.
  - Built BFF cookie security handlers in `frontend/app/api/auth/` and API Wildcard proxy in `frontend/app/api/v1/`.
  - Created auth views (`/login`, `/register`) and protected dashboards (`/student/dashboard`, `/student/courses`, `/instructor/dashboard`) sharing layout sidebar menus (`ShellLayout`).
* **Decisions**: Utilized Next.js 15+ async `cookies()` resolutions and route parameters promises. Implemented state preservation checks through manual refresh.
* **Tests Executed**: TypeScript compile check (`npx tsc --noEmit`), ESLint check (`npx eslint .`), production compile build (`npm run build`), and Chrome E2E flows via browser automation.
* **Results**: Passed. E2E Chrome test registered student, synchronized Canvas course details (`SWE301`, `SWE402`), verified syllabus readings, logged out, registered instructor, verified warnings statistics (1 flagged at risk), and logged out.

---

## 7. Current Blockers
* **None**: Backend and Frontend Slice 1 & 2 integrations are fully stable.

---

## 8. Next Action
* **Slice 3 — Planner UI**: Build scheduling components, preferred study period inputs, weekly target generators, and approval cards workflows.

---

## 9. Context Update Protocol
Every future development session must update this file under Section 6 (Work Completed) detailing changes, results, and limitations.
