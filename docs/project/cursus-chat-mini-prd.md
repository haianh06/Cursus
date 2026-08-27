# Cursus Chat — Mini PRD

## Problem and users

Student users need one private, grounded place to ask about the courses they
are enrolled in, understand Cursus features, and take safe next steps in their
Plan → Do → Reflect workflow. The assistant must be helpful without completing
assessed work, exposing another course's material, or becoming intrusive.

## Product decision

Cursus Chat is a right-side panel launched from a compact floating control. It
uses only a student's enrolled course material, streams friendly Markdown
responses, shows source citations for academic answers, and creates previews
for any write action. A student must explicitly confirm every write.

## In scope

- Enrolled-course Q&A with source name, page/section/slide, excerpt and source
  drawer link.
- Product help, navigation quick actions, plan/task proposals, and reflection
  navigation.
- Private one-week chat history and short-lived memory, export and deletion.
- Academic-integrity and crisis-safety guardrails.
- On-entry, low-interruption reminders in a compact briefing bubble.
- OpenAI-backed streaming with lightweight/strong model routing.

## Out of scope

- Email, browser-push, or SMS reminders.
- Instructor/admin access to raw chat transcripts.
- Clinical, diagnostic, or emergency counselling.
- Direct data mutations without a confirmation action.

## Success criteria

1. No answer can retrieve a course the current student is not enrolled in.
2. All academic answers return at least one server-validated citation, or say
   that no grounded answer is available.
3. Every state-changing assistant action is represented as a preview and is
   idempotently confirmed by the student.
4. Guardrails execute before model invocation and fail closed.
5. Conversation data is hard-deleted after seven days and can be exported or
   deleted early by its owner.
