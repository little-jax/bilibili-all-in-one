### 1.7 🔴 Live Orchestrator (`bilibili_live_orchestrator`)

Bilibili + OBS live control surface for room inspection, announcement updates, preflight, start/stop orchestration, and end-of-session summaries.

#### High-value actions

| Action | Description |
|---|---|
| `get_live_room_profile` / `room_profile` | Inspect current room title, description, live status, area, and room news |
| `update_live_announcement` / `set_announcement` | Update the room announcement/news |
| `update_live_title` / `set_title` | Update the live-room title and return Bilibili audit info |
| `pre_start_room_patch` | Apply safe pre-start changes now and return title/announcement results plus start-time area plan |
| `prepare_live_session` | Preflight room + OBS connection + current stream target |
| `start_live_session` | Start Bilibili live, optionally absorb `title` / `announcement` / `area_id` pre-start patching, capture RTMP target, apply to OBS, optionally start OBS output, and optionally auto-sample runtime stats |
| `stop_live_session` | Stop OBS + Bilibili live, optionally restore OBS target, and fetch `StopLiveData` when `live_key` is provided |
| `live_health_check` / `health_check` | Compare Bilibili room state vs OBS output with transient grace-window handling |

#### Examples

```bash
# Inspect current room profile
python main.py live_orchestrator get_live_room_profile

# Update announcement / room news
python main.py live_orchestrator update_live_announcement '{"content": "今晚八点，来。"}'

# Update live-room title
python main.py live_orchestrator update_live_title '{"title": "Rig/2 live dev"}'

# Patch pre-start room state
python main.py live_orchestrator pre_start_room_patch '{"announcement": "今晚八点，来。", "area_id": 216, "title": "Rig/2 live dev"}'

# OBS + room preflight
python main.py live_orchestrator prepare_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'

# Start live and start OBS (can absorb pre-start title / announcement / area patching)
python main.py live_orchestrator start_live_session '{"title": "Rig/2 live dev", "announcement": "今晚八点，来。", "area_id": 216, "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "auto_start_obs": true, "watch_runtime": true, "watch_interval_seconds": 10, "watch_samples": 6, "watch_clear_log_first": true}'

# Stop live and fetch StopLiveData summary (save live_key from start)
python main.py live_orchestrator stop_live_session '{"live_key": "<live_key>", "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'

# Health check with transient grace window
python main.py live_orchestrator live_health_check '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "transient_grace_seconds": 8}'
```

#### Important behavior notes

- `announcement` is supported now via `updateRoomNews`.
- `title` is supported now via `POST /room/v1/Room/update` and returns Bilibili `audit_info`.
- `area_id` is treated as a confirmed **start-time patch** because `startLive(area_v2=...)` is the write path we have wired.
- `start_live_session` now runs the same safe pre-start patch logic when `title`, `announcement`, or `area_id` is provided; if title/announcement patching fails, the live start is aborted instead of pretending success.
- successful `start_live_session` writes workspace cache file `bilibili-live-session.json` so another session can stop the live and fetch `StopLiveData` without manually re-pasting `live_key`.
- `get_live_session_cache` reads that workspace cache with masked sensitive fields by default; set `reveal_sensitive=true` only when you truly need raw values.
- `clear_live_session_cache` deletes the cache file for manual recovery / reset.
- `get_live_runtime_stats` can probe session data mid-stream via `live_key`; treat those numbers as provisional until stop.
- `watch_live_runtime` samples runtime stats on an interval and appends JSONL snapshots to the workspace log file `bilibili-live-runtime.jsonl`.
- `get_live_runtime_log` reads recent runtime snapshots; `clear_live_runtime_log` resets the JSONL log.
- `recover_live_session` combines cache, room health, OBS state, and optional runtime stats into a concrete recommendation.
- `stop_live_session` now includes a normalized `StopLiveData` summary with derived quality flags.
- `stop_live_session` reads the workspace cache by default when `live_key` is omitted, then marks that cache inactive after stop.
- OBS may return `StopStream` 501 when already stopped; this is treated as an idempotent stop path, not a hard failure.
- If OBS still looks active, the stop flow can fall back to `StopOutput("adv_stream")`.


### Title update verification note

Workspace live-session cache:

- path: `<workspace>/bilibili-live-session.json` (workspace root is auto-detected)
- written on successful live start
- read on stop when `live_key` is omitted
- preserves `last_stop_stats` / `last_live_key` after stop for later inspection

Real-world verification now confirms the live title write path:

- endpoint: `POST /room/v1/Room/update`
- required fields: `room_id`, `title`, `csrf`, `csrf_token`
- safe verification method: write back the current title unchanged and inspect the returned `audit_info`


### 1.9 📡 OBS Client (`bilibili_obs`)

Thin OBS websocket control layer used by the live orchestrator.

#### Useful actions

| Action | Description |
|---|---|
| `get_status` / `status` | Stream/record/stats snapshot |
| `get_stream_service` / `stream_service` | Inspect current stream target, masked by default |
| `set_stream_service` / `apply_stream_target` | Apply RTMP server/key |
| `start_stream` | Start OBS stream output |
| `stop_stream` | Stop OBS stream with fallback-aware logic |
| `stop_output` | Force-stop a named output such as `adv_stream` |
| `get_output_list` / `output_list` | Inspect available OBS outputs |
| `get_current_program_scene` / `current_scene` | Inspect active scene |

#### Examples

```bash
python main.py obs_client get_status '{"host": "127.0.0.1", "port": 4455, "password": "..."}'
python main.py obs_client get_stream_service '{"host": "127.0.0.1", "port": 4455, "password": "..."}'
python main.py obs_client stop_output '{"host": "127.0.0.1", "port": 4455, "password": "...", "output_name": "adv_stream"}'
```


#### Workflow examples

```bash
# Minimal start -> auto-watch -> stop
python main.py live_orchestrator start_live_session '{"area_id": 216, "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "auto_start_obs": true, "watch_runtime": true, "watch_interval_seconds": 5, "watch_samples": 3, "watch_clear_log_first": true}'
python main.py live_orchestrator get_live_runtime_log '{"limit": 10}'
python main.py live_orchestrator stop_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'

# Recover from cache in another session
python main.py live_orchestrator recover_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
```
