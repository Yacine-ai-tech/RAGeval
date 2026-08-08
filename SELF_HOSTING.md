# Self-Hosting RAGeval

1. **Installation:** Run `pip install omnismart-rageval`.
2. **Configuration:** Copy `.env.example` to `.env` and set your API keys (e.g., `GROQ_API_KEY`, `ANTHROPIC_API_KEY`). Ensure all keys are dynamically loaded via `os.getenv` in your application.
3. **Docker:** Deploy using the provided Dockerfile.
4. **Database:** Uses a local SQLite fallback (`sqlite:///rageval.db`) but Postgres is recommended for production.
