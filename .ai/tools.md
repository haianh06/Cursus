# AI Tool Permissible Usage Guide

This document defines rules, conditions, and boundaries for tool execution within the "AI Learning Companion" workspace.

## 1. Grounded Available Tools

The following tools are actually available in the current development environment:

### Repository and Filesystem Tools
* **`view_file`**
  * *Purpose*: Read text or inspect images/PDF files.
  * *Allowed*: Reading up to 800 lines of source code or configs.
  * *Prohibited*: Writing edits or modifications.
* **`grep_search`**
  * *Purpose*: Ripgrep-based text searches across files.
  * *Allowed*: Finding variable names, imports, or API pathways.
  * *Prohibited*: Modifying files.
* **`list_dir`**
  * *Purpose*: Checking subdirectory contents.
  * *Allowed*: Inspecting project layout and listing folder trees.
* **`write_to_file`**
  * *Purpose*: Creating new files or completely overwriting existing ones.
  * *Allowed*: Creating configuration scripts, documentation, and tests.
  * *Prohibited*: Modifying existing codebase files when a minor edit is sufficient (use replacement tools instead to minimize risk).
* **`replace_file_content`** / **`multi_replace_file_content`**
  * *Purpose*: Modifying targeted contiguous or non-contiguous blocks of an existing file.
  * *Allowed*: Code edits, bug fixes, config adjustments.
  * *Prohibited*: Swallowing unedited lines or making parallel calls on the same file.

### Terminal Tools
* **`run_command`**
  * *Purpose*: Execute shell commands (Powershell).
  * *Allowed*: Running tests (`pytest`), linters (`ruff`), checking active Python dependencies, starting the development server.
  * *Prohibited*: Running destructive deletion commands (`rm -rf`, `del /s /q`), modifying Git history, force-pushing, or running unverified external binaries.
  * *Preconditions*: Ensure working directory (`Cwd`) is within the project root.

### External Tools
* **`search_web`** / **`read_url_content`**
  * *Purpose*: Fetch external documentation or packages details.
  * *Allowed*: Searching documentation for FastAPI, SQLAlchemy 2.x, LangGraph, or ChromaDB.
  * *Prohibited*: Submitting student homework files, course contents, or sensitive API keys to external index search queries.

---

## 2. Tool Safety and Restriction Rules

The AI assistant must strictly adhere to the following safety constraints:
1. **Destructive Action Ban**: Never propose or run commands to delete files outside the workspace, force-reset Git history, or force-push commits.
2. **Secret Leak Prevention**: Never log, print, or store passwords, database credentials, JWT secrets, or mock API keys.
3. **Infrastructure Isolation**: Never attempt to modify production databases, cloud configurations, or remote deployment pipelines.
4. **Verifiable Completion**: Never report that a command succeeded without inspecting and quoting its execution logs/output.
5. **No Hallucinated Tools**: Do not invent commands, integrations, or environment variables. If a required tool is not available in the API list, report this limitation to the human reviewer immediately.

---

## 3. Dependency Installation Protocol

Installing a new package requires explicit human approval. When suggesting a dependency, the AI must provide:
* **Package Name**: (e.g. `python-multipart`).
* **Exact Purpose**: Why it is needed.
* **Existing Alternatives**: What is already installed in `requirements.txt` that could serve the same purpose.
* **Maintenance Risk**: Star counts, last release dates, or open issues.
* **Security Implications**: Risk of remote code executions, malicious dependencies.
* **Runtime Impact**: Memory usage, initialization cost.
* **Human Approval Request**: A clear prompt asking the user for authorization before adding it to `requirements.txt` or executing `pip install`.
