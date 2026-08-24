# Non-Negotiable Engineering and Repository Rules

This document sets forth strict engineering constraints, standards, and workflow rules that must be enforced during all coding operations.

## 1. General Rules
* **No Premature Code**: Do not generate implementation code before the System Design and API Contract are approved by the human reviewer.
* **Scope Restraint**: Do not modify files unrelated to the current target task.
* **Contract Integrity**: Do not modify approved API models, fields, or database contracts without explicit human approval.
* **No Unclear Requirements**: Do not invent missing business logic or parameters. If unsure, stop and ask the user.
* **Verifiable Assertions**: Do not claim tests or builds passed unless they ran and succeeded.
* **No Placeholders**: Do not write comments like `# TODO: implement later` or dummy responses in final commits.
* **Structured Errors**: Avoid catching broad exceptions (`except Exception`) without re-raising or logging them properly.
* **Keep it Simple**: Prioritize simple, demonstrable implementations for the MVP.

## 2. Python Coding Rules
* **Type Hints**: Explicitly type-hint all public functions, methods, parameters, and return types.
* **Python Compatibility**: Use Python syntax compatible with Python 3.12 (as configured in the virtual environment).
* **Descriptive Naming**: Use clear `snake_case` names for variables, methods, and files. Use `PascalCase` for classes.
* **Single Responsibility**: Keep functions short and focused on one task.
* **No Mutable Defaults**: Never use mutable objects (e.g. lists, dicts) as default arguments in function definitions.
* **Pydantic Validation**: Use Pydantic models for all API request payloads and responses. Do not return raw dictionaries at module boundaries.

## 3. FastAPI Rules
* **Controller Isolation**: Route handlers must validate inputs, call service methods, and format output. They must not contain core business logic.
* **Business Logic Segregation**: Core business logic belongs in `src/services/` or use-case structures.
* **Database Injection**: Inject database sessions (`Session` objects) using FastAPI `Depends`.
* **Central Error Handling**: Use centralized exception handlers for standard JSON error responses.
* **Authorization & Access**: Enforce authentication on all protected endpoints. Restrict access checking based on user role (Student vs. Instructor) and ownership.
* **No Client Trust**: Never trust student identifiers supplied by the client without verifying their JWT credentials.
* **No Direct ORM Serialization**: Always serialize ORM models through Pydantic schemas before returning responses.
* **Versioned Paths**: Use `/api/v1` prefixes for all API routes.

## 4. Database & SQLAlchemy Rules
* **SQLAlchemy 2.x Syntax**: Use modern SQLAlchemy query syntax (`select()`, `scalars()`).
* **Explicit Schemas**: Always define primary keys, foreign keys, index bounds, and nullability properties.
* **Avoid N+1 Queries**: Use `joinedload` or `selectinload` when retrieving associated relational entities.
* **Timezone Safety**: Store all timestamps in UTC (`datetime.now(timezone.utc)` or equivalent). Do not use local system timezone.
* **Granular Progress Rules**: Do not store progress attributes globally on assignments; track them strictly inside user-specific progress maps.
* **Granular Enrollment Enforcement**: Access to course materials, plans, and tasks must be validated against enrollment data.
* **Reversible Migrations**: Write database migrations with both `upgrade` and `downgrade` definitions where applicable.

## 5. Security Rules
* **No Committed Secrets**: Never write API keys, passwords, database passwords, or JWT secrets in code or commits. Use env variables.
* **Mask Sensitive Logs**: Never log plaintext passwords, authorization headers, or decrypted course documents.
* **Secure Hashing**: Use bcrypt (locally configured wrapper) to store passwords.
* **File Upload Constraints**: Validate uploaded document size, MIME type, and sanitize filenames to prevent path traversals.
* **Document Retrieval Security**: Validate that the requesting student is actively enrolled in the course hosting the document.
* **Parameterization**: Use ORM statements to defend against SQL Injection.
* **No Exposed Stack Traces**: Hide internal exception traces in production environment responses.

## 6. LangGraph & LLM Rules
* **No Deterministic CRUD**: Never use an LLM to perform simple database creations, updates, or deletions. Use standard SQL commands.
* **Structured Verification**: Always parse and validate LLM outputs using structured Pydantic models before consuming.
* **Deterministic Routing**: Keep state graph transitions predictable, avoiding raw text classification for routing decisions where possible.
* **Fail Safe**: Set token usage limits, request timeouts, and retry parameters.
* **No Hallucinated Citations**: RAG outputs must cite actual chunks retrieved. If evidence is missing, state it clearly.
* **Academic Honesty Gate**: Run Guardrail validation checks on queries before generating answer synthesis.

## 7. RAG Ingestion & Retrieval Rules
* **Metadata Attachment**: Every document chunk must retain its parent document ID, file source, and course ID.
* **Isolated Queries**: Restrict search query scopes strictly by course filter metadata. Never retrieve across course bounds.
* **Grounding Check**: Distinguish retrieved document statements from model inference.
* **Copyright Shielding**: Do not return entire textbook documents or large consecutive sections to students.

## 8. Testing Rules
* **Continuous Testing**: Write tests for all new endpoints, services, or helper functions.
* **Regression Protection**: Include regressions tests for resolved bugs.
* **Mock LLMs**: Mock all OpenAI model invocations during tests to guarantee offline capability.
* **Grounding Tests**: Verify citation correctness in chat pipelines.
* **Regression Suites**: Run the full pytest suite before proposing any completed feature slice.

## 9. Git and File-Change Rules
* **Git Sanitation**: Check Git status and review code diffs after each task.
* **No Unrelated Formatting**: Do not run formatters over files not modified in the task scope.
* **No Force Push**: Prohibit any use of force-pushing.

## 10. Dependency Management Rules
* **Approval First**: Do not add packages to `requirements.txt` without human reviewer authorization.
* **Dependency Checklist**: When proposing a new package, justify it against standard Python libraries and analyze security risks.

## 11. Task Completion Definition
A task is marked completed only when:
1. Implementation conforms strictly to the approved design.
2. All target unit and integration tests run and pass.
3. Code complies with linters and type checkers.
4. Git diff contains only relevant changes.
5. `.ai/context.md` is updated.
