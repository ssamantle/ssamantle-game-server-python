# Loadtests

Locust-based load tests for the V1 game server live under this directory.

## Quick Start

1. Install the Locust dependency group:

```bash
uv sync --group perf
```

2. Run the default gameplay scenario:

```bash
uv run --group perf locust -f loadtests/scenarios/locustfile.py --host http://127.0.0.1:8000
```

3. Run a headless polling-focused scenario:

```bash
uv run --group perf locust \
  -f loadtests/scenarios/polling_cache.py \
  --host http://127.0.0.1:8000 \
  --headless \
  -u 200 \
  -r 20 \
  -t 10m \
  --csv loadtests/reports/polling_cache \
  --csv-full-history
```

## Notes

- The current application only supports a single active game with `V1_GAME_ID = 1`.
- `HostUser` is intentionally a single fixed-count user that creates the game first.
- A gameplay user submits one guess every 2 seconds and polls the game state every 3 seconds.
- The built-in word list is a fallback only. Replace `loadtests/data/words_smoke.txt` with words that are guaranteed to exist in your vector database.
- `/api/v1/games/polling/db` is deprecated and intentionally excluded from the current Locust suite.
