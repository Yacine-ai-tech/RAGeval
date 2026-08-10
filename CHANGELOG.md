# Changelog

## [0.1.15] - 2026-08-10
### Added
- Multi-judge consensus now requires ≥2 configured judges; raises (HTTP 503 from
  `/eval/log|score`) instead of silently scoring on 0–1 judges. Removed the per-judge
  `litellm` `fallbacks=` swap — a judge is used as configured or skipped, never
  substituted for a different model.
- pgvector embedding storage for the Postgres production tier (`query_embedding`
  column + HNSW index, migrated via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` so it
  applies to existing deployments, not just fresh ones).
- `dspy_compile_callback` / `log_dspy_run` promoted to the public `rageval` package
  API, with real persistence tests (previously present but uncalled from anywhere).
- Live dogfooding: IntelAI's chatbot now logs every persona chat reply to a configured
  RAGeval-compatible evaluator in the background (generic `RAG_EVALUATOR_URL`
  contract, opt-in, never blocks the chat response).
### Fixed
- Removed the Cohere/Jina hosted-embeddings backstop — embeddings are now strictly
  local (`USE_LOCAL_EMBEDDER`) or a generic, provider-agnostic remote endpoint
  (`INFERENCE_MODE=remote` + `EMBEDDING_ENDPOINT`), no vendor-specific fallback chain.
- `CORS_ALLOWED_ORIGINS` in `.env.example` no longer points at a sibling project's
  production domain (was a copy-paste leftover).
- `TELEMETRY_URL` is now documented under its actual variable name (`.env.example`
  previously listed `TELEMETRY_ENDPOINT`/`OMNI_TELEMETRY_ENDPOINT`, neither of which
  the code reads).
- README Quick Start now installs from public PyPI directly instead of a private
  package index, despite the package already being live on public PyPI.
- `requirements.txt` (what the Dockerfile actually installs) was missing
  `google-genai` (Gemini judge) and `psycopg2-binary` (Postgres) — both silently
  non-functional in the deployed container until now.
- Test suite: SQLite-mode tests were silently writing to the real configured
  `POSTGRES_URL` instead of a temp file, because the isolation helper only patched
  `RAGEVAL_DB_PATH`. Fixed via a shared `sqlite_store` fixture that also forces
  `POSTGRES_URL` empty and reloads `rageval._compat` (the settings module `store.py`/
  `evaluator.py` actually read — reloading only `core.config` had no effect on it).

## [0.1.12]–[0.1.14]
Published to PyPI; no corresponding version-bump commit found in this repo's git
history between the 0.1.11 bump and the current HEAD at the time of this audit —
noting the gap rather than guessing at unrecorded changes.

## [0.1.11]
### Added
- Zero-trust Postgres endpoint architecture; anonymous per-session demo isolation for
  eval logs (`DEMO_SESSION_SCOPING`).
- Native in-app API reference and user guide pages (replacing an iframe-based/dead
  ApiDocs stub).
### Fixed
- Removed multiple hardcoded default-token/admin-password fallbacks — internal-token
  auth is now fully env-driven with no insecure default.
- Fixed a Vercel frontend mixed-content issue on the API docs page.
- Synced default embedding model to BAAI/bge-m3.
- Fixed a route-change flash caused by a nested `AnimatePresence` wrapper.
- Replaced MAC-address-derived telemetry instance ID with a random, persisted UUID.
- Stopped hardcoding the maintainer's gateway URL in the frontend and in e2e tests.
- Removed Lightning AI branding and internal planning-doc references from the shipped
  app.

## [0.1.10]
### Added
- Telemetry instance tracking with crash-loop protection.
### Fixed
- Recharts/Vite production chunking error (React error #130) and the resulting SPA
  black-screen (missing `/assets` mount).
- CI/deploy pipeline fixes (JSON decode error in the deploy job, pytest exit-code-5
  from a stray `addopts`, integration-test hardening).

## [0.1.9] - 2026-07-16
### Changed
- Corrected package license metadata from MIT to AGPL-3.0 to comply with strict dual-licensing policy.

## [0.1.8]
### Fixed
- Resolved reranker fallback issue.
- Fixed HuggingFace URL formatting bug.
