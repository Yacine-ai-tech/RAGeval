# Changelog

## [0.1.19] - 2026-08-14
### Fixed
- **`_remote_embed()` sent the wrong bearer token to a `huggingface.co` `EMBEDDING_ENDPOINT`.**
  It always authenticated with `INFERENCE_TOKEN` — the credential for a self-hosted
  orchestrator/Studio host, per the generic `POST {url}/embed` contract — even when the
  URL was HF's own Inference API, which needs `HF_TOKEN`. Every call to that branch got
  a 401 that looked like an HF-side flake but wasn't: it was authenticating with a token
  that was never valid for HF in the first place. Found live while evaluating against a
  host app configured for the HF-direct path. Now dispatches on the URL, matching the
  `HF_TOKEN`/`INFERENCE_TOKEN` split already used elsewhere for this exact distinction.

## [0.1.18] - 2026-08-11
### Fixed
- **Resolves the 0.1.17 "known gotcha".** `core.config`/`rageval._compat` no longer fall
  back to a bare `POSTGRES_URL` at all — they read `RAGEVAL_POSTGRES_URL` exclusively.
  The fallback was the actual bug: it made `rageval`, embedded as a library, silently
  adopt a host app's own unrelated Postgres whenever that host (reasonably) also used
  the generic `POSTGRES_URL` name for itself. Confirmed live twice while fixing this —
  the fallback wrote a real `rageval_log` table into another real project's production
  database before being removed (cleaned up, verified zero rows remain).
- This project's own standalone deployment (`api.py`, e.g. this repo's Render service,
  which sets `POSTGRES_URL` via Render's dashboard rather than this repo's `.env`) keeps
  working via a narrow, one-time `POSTGRES_URL`->`RAGEVAL_POSTGRES_URL` compat copy done
  in `api.py` itself at process startup — that behavior is specific to this app's own
  entrypoint and is not part of the `rageval` library other projects import.

## [0.1.17] - 2026-08-11
### Fixed
- **The "60-second pitch" was broken for any first-time user.** Nothing except `api.py`
  (module-level import) or the `rageval init` CLI command ever called
  `init_rageval_table()` — so `pip install omnismart-rageval` + `@track` on a fresh
  install, with no API server ever run, failed on the very first call with
  `sqlite3.OperationalError: no such table: rageval_log`. `log_interaction()` (used by
  `@track`, `log_dspy_run`/`dspy_compile_callback`, and any bare library use) now
  auto-initializes the table on first write, once per process. Caught by actually
  testing the drop-in-library path end-to-end (wiring AgentKit's DSPy compile step to
  this package) rather than assuming the README's own pitch worked.
### Known gotcha (documented, not changed)
- Embedding `rageval` as a library inside a host app that has its own `POSTGRES_URL` for
  its own unrelated database will make `rageval` try to write to *that* database instead
  of SQLite — `rageval._compat.settings.POSTGRES_URL` reads the same generic env var
  name, so it collides whenever both use the convention. Workaround for now: unset/blank
  `POSTGRES_URL` before importing `rageval`, or point it at a database that actually has
  the `rageval_log` schema. A `RAGEVAL_POSTGRES_URL`-prefixed override would fix this
  properly but changes the existing `.env.example` contract, so it's flagged rather than
  changed in this pass.

## [0.1.16] - 2026-08-11
### Added
- `_remote_embed` now dispatches on the `EMBEDDING_ENDPOINT` URL's own shape instead of
  speaking only the generic contract: a `huggingface.co` URL is called in HF's native
  Inference API shape (`{"inputs": [...]}` in, mean-pooling per-token responses when the
  target is a plain feature-extraction pipeline rather than a sentence-embedding model).
  Verified live against both a real Hugging Face Inference endpoint and a real on-demand
  orchestrator host — not just unit-tested.
### Fixed
- Rewrote the e2e test suite (`rageval_telemetry.spec.ts`, `exhaustive_ui.spec.ts`)
  against the real API/UI; the previous version tested a fictional `/api/*` surface and
  UI flows (a Cost-page threshold slider, an Instrumentation config panel, etc.) that
  don't exist in this app. All 29 UI + API e2e tests verified passing against a live
  local instance before merging.
- Vite's dev-server proxy (`vite.config.ts`) used a plain `/eval` string-prefix key,
  which also silently swallowed the `/evaluate` client-side route — caught by an e2e
  test actually navigating there, not by code review.
- `frontend/src/App.tsx`: the Benchmark page (a real, implemented HaluEval results
  write-up) had a route but was missing from the nav array.

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
