# DESIGN: core/braid + core/aardvark

**Status:** v0 implemented  
**Decoupled** from Lightspeed-Engine/Aardvark (TALONS). Callable from any extension via HTTP.

## Defaults

| Behavior | Default |
|----------|---------|
| Recording | **OFF** — nothing written |
| Fan-out stream | **OFF** — opt-in `sinks.stream: true` |
| Hooks | POST braid `/v1/ingest` — dropped when not recording |
| Legacy direct file | `ACTIVITY_LEGACY_DIRECT=1` (tests) |

## Ports

| Service | URL |
|---------|-----|
| braid | `http://127.0.0.1:4711` |
| aardvark control | `http://127.0.0.1:4712` |
| aardvark proxy | `48200+` per `agentKey` |

## braid API

- `GET /health`
- `GET /v1/recording/status`
- `POST /v1/recording/start` — `{ logPath, sessionId?, agentKey?, verbosity?, sinks? }`
- `POST /v1/recording/stop`
- `PUT /v1/context`
- `POST /v1/ingest` — `{ event }` or `{ events: [] }`
- `GET /v1/events`
- `GET /v1/events/stream` (SSE, when `sinks.stream`)

## aardvark API

- `GET /health`
- `GET|POST /v1/ports` — allocate plug-and-play proxy port
- `DELETE /v1/ports/{agentKey}`
- `GET /v1/config`

Observations ingested to braid **only when recording is on**.

## UI (cursor-activity)

- **Activity: Start Recording** / **Stop Recording**
- Timeline toolbar + status bar `Rec OFF` / `Rec ON`
- Optional proxy port allocation on start

## Start daemons

```bash
bash cursor/scripts/start-core-daemons.sh
```
