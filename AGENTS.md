# AGENTS.md

Repository guidance for agentic coding assistants working in `KITabytes`.

## Scope

- This repo is a two-part app: FastAPI backend in `backend/` and React/Vite frontend in `frontend/`.
- Prefer small, focused changes that match the existing style.
- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` files were found in this repo.
- Use `uv` for Python environment/dependency management.

## Workflow

- Always use red/green TDD for changes.
- Start by writing or updating a failing test that captures the intended behavior.
- Make the smallest code change needed to turn that test green.
- Re-run the relevant test(s) after each change before moving on.
- Prefer adding focused tests for new behavior instead of broad end-to-end coverage first.

## Quick Setup

- Python dependencies live in `backend/requirements.txt`.
- Frontend dependencies live in `frontend/package.json`.
- Python project is managed via `pyproject.toml` with `uv`.

Recommended setup:

```bash
uv venv .venv
uv pip install -r backend/requirements.txt
cd frontend && npm install
```

## Build / Run Commands

Backend:

```bash
uv run uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend && npm run dev
cd frontend && npm run build
cd frontend && npm run preview
```

Full app (typical local flow):

```bash
uv run uvicorn app.main:app --reload --app-dir backend
cd frontend && npm run dev
```

## Test Commands

- Backend tests live in `backend/tests/`.
- Single backend test:

```bash
uv run pytest backend/tests/test_file.py::test_name -q
```

- Single test module:

```bash
uv run pytest backend/tests/test_file.py -q
```

- Frontend is a single HTML file; `cd frontend && npm run build` is the best frontend verification.
- Unified test run (backend): `uv run pytest backend/tests -q`

## Formatting / Linting

- No formatter or linter config is currently checked in.
- If you add linting, prefer low-friction tools that fit the current stack:
  - Python: Ruff for lint/format, plus `pytest`.
  - TypeScript: TypeScript compiler checks plus ESLint if introduced.
- Avoid introducing a new style system unless needed.

## Python Style

- Use snake_case for functions, variables, and module names.
- Use PascalCase for classes and Pydantic models.
- Keep route handlers thin; move logic into `backend/app/services/` or helpers.
- Prefer type hints on public functions and request/response models.
- Use `Optional[...]` or `| None` only when the value is truly nullable.
- Keep helper functions private with a leading underscore when they are file-local.
- Use module docstrings where they already exist; keep new modules similarly documented.
- Raise `fastapi.HTTPException` with the right status code for API failures.
- Prefer early returns over deeply nested branching.
- Keep database access in service/db modules, not in route handlers.
- Use `async`/`await` consistently for I/O-bound backend code.
- Avoid broad `except Exception` unless you re-raise as a controlled API error.

## Python Imports

- Order imports as: stdlib, third-party, local.
- Prefer explicit imports over wildcard imports.
- Keep imports minimal and remove unused ones.
- Match the existing style of local imports in files that defer heavy dependencies.

## Python Error Handling

- Return `404` for missing resources, `500` for unexpected backend failures.
- Preserve useful error messages, but avoid leaking secrets or raw internal context.
- Validate request bodies with Pydantic models instead of manual dict checks.
- Keep API responses stable; avoid changing response shape unless necessary.

## TypeScript / React Style

- Use function components and hooks, as the existing code does.
- Prefer TypeScript strictness; keep types explicit at boundaries.
- Use `interface` for object-shaped props and shared app data when that matches existing files.
- The frontend is a single-file React app in `frontend/index.html` (no `src/` directory).
- Keep UI logic local and simple; lift state only when necessary.
- Use `useCallback`/`useEffect` intentionally, not preemptively.
- Fetch helpers live at the top of `frontend/index.html`.

## TypeScript Imports / Formatting

- Use single quotes.
- Omit semicolons, matching the current frontend codebase.
- Prefer 2-space indentation.
- Group imports as external first, then internal, then type-only imports when practical.
- Keep line wrapping readable rather than forcing compact one-liners.
- Use `type` imports when importing only types.

## Naming Conventions

- Backend files and functions: snake_case.
- Frontend components: PascalCase filenames and component names.
- React props types should end with `Props`.
- API helpers should use verb-first names such as `getDatabaseOverview` and `sendChatMessage`.
- Constants should be uppercase with underscores when they are true constants.

## React / UI Conventions

- Keep components small and composable.
- Preserve the existing dashboard/chat split and the Zwick color system in Tailwind.
- Use Tailwind utility classes consistently; avoid mixing in a new styling approach.
- Keep Markdown rendering and card proposal handling in the chat flow unless there is a strong reason to move it.

## Data / API Conventions

- Frontend API calls go through the proxy at `/api` in `frontend/vite.config.ts`.
- Backend routes are prefixed with `/api/...`.
- Preserve current response fields such as `response`, `tool_calls`, `tests`, and `overview` keys unless a change is intentional.
- Be careful with MongoDB queries; keep filters case-insensitive when matching user-entered text.

## Verification Checklist

- Backend service starts with `uv run uvicorn app.main:app --reload --app-dir backend`.
- Frontend production build succeeds with `cd frontend && npm run build`.
- Any new backend test can be run directly with `uv run pytest path/to/test.py::test_name -q`.
- Avoid leaving the repo in a state that depends on undocumented manual steps.

## When Editing

- Match the surrounding style in each file rather than normalizing the whole repo.
- Avoid unnecessary comments; add them only for non-obvious logic.
- Do not rename public APIs or response shapes casually.
- Do not delete user changes outside the requested scope.
- Follow red/green TDD for every substantive change.
