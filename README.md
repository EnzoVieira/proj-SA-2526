# pi-server — ambient comfort smart-home

Python asyncio server for a university project (Sensorização e Ambiente, MEI — Universidade do Minho). Runs on a Raspberry Pi alongside Home Assistant: reads sensor data from an Arduino over USB, classifies thermal and luminosity comfort with two RandomForest models, looks up the resulting device action in a policy table, and POSTs it to Home Assistant — which drives the AC unit (via IR blaster) and the motorised blinds.

```
Arduino ──USB serial──> Ingester ──> EventBus ──> Processor ──> MLModel ──> ActionHandler ──> Home Assistant REST
```

Deeper architectural and ML docs live under `CLAUDE.md` and `.claude/docs/`.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A Raspberry Pi running Home Assistant (for production)
- An Arduino with a DHT11 sensor + analog light sensor wired over USB (9600 baud)

Install uv:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Local development

```sh
uv sync
cp .env.example .env   # fill in HA_BASE_URL, HA_TOKEN, HA_AC_ENTITY, HA_BLINDS_ENTITY
uv run -m pi_server
```

The server reads from `/dev/ttyACM0` by default. On macOS dev machines you may need to edit `_PORT` in `pi_server/core/ingester.py:27` (or set it to `"..."` to trigger auto-detection).

### Run without an Arduino

For off-Pi development, flip `DEBUG_MODE` to `True` in `pi_server/core/manager.py:19`. The ingester then emits synthetic sensor readings every 2 seconds.

### Generate dataset and train models locally

```sh
uv run -m pi_server.ml.dataset    # writes assets/dataset.csv
uv run -m pi_server.ml.train      # writes assets/models/{thermal,luminosity}.joblib
```

For dataset and model design details, see `.claude/docs/ml_models.md`.

### Developer commands

```sh
uv run ruff check .
uv run ruff format .
```

## Deploy and run on the Raspberry Pi

The full flow from your laptop to a running server on the Pi:

### 1. Push the code

From the repo root on your laptop:

```sh
bash deploy.sh
```

This rsyncs the source tree to `pi@raspberrypi.local:/home/pi/proj-SA-2526/`, excluding `.venv`, `.env`, `assets/models`, `assets/dataset.csv`, and other local cruft.

### 2. Copy the `.env` separately

`.env` is intentionally excluded from rsync so secrets don't ride along with the source code. Copy it explicitly whenever it changes:

```sh
scp .env pi@raspberrypi.local:/home/pi/proj-SA-2526/.env
```

### 3. Sync the venv on the Pi

```sh
ssh pi@raspberrypi.local
cd /home/pi/proj-SA-2526
uv sync
```

### 4. Generate dataset and train models on the Pi

`deploy.sh` excludes `assets/dataset.csv` and `assets/models/`, so both must be regenerated on the Pi after the first deploy (and any time the labelling or training code changes):

```sh
uv run -m pi_server.ml.dataset
uv run -m pi_server.ml.train
```

This takes ~30 seconds on a Pi 4.

### 5. Sanity-check Home Assistant

Before starting the server, confirm your token and entity IDs work:

```sh
source .env
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_BASE_URL/api/"
# expect: {"message":"API running."}
```

Fire one real device call to confirm IR codes and entity IDs:

```sh
curl -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"entity_id\":\"$HA_AC_ENTITY\",\"hvac_mode\":\"off\"}" \
  "$HA_BASE_URL/api/services/climate/set_hvac_mode"
```

If the AC actually responds, you're good. A 401/404 here means fix `.env` before starting the server.

### 6. Run the server in tmux

```sh
tmux new -s pi_server
cd /home/pi/proj-SA-2526
uv run -m pi_server
# detach with Ctrl-b d ; re-attach later with `tmux attach -t pi_server`
```

You'll see live `[server]` console output, and the same lines land in `logs/server.log` (file is truncated on each restart — see `.claude/docs/code_patterns.md`).

## What to watch in the log

- `Sensor data: Temp=...°C, Humidity=...%, Light=...` — ingester reading the Arduino.
- `Action plan: thermal=..., lum=... -> hvac=..., cover=... (...)` — comfort policy made a decision.
- `HA: AC set to hvac_mode=...` and `HA: blinds open_cover|close_cover` — HA accepted the call.
- Silence for the matching action when the decision is unchanged — debouncer working.
- `HA set_hvac_mode=... failed: ...` — credentials or entity IDs are wrong, or HA is unreachable.

## Quick reference

```sh
# laptop
bash deploy.sh
scp .env pi@raspberrypi.local:/home/pi/proj-SA-2526/.env   # only when .env changed

# pi (after first deploy or after ml/ changes)
cd /home/pi/proj-SA-2526 \
  && uv sync \
  && uv run -m pi_server.ml.dataset \
  && uv run -m pi_server.ml.train \
  && uv run -m pi_server
```

## Documentation

- `CLAUDE.md` — 1-minute project orientation (status, layout, conventions, gotchas).
- `.claude/docs/architecture.md` — component-by-component data flow.
- `.claude/docs/code_patterns.md` — style conventions across the codebase.
- `.claude/docs/ml_models.md` — synthetic dataset rules, training pipeline, model design.
- `.claude/docs/homelab_architecture.md` — physical setup, HA REST contracts, `.env` schema.
- `.claude/docs/next_improves.md` — roadmap of possible next steps.

---

![](https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fwallpapers.com%2Fimages%2Fhd%2Fnicolas-cage-meme-pokemon-characters-66m522s32l1oiz43.jpg&f=1&nofb=1&ipt=8293c36c71a3e38017afc2c178a865ef07c614c8d680d1b06dd4e68ab2ef719c)
