# Telemetry

RAGeval can send a single anonymous "startup" ping so the maintainer can gauge install
volume. It is off by default in a self-hosted install: nothing is sent unless you set
`TELEMETRY_URL` in your `.env`.

## What is sent

When `TELEMETRY_URL` is set and `TELEMETRY_OPT_OUT` is not `true`, on process start the
server sends one HTTP POST containing:

```json
{"service": "RAGeval", "event": "startup", "instance_id": "<random hex string>"}
```

- `instance_id` is a random UUID generated locally on first run and persisted under the
  logs directory (`.telemetry_instance_id`) — **not** derived from a MAC address or any
  other hardware fingerprint. Delete that file to reset it.
- No API keys, prompts, queries, answers, retrieved chunks, scores, or any other
  application data are ever included.
- At most one ping is sent per 6-hour window per running instance.

## How to disable

Set `TELEMETRY_OPT_OUT=true` in your `.env`, or simply leave `TELEMETRY_URL` unset (the
default) — either one is sufficient on its own.
