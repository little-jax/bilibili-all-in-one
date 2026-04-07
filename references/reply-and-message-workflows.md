# Reply and Message Workflows

Use this when the task is about Bilibili replies, comments, @mentions, DMs, or inbox triage.

## Strong triggers

- 处理B站回复
- 回评论
- 回动态
- 看看谁回复了我
- 消息中心
- 帮我回一下这个

## Default workflow

1. Resolve the source first: reply / at / dm / message center.
2. Build thread/context before drafting.
3. If wording is missing, ask once or draft once.
4. Then send/queue/preview depending on certainty and public-write risk.

## Core commands

```bash
python main.py client_workflows prepare_reply_context '{"source": "reply", "limit": 3}'
python main.py client_workflows operator_triage '{"source": "reply", "limit": 5}'
python main.py client_workflows operator_decision_loop '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows draft_reply_candidate '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows send_or_queue_reply '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "execute_send": false, "force_public_send": true}'
python main.py client_workflows reply_preview_card '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "force_public_send": true}'
python main.py client_workflows approve_and_send_reply '{"approved": true, "source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "force_public_send": true}'
```

## Automation-friendly entrypoints

```bash
python main.py client_workflows automation_brief '{"period": "week", "max_items": 5, "priority_threshold": 80}'
python main.py client_workflows automation_tick '{"period": "week", "max_items": 5, "priority_threshold": 80, "mode": "review"}'
```
