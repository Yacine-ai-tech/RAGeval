# Self-Hosting RAGeval

RAGeval is designed to be self-hosted: it ships with a SQLite-default storage backend (no database
server required to get started), a single-container Docker build, and an optional Postgres backend
for production use. This guide covers the common ways to run it yourself.

## 1. Installing via pip

The published package is `omnismart-rageval` (the distribution name); the CLI and Python import
remain `rageval`:

```bash
pip install omnismart-rageval
rageval init                 # creates ~/.rageval/rageval.db
rageval serve --port 8003
```

This is the fastest path for local use or for embedding RAGeval's `@track` decorator directly into
an existing Python application (see the README for integration examples). The dashboard is served
at `http://localhost:8003` once the server is running.

## 2. Running via Docker

The repo includes a `Dockerfile` (a slim `python:3.11-slim` base that installs
`requirements.txt`, copies the app, and runs `uvicorn api:app` on port 8003, honoring a
platform-injected `$PORT` if one is set) and a `docker-compose.dev.yml` for a batteries-included
dev/self-hosted setup.

To build and run with Docker directly:

```bash
docker build -t rageval .
docker run -p 8003:8003 --env-file .env rageval
```

Or, using the provided compose file (this is written for a remote host — an on-demand cloud box,
a home server, a spare VM — as much as for your local machine):

```bash
docker compose -f docker-compose.dev.yml up --build
```

This compose setup:

- Uses SQLite by default (`RAGEVAL_STORE=sqlite`, `RAGEVAL_DB_PATH=/app/data/rageval.db`), so no
  separate database container is needed to get running.
- Mounts your `.env` file read-only into the container, plus named volumes for the SQLite database
  (`rageval_db`) and the HuggingFace model cache (`hf_cache`) — the latter matters because the
  default embedding model (BGE-large, ~1.3 GB) downloads on first use and you don't want to re-pull
  it on every container restart.
- Runs `uvicorn` with `--reload`, i.e. it's a dev-oriented setup (live code reload from your working
  tree via bind mounts), not a hardened production configuration as-is.
- Includes a healthcheck against `/health` on port 8003.

If you're running it on a remote host and developing from your laptop, forward the port over SSH:

```bash
ssh -L 8003:localhost:8003 <your-remote-host>
# then open http://localhost:8003/health
```

For a production deployment you'd typically drop the `--reload` flag and the source bind-mounts,
and rely on the plain `Dockerfile` build (`COPY . .` bakes the code into the image) instead.

## 3. Configuration via `.env`

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

`.env.example` documents the full set of configuration variables (API keys, judge model selection,
embedding backend, storage backend, CORS, telemetry opt-out, and more) with placeholder values and
inline comments explaining each one — it's the authoritative reference, so this guide won't restate
every variable here. A few that matter most when you're first standing up an instance:

- `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY` — provider keys for whichever LLMs you
  configure as judges.
- `JUDGE_MODELS` — the multi-judge consensus needs at least two judges actually reachable at score
  time (missing keys / network errors just remove that judge from the vote; fewer than two
  reachable judges returns an error rather than silently scoring on one).
- `RAGEVAL_STORE` / `RAGEVAL_DB_PATH` — storage backend selection (see below).
- `CORS_ALLOWED_ORIGINS` — set this explicitly for anything beyond local dev.

Never commit a real `.env` file — only `.env.example` (with placeholder values) belongs in version
control.

## 4. Storage: SQLite default vs. Postgres for production

By default RAGeval stores everything in a local SQLite file (`RAGEVAL_STORE=sqlite`,
`RAGEVAL_DB_PATH` pointing at e.g. `~/.rageval/rageval.db` or a mounted volume path in Docker).
This is enough for local use, evaluation, and small deployments, and it's why "SQLite-default" is
one of RAGeval's headline properties — there's no database server to stand up before you can start
scoring queries.

For production use, set `RAGEVAL_POSTGRES_URL` to a Postgres connection string. When configured,
RAGeval stores query embeddings in a `pgvector` column so retrieval-relevance queries can use
Postgres-native vector similarity instead of recomputing embeddings on every read — this needs the
`pgvector` extension available on your Postgres instance (`CREATE EXTENSION vector`), which most
managed Postgres providers support out of the box.

Note the variable name specifically: it's `RAGEVAL_POSTGRES_URL`, not a bare `POSTGRES_URL`. This is
intentional — a generic `POSTGRES_URL` fallback would risk RAGeval, when imported as a library into
a host application, silently adopting that application's own unrelated database. Set the
RAGeval-specific variable.

## 5. Deploying to a container host

Because RAGeval ships as a standard container (a `Dockerfile` producing a single image that serves
both the API and, via the same origin, the built frontend), it's portable across most container
hosting options. A few interchangeable examples of where you could run it:

- **A managed container platform** (e.g. Fly.io, Railway, or similar) — point it at the `Dockerfile`
  and set your `.env` values as platform environment variables. Most of these platforms inject
  their own `$PORT`, which the Dockerfile already honors (`--port ${PORT:-8003}`).
- **A plain VPS** — run the Docker image directly (`docker run`) or via `docker compose`, behind
  whatever reverse proxy / TLS termination you already use.
- **Your own Kubernetes cluster** — build the image, push it to your registry, and deploy it as you
  would any other stateless HTTP service, with a persistent volume for the SQLite file (or a
  managed Postgres instance via `RAGEVAL_POSTGRES_URL`) if you need data to survive pod restarts.

None of these is "the" recommended target — pick whatever fits your existing infrastructure. The
main things any deployment needs to get right are: persistent storage for the database (a volume
for SQLite, or Postgres), API keys supplied as environment variables (never baked into the image),
and `CORS_ALLOWED_ORIGINS` set appropriately once the frontend isn't being served from the same
origin as the API in your setup.
