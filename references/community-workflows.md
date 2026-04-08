### 1.8 🧠 Client Workflows (`client_workflows`)

Higher-level workflow layer that combines entity resolution, user intel, message center context, creator analytics, operator-task assembly, and inbound triage.

#### High-value actions

| Action | Description |
|---|---|
| `content_object_lookup` | Resolve a target URL/id into a normalized entity plus lookup bundle |
| `investigate_user` | Build a creator-aware investigation bundle with profile, recent content, creator metrics, and audience fit |
| `prepare_reply_context` | Build thread-aware reply context and `candidate_reply_input` |
| `classify_inbound_intent` | Classify inbound text into cooperation / licensing / support / praise / low-value heuristics |
| `operator_triage` | Produce triage output for a live inbound item with urgency, tone, review flag, and reply guidance |
| `creator_dashboard_snapshot` | Unified operator snapshot across inbox, priority, and creator KPIs |
| `operator_dashboard_snapshot` | Alias of `creator_dashboard_snapshot` |
| `creator_task_queue` | Structured creator/operator task queue derived from inbox + KPI signals |
| `operator_task_queue` | Alias of `creator_task_queue` |
| `recommend_reply_targets` | Ranked reply-target suggestions from priority inbox signals |
| `content_opportunity_brief` | Structured content/opportunity brief from creative-center analytics |

#### Examples

```bash
# Resolve a content object into a normalized entity + lookup bundle
python main.py client_workflows content_object_lookup '{"target": "https://www.bilibili.com/opus/1187451323683962904"}'

# Creator-aware user investigation
python main.py client_workflows investigate_user '{"uid": 434156493, "include_creator_metrics": true, "period": "week"}'

# Build reply/thread context for a latest reply / @ mention / DM flow
python main.py client_workflows prepare_reply_context '{"source": "reply", "limit": 3}'
python main.py client_workflows prepare_reply_context '{"source": "at", "limit": 3}'
python main.py client_workflows prepare_reply_context '{"source": "dm", "receiver_id": 123456, "limit": 20}'

# Inbound classification / triage
python main.py client_workflows classify_inbound_intent '{"text": "想合作推广一下这个项目", "target": "https://www.bilibili.com/video/BV1KQPyzcEhH"}'
python main.py client_workflows operator_triage '{"source": "reply", "limit": 5}'
python main.py client_workflows operator_decision_loop '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows draft_reply_candidate '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows send_or_queue_reply '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "execute_send": false, "force_public_send": true}'
python main.py client_workflows reply_preview_card '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "force_public_send": true}'
python main.py client_workflows approve_and_send_reply '{"approved": true, "source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "force_public_send": true}'
python main.py client_workflows automation_brief '{"period": "week", "max_items": 5, "priority_threshold": 80}'
python main.py client_workflows automation_tick '{"period": "week", "max_items": 5, "priority_threshold": 80, "mode": "review"}'

# Unified operator / creator dashboard snapshot
python main.py client_workflows creator_dashboard_snapshot '{"period": "week", "max_items": 5}'
python main.py client_workflows operator_dashboard_snapshot '{"period": "week", "max_items": 5}'

# Structured action queue + reply targeting
python main.py client_workflows creator_task_queue '{"period": "week", "max_items": 5}'
python main.py client_workflows recommend_reply_targets '{"max_items": 5}'
python main.py client_workflows content_opportunity_brief '{"period": "week", "max_items": 5}'
```

#### Structured output notes

- `prepare_reply_context` returns `thread_context`, `reply_guidance`, `candidate_reply_input`, and `interest_profile`
- `investigate_user` returns `creator_profile`, `creator_metrics`, `audience_fit`, and `brief`
- `classify_inbound_intent` returns `classification.interest`, `urgency`, `tone`, `review_required`, and `canned_refs`
- `operator_triage` returns `triage`, `reply_guidance`, `candidate_reply_input`, and compact context payloads
- `operator_decision_loop` returns a concrete decision, enriched object context, and operator brief
- `draft_reply_candidate` returns a reply draft plus a send-plan preview
- `send_or_queue_reply` sends DMs directly, public replies only when thread mapping is proven, and otherwise returns a structured queue item
- `automation_brief` is the preferred automation snapshot for cron/sub-agents: dashboard + tasks + reply targets + opportunities + normalized `next_actions`.
- `automation_tick` is the lightweight automation poll result: `recommended_mode`, `should_act`, and the top next action.
- Use **OpenClaw Cron Job**, not Unix cron, for OpenClaw-native scheduling of these workflows.
- Prefer **cron** for exact schedules / isolated runs, and **heartbeat** for drift-tolerant review loops and low-urgency scanning.
- `creator_dashboard_snapshot` merges `message_center` + `creative_center`
- `creator_task_queue` produces structured work items with `type`, `priority`, `risk`, `reason`, and `payload`
- Workflow actions increasingly include a `schema` field like `bilibili.client_workflows.<action>.v1` for downstream consumers
- Use this layer when the task is operational, not just raw endpoint access

---

#### Automation scheduling guidance

Use the workflow layer as the automation boundary.

- **Do use OpenClaw Cron Job** for scheduled automation in OpenClaw.
- **Do not prefer Unix cron** for these in-agent workflows unless you are intentionally operating outside OpenClaw runtime.
- **Cron is best for**: exact schedules, isolated agent turns, recurring digests, fixed 15-minute / hourly review loops.
- **Heartbeat is best for**: low-pressure review sweeps, drift-tolerant monitoring, and “only interrupt me if something actually matters.”

OpenClaw Cron Job example:

```json
{
  "name": "bilibili-automation-tick",
  "schedule": {
    "kind": "cron",
    "expr": "*/15 * * * *",
    "tz": "Asia/Shanghai"
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Run: python main.py client_workflows automation_tick '{\"period\": \"week\", \"max_items\": 5, \"priority_threshold\": 80, \"mode\": \"review\"}'. Summarize the top next action and keep reply sending on the preview/approval path.",
    "timeoutSeconds": 120
  },
  "delivery": {
    "mode": "announce"
  }
}
```


### Message Center Quick Examples

```bash
# Unified inbox summary for cron / dashboards
python main.py message_center inbox_summary
python main.py message_center inbox_digest
python main.py message_center priority_digest
python main.py message_center automation_snapshot
python main.py message_center show_config

# Unread counters
python main.py message_center unread

# Replies / @ / likes
python main.py message_center replies
python main.py message_center at_me
python main.py message_center likes

# Message sessions and thread fetch
python main.py message_center sessions
python main.py message_center session_detail '{"talker_id": 123456, "session_type": 1}'
python main.py message_center fetch_messages '{"talker_id": 123456, "session_type": 1, "begin_seqno": 0}'
python main.py message_center dm_history '{"talker_id": 123456, "session_type": 1, "begin_seqno": 0}'

# Send a plain-text DM
python main.py message_center send_text '{"receiver_id": 123456, "text": "你好，这里是测试私信。"}'

# Config-driven automation rules live outside code
# Default config file: <workspace>/bilibili-message-center.json (workspace root is auto-detected)
# Template/reference only: skills/bilibili-all-in-one/config/message-center.example.json
# Optional override: export BILIBILI_MESSAGE_CENTER_CONFIG=/path/to/override.json

# System notifications
python main.py message_center system_messages
```
