# How the Database and Backend Work

*2026-03-19T07:32:47Z by Showboat 0.6.1*
<!-- showboat-id: 5bdf6105-a514-4448-87fd-6556e9258967 -->

## What this app is

This repo has a FastAPI backend in `backend/app` and a React frontend in `frontend/`.
The backend is the source of truth for database access, and the frontend calls it through `/api` endpoints.

## Startup flow

1. `backend/app/main.py` creates the FastAPI app, enables CORS, and mounts the route routers.
2. `backend/app/config.py` loads `.env` values and exposes `MONGO_URI`, `MONGO_DB`, and AI API keys.
3. `backend/app/db.py` creates a shared async MongoDB client with Motor.
4. Route handlers call service functions, and service functions read from MongoDB collections.

## Database access

The database connection lives in `backend/app/db.py`.

- `AsyncIOMotorClient(settings.MONGO_URI, tlsAllowInvalidCertificates=True)` creates the async client.
- `db = async_client[settings.MONGO_DB]` selects the database.
- The main collections are:
  - `_tests`
  - `valuecolumns_migrated`
  - `unittables_new`
  - `translations`

The important relationship is:

- `_tests` holds test metadata and parameter fields like `CUSTOMER`, `MATERIAL`, and `TEST_SPEED`.
- `valuecolumns_migrated` holds the actual measurement arrays.
- `metadata.refId` links a value document back to a test `_id`.
- `metadata.childId` ties a value document to a `valueColumns` entry in the test document.

## How queries work

Most data access goes through `backend/app/services/data_service.py`.

- `_build_filter()` turns human-readable filters into MongoDB regex queries.
- `query_tests()` searches `_tests`, counts matches, and returns a compact list of test summaries.
- `get_test_by_id()` returns one test plus its non-`_Key` value column definitions.
- `get_values_for_test()` loads matching documents from `valuecolumns_migrated` using `metadata.refId`.
- `get_summary_table()` returns a preview table for the UI.
- `get_available_metrics()` checks which metrics are actually present before the AI suggests visualizations.
- `get_result_values_for_tests()` extracts a specific named result across tests.

## Route layer

The backend exposes two main route groups.

### `backend/app/routes/data.py`

Direct data endpoints:

- `GET /api/data/tests` -> filtered test search
- `GET /api/data/tests/{test_id}` -> one test
- `GET /api/data/tests/{test_id}/values` -> measurement values
- `GET /api/data/summary` -> compact preview rows

### `backend/app/routes/chat.py`

Chat endpoints:

- `POST /api/chat/send` sends the user message to the AI layer.
- `GET /api/chat/overview` returns database stats for a greeting.
- `POST /api/chat/reset` clears the in-memory conversation history.
- `POST /api/chat/chart-data` turns approved card requests into Plotly-ready payloads.

## AI orchestration

`backend/app/services/ai_service.py` is the coordination layer for the assistant.

- It defines the tool list the model can call.
- It routes tool calls to the data/service functions.
- It supports Gemini, Anthropic, and OpenAI, using whichever API key is configured first.
- It keeps the system prompt strict: show a preview first, confirm the dataset, then suggest only metrics that exist.

## Typical request flow

For a normal data question:

1. The frontend sends a chat message to `/api/chat/send`.
2. `chat_with_ai()` in `ai_service.py` chooses the model provider.
3. The model may call `get_summary_table()` or `query_tests()`.
4. After the user confirms the dataset, the model can call `get_available_metrics()`.
5. If the user approves a visualization, `chart-data` builds the chart payload from MongoDB data.

## Practical takeaway

If you want to understand the backend quickly, read these files in order:

1. `backend/app/main.py`
2. `backend/app/config.py`
3. `backend/app/db.py`
4. `backend/app/services/data_service.py`
5. `backend/app/routes/data.py`
6. `backend/app/routes/chat.py`
7. `backend/app/services/ai_service.py`

`DATABASE_STRUCTURE.md` is the best companion doc for the exact MongoDB schema.
