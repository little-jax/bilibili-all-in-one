---
name: bilibili-all-in-one
description: >
  A Bilibili creator-operations toolkit for creator/community workflows:
  live start/stop/recovery/runtime sampling, dynamic posting/repost/delete,
  comment/reply handling, message/reply triage, follower/community ops, plus
  download/watch/subtitle/publishing support. Use when the user talks about
  开播, 下播, 继续上次直播, 直播间标题/分区/公告, 发动态, 回动态, 回评论,
  处理B站回复/消息, or general Bilibili creator operations with authenticated cookies.
version: 1.0.18
type: code
implementation: python
interface: cli-and-api
runtime: python>=3.8
languages:
  - zh-CN
  - en
tags:
  - bilibili
  - video-download
  - hot-trending
  - subtitle
  - danmaku
  - video-publish
  - video-player

  - batch-download
  - multi-format
author: Little Jax / Mozi A.
license: MIT-0
homepage: https://github.com/little-jax/bilibili-all-in-one
repository: https://github.com/little-jax/bilibili-all-in-one
original_author: wscats
upstream_repository: https://github.com/wscats/bilibili-all-in-one
entry_point: main.py
required_env_vars: []
optional_env_vars:
  - BILIBILI_SESSDATA
  - BILIBILI_BILI_JCT
  - BILIBILI_BUVID3
  - BILIBILI_PERSIST
install: pip install -r requirements.txt
---

## What this skill is for

Use this skill aggressively for **Bilibili creator operations**.

Strong triggers:

- **Live ops**: `开播`, `下播`, `继续上次直播`, `收播`, `恢复直播`, `直播标题`, `直播分区`, `直播公告`, `OBS`, `推流`, `直播数据`
- **Community ops**: `处理B站回复`, `回评论`, `回动态`, `看谁回复了我`, `消息中心`, `评论区处理`, `粉丝互动`
- **Posting ops**: `发动态`, `转发动态`, `删动态`, `空间公告`, `发视频`, `查稿件`

Do not wait for the user to name the tool explicitly. If the intent is obviously Bilibili creator/account operation, use this skill.

## Default operating instincts

### If the user says 开播 / 下播 / 继续上次

1. Check session cache / recovery context first if continuity may matter.
2. If start intent is clear but continuity is ambiguous, ask one short fork:
   - continue last title/area/announcement
   - or start with new title/area/announcement
3. If the user already gave the new values, stop asking and execute.
4. Prefer:
   - `start_live_session`
   - `stop_live_session`
   - `recover_live_session`
5. When useful, enable runtime watching so the session leaves a timeline.

### If the user says 发动态 / 回动态 / 回评论 / 处理回复

1. Resolve the object/thread first.
2. If final wording is missing, ask for wording or produce a short draft.
3. Once wording and target are clear, execute the write action.
4. Return object id / url / success status when available.

### Ambiguity rule

Ask only for the missing write-critical fork.
If target + wording + mode are already clear, just do the work.

## Quick command patterns

### Live ops

```bash
# inspect / preflight / start
python main.py live_orchestrator get_live_room_profile
python main.py live_orchestrator prepare_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
python main.py live_orchestrator start_live_session '{"area_id": 216, "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "auto_start_obs": true}'

# recover / stop
python main.py live_orchestrator recover_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
python main.py live_orchestrator stop_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
```

### Runtime timeline

```bash
python main.py live_orchestrator watch_live_runtime '{"interval_seconds": 10, "samples": 6, "clear_log_first": true}'
python main.py live_orchestrator get_live_runtime_log '{"limit": 20}'
python main.py live_orchestrator clear_live_runtime_log
```

### Reply / creator workflows

```bash
python main.py client_workflows prepare_reply_context '{"source": "reply", "limit": 3}'
python main.py client_workflows operator_triage '{"source": "reply", "limit": 5}'
python main.py client_workflows draft_reply_candidate '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows automation_brief '{"period": "week", "max_items": 5, "priority_threshold": 80}'
```

## Reading map

Read only what you need:

- `references/auth-and-session.md` — QR login, auth repair, session validation
- `references/live-ops-interactive.md` — human-in-the-loop live start/stop/recovery
- `references/live-ops-scheduled.md` — cron/heartbeat/live automation workflows
- `references/reply-and-message-workflows.md` — replies, comments, inbox triage, automation entrypoints
- `references/dynamic-and-publishing.md` — dynamics, reposts, notices, publishing-adjacent writes
- `references/live-ops.md` — broader live technical reference / OBS details
- `references/community-workflows.md` — broader workflow reference / client workflow detail
- `references/general-cli.md` — auth, config, installation, downloader/player/subtitle/general commands
- `references/full-reference.md` — full legacy reference when the targeted files are not enough

### Scheduling rule

If the task is a cron job / heartbeat / scheduled automation, feed the most specific reference file directly instead of loading the whole skill reference set.

## Notes

- Keep `SKILL.md` short. It is the trigger/index page, not the dump site.
- Put new heavy examples and module-specific detail into `references/` unless they are truly core trigger/workflow guidance.
