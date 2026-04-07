# Live Ops — Scheduled / Automation

Use this when the work is for cron, heartbeat follow-up, isolated automation turns, or machine-driven live checks.

## Best-fit tasks

- 定时检查直播状态
- 收集直播 runtime timeline
- 直播恢复巡检
- 收播后自动汇总
- 只要有异常再提醒我

## Preferred read path for automation

For scheduled tasks, feed this file directly instead of the whole skill.

## Minimal automation patterns

### Runtime sampling window

```bash
python main.py live_orchestrator watch_live_runtime '{"interval_seconds": 30, "samples": 20, "clear_log_first": true, "include_overview": false}'
python main.py live_orchestrator get_live_runtime_log '{"limit": 20}'
```

### Recovery audit

```bash
python main.py live_orchestrator recover_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "include_runtime_stats": true, "include_overview": false}'
```

### End-of-session cleanup / summary

```bash
python main.py live_orchestrator stop_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
python main.py live_orchestrator get_live_runtime_log '{"limit": 50}'
```

## Automation rules

1. Prefer cache-aware flows over manually threading `live_key` around.
2. Prefer `recover_live_session` when state may be split across sessions.
3. Prefer `watch_live_runtime` for time-series capture instead of ad-hoc one-off reads.
4. If the task is exact-time or isolated, use cron. If it is drift-tolerant monitoring, use heartbeat.
