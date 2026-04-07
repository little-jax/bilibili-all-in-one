# Live Ops — Interactive

Use this when the user is actively operating a live session in real time.

## Strong triggers

- 开播
- 下播
- 继续上次直播
- 改直播标题 / 分区 / 公告
- 看直播状态
- OBS / 推流 / 恢复直播

## Default workflow

### Start flow

1. If ambiguous, ask one fork only:
   - 延续上次标题/分区/公告
   - 还是这次新开一场
2. If the user already gave title/area/announcement, skip the question.
3. Run preflight when OBS state matters.
4. Start live, optionally enable runtime watching.

## Core commands

```bash
python main.py live_orchestrator get_live_room_profile
python main.py live_orchestrator pre_start_room_patch '{"title": "Rig/2 live dev", "announcement": "今晚八点，来。", "area_id": 216}'
python main.py live_orchestrator prepare_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
python main.py live_orchestrator start_live_session '{"title": "Rig/2 live dev", "announcement": "今晚八点，来。", "area_id": 216, "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "auto_start_obs": true, "watch_runtime": true, "watch_interval_seconds": 10, "watch_samples": 6, "watch_clear_log_first": true}'
python main.py live_orchestrator stop_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
python main.py live_orchestrator recover_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
```

## Use when uncertain

```bash
python main.py live_orchestrator get_live_session_cache
python main.py live_orchestrator get_live_runtime_log '{"limit": 20}'
python main.py live_orchestrator live_health_check '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "transient_grace_seconds": 8}'
```
