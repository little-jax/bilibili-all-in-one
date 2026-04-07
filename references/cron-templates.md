# Bilibili Cron Templates

Use these as copy-ready OpenClaw cron payload templates.

Rule: for scheduled jobs, read `skill.md` only as the index page, then read the most specific workflow reference directly.

## 1. Low-activity reply/message review

Use when the account is quiet and you want a low-noise inbox/reply triage pass.

```json
{
  "name": "bilibili-low-activity-automation-tick",
  "description": "Low-frequency Bilibili automation tick for a quiet account.",
  "schedule": {
    "kind": "cron",
    "expr": "0 */6 * * *",
    "tz": "Asia/Shanghai",
    "staggerMs": 300000
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "In /Users/jaxlocke/.openclaw/workspace/skills/bilibili-all-in-one, read `skill.md` only as the trigger/index page, then read `references/reply-and-message-workflows.md` directly as the workflow document for this scheduled task. Do not load the full skill reference set unless the targeted workflow file proves insufficient. Run a low-frequency Bilibili automation review for a quiet account using the workflow layer, not raw endpoint stitching. Run: python main.py client_workflows automation_tick '{\"period\": \"week\", \"max_items\": 3, \"priority_threshold\": 85, \"mode\": \"review\"}'. Summarize the top next action for logs. Do not send or approve any reply automatically. If nothing meaningful is happening, keep the result terse and quiet.",
    "timeoutSeconds": 120
  },
  "delivery": {
    "mode": "none"
  },
  "failureAlert": {
    "mode": "announce",
    "after": 1,
    "cooldownMs": 21600000
  }
}
```

## 2. Live recovery audit

Use when you want a scheduled pass that checks whether Bilibili/OBS/cache state drifted apart and tells you the next action.

```json
{
  "name": "bilibili-live-recovery-audit",
  "description": "Scheduled live recovery audit using cache + OBS + Bilibili state.",
  "schedule": {
    "kind": "every",
    "everyMs": 1800000
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "In /Users/jaxlocke/.openclaw/workspace/skills/bilibili-all-in-one, read `skill.md` only as the trigger/index page, then read `references/live-ops-scheduled.md` directly. Do not load the full skill reference set unless the targeted workflow file proves insufficient. Run: python main.py live_orchestrator recover_live_session '{\"obs_host\": \"127.0.0.1\", \"obs_port\": 4455, \"obs_password\": \"...\", \"include_runtime_stats\": true, \"include_overview\": false}'. Return the concrete next action only: continue, stop, clear cache, or none.",
    "timeoutSeconds": 180
  },
  "delivery": {
    "mode": "none"
  },
  "failureAlert": {
    "mode": "announce",
    "after": 1,
    "cooldownMs": 21600000
  }
}
```

## 3. Runtime timeline sampler

Use when you want a machine-driven live timeline log without manual babysitting.

```json
{
  "name": "bilibili-live-runtime-sampler",
  "description": "Sample Bilibili live runtime stats into JSONL for later review.",
  "schedule": {
    "kind": "every",
    "everyMs": 900000
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "In /Users/jaxlocke/.openclaw/workspace/skills/bilibili-all-in-one, read `skill.md` only as the trigger/index page, then read `references/live-ops-scheduled.md` directly. Run: python main.py live_orchestrator watch_live_runtime '{\"interval_seconds\": 30, \"samples\": 20, \"clear_log_first\": false, \"include_overview\": false}'. Then run: python main.py live_orchestrator get_live_runtime_log '{\"limit\": 20}'. Keep the summary compact.",
    "timeoutSeconds": 900
  },
  "delivery": {
    "mode": "none"
  }
}
```

## 4. Post-live summary pull

Use when you want a delayed follow-up after a stream likely ended, to fetch stop stats and inspect the latest runtime log.

```json
{
  "name": "bilibili-post-live-summary",
  "description": "Fetch post-live stop stats and recent runtime log after a likely stream end.",
  "schedule": {
    "kind": "at",
    "at": "2026-04-07T15:00:00+08:00"
  },
  "deleteAfterRun": true,
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "In /Users/jaxlocke/.openclaw/workspace/skills/bilibili-all-in-one, read `skill.md` only as the trigger/index page, then read `references/live-ops-scheduled.md` directly. Run: python main.py live_orchestrator stop_live_session '{\"obs_host\": \"127.0.0.1\", \"obs_port\": 4455, \"obs_password\": \"...\"}'. Then run: python main.py live_orchestrator get_live_runtime_log '{\"limit\": 50}'. Return a compact post-live summary.",
    "timeoutSeconds": 300
  },
  "delivery": {
    "mode": "announce"
  }
}
```

## 5. Dynamic draft / publishing reminder

Use when you want a scheduled writing prompt or pre-publish review instead of an automatic public write.

```json
{
  "name": "bilibili-dynamic-draft-reminder",
  "description": "Periodic reminder to review/post a Bilibili dynamic draft.",
  "schedule": {
    "kind": "cron",
    "expr": "30 19 * * 1,3,5",
    "tz": "Asia/Shanghai"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "In /Users/jaxlocke/.openclaw/workspace/skills/bilibili-all-in-one, read `skill.md` only as the trigger/index page, then read `references/dynamic-and-publishing.md` directly. Prepare a short Bilibili dynamic draft or publishing reminder based on current context, but do not post automatically. Return the draft and the recommended next action only.",
    "timeoutSeconds": 180
  },
  "delivery": {
    "mode": "announce"
  }
}
```

## 6. Auth health check

Use when repeated scheduled failures may actually be caused by expired cookies.

```json
{
  "name": "bilibili-auth-health-check",
  "description": "Scheduled auth/session health check for Bilibili creator workflows.",
  "schedule": {
    "kind": "cron",
    "expr": "0 10 * * *",
    "tz": "Asia/Shanghai"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "In /Users/jaxlocke/.openclaw/workspace/skills/bilibili-all-in-one, read `skill.md` only as the trigger/index page, then read `references/auth-and-session.md` directly. Run: python main.py auth_client verify_auth. If auth looks broken, say so plainly and stop there; do not attempt unrelated write workflows.",
    "timeoutSeconds": 120
  },
  "delivery": {
    "mode": "announce"
  }
}
```

## Notes

- Replace placeholder OBS password / host / port values before enabling.
- Prefer `delivery.mode = none` for background review jobs unless the output is meant to notify.
- Prefer `announce` only for drafts, actionable alerts, or summaries the user actually wants surfaced.
- For public-write tasks, schedule a draft/review job first unless explicit autonomous posting is desired.
