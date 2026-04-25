# sastaspace comment moderator

Polls SpacetimeDB for `Comment` rows with `status='pending'`, classifies each via
a local Ollama-served `llama-guard3:1b` (Agno wraps the agent loop), and calls
`set_comment_status` with the owner identity.

## Env

| Var | Default | Notes |
|---|---|---|
| `STDB_HTTP_URL` | `http://localhost:3100` | Container reaches the stdb container via host loopback (host network mode) or the compose service name |
| `STDB_MODULE` | `sastaspace` | |
| `SPACETIME_TOKEN` | (required) | Same value as the GH secret — must be the owner identity token |
| `OLLAMA_HOST` | `http://localhost:11434` | Reaches host's Ollama via `host.docker.internal` (compose maps it) |
| `MODERATOR_MODEL` | `llama-guard3:1b` | Pull on the host before first run: `ollama pull llama-guard3:1b` |
| `POLL_SECONDS` | `3` | Sleep when the pending queue is empty |
| `LOG_LEVEL` | `INFO` | |

## Local dev

```bash
cd infra/agents/moderator
pip install -e .[dev]
SPACETIME_TOKEN=$(cat ~/.config/spacetime/cli.toml | grep spacetimedb_token | cut -d'"' -f2) \
  STDB_HTTP_URL=https://stdb.sastaspace.com \
  python -m sastaspace_moderator.main
```

## Tests + coverage

```bash
pip install -e .[dev]
pytest        # 70% coverage gate per pyproject.toml
```
