# Bilibili Skill → Client Kernel Roadmap

## Positioning

This skill should evolve from a narrow task bundle into an **agent-first Bilibili client kernel**.

That means three layers:

1. **Core client capabilities**
   - auth
   - account / profile
   - search
   - feed / hot / rank / trends
   - video info / comments / interactions
   - dynamic / opus / note / session / inbox
   - publishing and management

2. **Operational intelligence**
   - digesting
   - audience profiling
   - creator-facing triage
   - configurable priority labeling
   - context-aware drafting

3. **OpenClaw orchestration**
   - cron
   - notification routing
   - memory / knowledge lookup
   - approval gates
   - multi-surface delivery

Keep layer 1 inside the skill.
Keep layers 2-3 mostly outside or only partially inside when they are genuinely Bilibili-native.

---

## Repo Signals from `Nemo2011/bilibili-api`

The upstream library already exposes broad capability modules, including:

- `video.py`
- `video_uploader.py`
- `dynamic.py`
- `opus.py`
- `note.py`
- `search.py`
- `user.py`
- `session.py`
- `comment.py`
- `favorite_list.py`
- `homepage.py`
- `hot.py`
- `rank.py`
- `topic.py`
- `creative_center.py`
- `article.py`
- `audio.py`
- `bangumi.py`
- `live.py`

So the opportunity is not “can we invent a client?”
The opportunity is: **can we wrap these modules into a stable operator-facing client surface?**

---

## Phase 1 — Harden the Existing Skill

### Goal
Make current operations reliable, explicit, and easier to extend.

### Work
- normalize auth and credential handling
- improve error surfaces and result schemas
- standardize JSON output shape
- separate read-only vs write actions clearly
- audit current modules:
  - operations
n  - publisher
  - subtitle
  - downloader
  - message_center
- add stronger action docs and examples
- add smoke tests for the most important actions

### First Targets
- video info
- comment list / reply / moderation
- dynamic post / delete / repost
- message center read paths
- publish/edit video flows already present or partially present

---

## Phase 2 — Expand Toward Real Client Surfaces

### Status
Substantially landed.

Second-phase pieces now in place:
- shared client base (`client_base.py`) for common auth / fetch helpers
- richer entity resolution for `dynamic` / `opus` / `note` / `article`
- stronger publisher flow with `preview_upload` and `inspect_video`
- thread-aware reply context assembly in `client_workflows.prepare_reply_context`
- `candidate_reply_input` for downstream reply generation
- partial-failure handling in user-intel so 412/risk failures degrade instead of exploding the whole workflow

### Goal
Fill the obvious client gaps.

### Candidate client modules

#### 1. Search client
Backed by `search.py`

Actions:
- search_videos
- search_users
- search_topics
- search_live
- search_by_type
- search_suggest

#### 2. User intel client
Backed by `user.py`, maybe `relation`-adjacent APIs if available

Actions:
- get_user_profile
- get_user_videos
- get_user_dynamics
- get_user_stats
- get_mutual_state / follow-state if supported
- summarize_user_presence

Purpose:
- audience profiling
- partner due diligence
- “见人说人话见鬼说鬼话” input shaping

#### 3. Dynamic / opus / note client
Backed by `dynamic.py`, `opus.py`, `note.py`

Actions:
- list_user_dynamics
- get_dynamic_detail
- list_opus
- get_note_detail
- interact_with_dynamic

#### 4. Feed / discovery client
Backed by `homepage.py`, `hot.py`, `rank.py`, `topic.py`

Actions:
- get_home_feed
- get_hot
- get_rank
- get_topic_detail
- get_trending_entities

#### 5. Session / DM client
Extend current message center around `session.py`

Actions:
- richer session listing
- parsed message content
- send richer message types later if safe
- thread summarization

#### 6. Creative center / creator analytics client
Backed by `creative_center.py`

Actions:
- get creator overview / compare windows
- get fan / audience trend signals
- get work / content performance panels
- get play / interaction / follower summaries
- normalize creator-facing KPIs for dashboard consumption

Purpose:
- operator dashboard input
- creator analytics snapshots
- campaign / posting feedback loops

Status:
- now moved into active Phase 3 execution as `creative_center_client.py`

---

## Phase 3 — Make It Feel Like a Client, Not an SDK Wrapper

### Status
Substantially landed.

Third-phase pieces now in place:
- `creative_center_client.py`
- `client_workflows.creator_dashboard_snapshot`
- `client_workflows.operator_dashboard_snapshot` alias
- `client_workflows.investigate_user` upgraded with creator metrics + audience-fit output
- `client_workflows.creator_task_queue` / `operator_task_queue`
- `client_workflows.recommend_reply_targets`
- `client_workflows.content_opportunity_brief`

### Goal
Wrap low-level actions into higher-level operator tasks.

### Examples
- `investigate_user`
  - profile
  - recent videos
  - recent dynamics
  - visible themes / likely intent
  - creator metrics
  - audience fit

- `prepare_reply_context`
  - fetch thread
  - fetch user info
  - fetch related content object
  - compact all into one operator-friendly payload
  - produce downstream `candidate_reply_input`

- `creator_dashboard_snapshot`
  - inbox
  - recent replies
  - top high-priority items
  - content performance signals
  - creative-center KPIs / creator analytics
  - current implementation already merges `message_center` + `creative_center`

- `creator_task_queue`
  - derive actionable reply / review / growth / conversion tasks
  - expose structured task items for later automation or human review

- `recommend_reply_targets`
  - rank who to answer next
  - expose reply strategy + why-now reasoning

- `content_opportunity_brief`
  - surface content worth amplifying / reviewing
  - normalize opportunity summaries for operator use

- `content_object_lookup`
  - accept BVID / dynamic ID / opus ID / user ID / URL
  - auto-resolve type
  - return normalized entity info

This is the point where it becomes a client kernel.

## Phase 4 — Audience / Intent Intelligence

### Status
Landed in initial productized form.

Phase-4 pieces now in place:
- `client_workflows.classify_inbound_intent`
- `client_workflows.operator_triage`
- `client_workflows.operator_decision_loop`
- `client_workflows.draft_reply_candidate`
- `client_workflows.send_or_queue_reply`
- structured `interest_profile` inside `prepare_reply_context`
- schema-tagged workflow outputs for downstream consumers
- direct-send for DMs plus conservative public reply auto-send only when thread mapping is proven
- automation-facing workflow entrypoints: `automation_brief` and `automation_tick` for cron/sub-agent orchestration

### Goal
Support context-sensitive creator operations.

Examples:
- classify inbound interest:
  - cooperation
  - licensing
  - support
  - fan praise
  - troll / low-value
- infer likely user role:
  - fan
  - creator
  - buyer
  - collaborator
  - scraper / spammy account
- attach operator hints:
  - tone suggestion
  - urgency
  - review required
  - safe canned references

Important:
These should remain **configurable heuristics**, not hardcoded truth claims.

## Phase 6 — Asset / Discovery Sync

### Status
Substantially landed for the first-tier target.

### Goal
Synchronize the next high-value Bilibili client surfaces that make this feel like a real operator product rather than an endpoint bundle.

### Batch A — Asset Surfaces
Priority: highest

Targets:
- favorites / favorite folders
- collections / channel series where practical
- watch-later

Why first:
- these are real account assets
- high operator value
- mature, stable API surface
- more product leverage than adding yet another hot-list endpoint

### Batch B — History / Interaction Memory
Priority: low / deferred

Targets:
- watch history
- recent interaction traces where API support is clean
- recently-viewed / recently-engaged summaries where normalization is useful

Note:
- explicitly deprioritized by Mozi
- not part of the current mainline delivery target
- only revisit if a concrete workflow later proves it necessary

### Batch C — Content Object Clients
Priority: high

Targets:
- dynamic client
- opus client
- note client
- article client

Status:
- landed as `content_client.py`
- readable/object actions include user-dynamics listing, dynamic detail/action, opus detail, note detail, user-article listing, and article detail
- workflow enrichment now consumes these object clients inside the reply decision loop

Why:
- resolver already exists, but object-level clients are still incomplete
- these should become first-class readable / operable / normalized modules

### Batch D — Feed / Discovery Client
Priority: medium-high

Targets:
- homepage / feed
- hot / rank / topic normalization
- discovery summaries and operator-facing digests

Status:
- landed as `discovery_client.py`
- current actions: `get_home_feed`, `get_hot`, `get_history_popular`, `get_rank`, `get_hot_topics`, `get_topic_detail`, `get_topic_cards`, `discovery_snapshot`
- upstream `get_hot_topics` is flaky/null-prone, and the client now soft-fails instead of taking down the whole discovery brief
- discovery signals are now consumed by `client_workflows.content_opportunity_brief`

Why:
- stronger product surface than isolated trending calls
- better discovery layer for downstream workflows

### Explicit Non-Priority
Not the current focus:
- more auth delivery-layer work for webchat
- expanding hot-list coverage just to add more endpoints

If someone asks for auth help later:
- prefer social-platform contact when image delivery matters
- otherwise recommend direct cookie/env setup

Current mainline focus:
- first-tier work only: asset surfaces + content-object clients + discovery layer
- second-tier/history-style work is explicitly non-essential for now

Adjacent realism enhancement (allowed, non-blocking):
- `emoji.py` integration as a lightweight native-expression layer for DM/comment/reply workflows
- use sparingly to feel like a real Bilibili user, not like an emoji spam bot

## Phase 7 — Live Orchestration / Streaming Control

### Status
Queued.

### Goal
Turn Bilibili live support into a real operator-facing orchestration layer instead of a pile of separate live/OBS helpers.

### Core tracks
- validate Bilibili live start/stop flows against real account behavior
- confirm whether `bilibili_api.live.LiveRoom.start()` exposes RTMP address / stream code directly in returned data
- add a dedicated `live_client` for room info, area info, announcement/news, moderation, danmaku, and high-sensitivity stream config access
- add an orchestration layer that can prepare/start/stop a live session end-to-end with OBS websocket control
- add live health/status checks so OpenClaw can distinguish “B站已开播 / OBS未推流 / OBS推流失败 / 状态分裂” instead of reporting fake success

### OBS integration track
- connect to OBS websocket first-class rather than shell-driving OBS blindly
- preflight stream configuration before start
- write RTMP server/key into OBS only after explicit confirmation
- support `start_live_session`, `stop_live_session`, and `live_health_check`
- detect and surface push failures, reconnect loops, and other output-state problems

### Live metadata / preflight track
- preview and edit live title / area / announcement before start
- add metadata sanitization / validation so special tags or risky text can be caught before OBS starts pushing
- keep write operations human-confirmed by default

### Current implemented status snapshot
- `obs_client` exists and already supports: status, stream-service inspection/update, start/stop stream, stop output, output list, current scene
- `live_orchestrator` exists and already supports: room profile, announcement update, pre-start patch planning, prepare/start/stop live session, health check
- `stop_live_session` can now fetch `StopLiveData` when given `live_key`, returning normalized summary + derived quality flags
- current confirmed live-metadata write surface:
  - announcement/news: **supported now** via `updateRoomNews`
  - title: **supported now** via `POST /room/v1/Room/update`
  - area: **supported as start-time patch** via `startLive(area_v2=...)`
- health checks now distinguish healthy vs split state vs transient stop-settling vs OBS reconnecting
- OBS stop path now treats `StopStream` 501 as idempotent and can fall back to `StopOutput("adv_stream")`

### Verification / QR presentation track
- support the real-world Bilibili “scan with mobile client” verification flow that may appear before live start (including face/identity verification or app-confirmed QR flows)
- treat this like auth QR presentation: default to social-platform delivery first; if that is unavailable, fall back to local image viewer / generated HTML / other operator-visible presentation paths
- do not bury these QR challenges in raw logs; surface them explicitly as operator action requirements

### Future live-agent track
- live danmaku loop agent for local-model classification / triage
- start with observation + highlighting, not autonomous replying
- later allow guarded semi-automatic assistance if it proves useful

## Architecture Rule

### Inside the skill
Keep:
- Bilibili-native actions
- entity lookup
- normalized data shaping
- safe task wrappers around upstream API modules

### Outside the skill
Keep:
- cron scheduling
- notification fan-out
- memory retrieval
- cross-channel routing
- approval policy
- speaker alerts

---

## Near-Term Build Order

1. Harden current skill outputs and error handling
2. Add `search_client`
3. Add `user_intel`
4. Add normalized entity resolver
5. Expand dynamic / opus / note coverage
6. Add operator-level composite actions
7. Add asset surfaces: favorites / collections / watch-later
8. Promote dynamic / opus / note / article into fuller object clients
9. Add unified feed / discovery client

Deferred unless later justified:
- history / interaction-memory surfaces

---

## Product Direction Statement

This should become:

**A programmable, agent-friendly Bilibili client kernel for creator operations, audience understanding, publishing, moderation, discovery, and messaging.**

Not just:

**a pile of scripts that can post and reply**.


## Live Operator Notes

Use this as the quick mental model for current live support:

- `get_live_room_profile` is the safest inspect-first entrypoint
- `pre_start_room_patch` is the safest place to stage announcement / area / title intent before start
- `prepare_live_session` is the safest preflight before touching OBS output state
- `start_live_session` returns the `live_key`; save it if you care about end-of-session stats
- `stop_live_session` should be given that `live_key` whenever possible so `StopLiveData` can be fetched
- title updates are now confirmed through `POST /room/v1/Room/update`; preserve returned `audit_info` because Bilibili may audit/normalize the title change
- if QR / face verification appears, surface it as operator action required; do not bury it in logs

Recommended field meanings for live stop summaries:
- `summary.duration_seconds` / `duration_minutes`: trusted only when non-negative
- `summary.watched_count`, `max_online`, `danmu_num`, `add_fans`, `new_fans_club`, `hamster_rmb`: useful session rollup
- `derived.quality_flags.invalid_duration`: Bilibili returned sentinel junk like `-999999`
- `derived.quality_flags.empty_session`: session appears structurally empty

## Automation / Cron Guidance

Preferred automation entrypoints:
- `client_workflows.automation_brief` for rich snapshots
- `client_workflows.automation_tick` for periodic checks and decision routing
- `client_workflows.reply_preview_card` + `approve_and_send_reply` for human-in-the-loop reply execution

Automation design rule:
- use **OpenClaw Cron Job**, not Unix cron, for OpenClaw-native automation scheduling
- keep scheduled jobs attached to stable workflow actions, not fragile low-level endpoint sequences
- let workflow outputs carry normalized schema tags and next-action queues so downstream agents stay thin
- default to review/queue semantics unless a send path is explicitly proven safe

Cron vs heartbeat rule of thumb:
- **Cron**: exact schedule, isolated automation runs, recurring digests, fixed interval inbox/task polling
- **Heartbeat**: drift-tolerant review sweeps, low-priority “check if anything matters”, batched scans that should stay quiet unless needed
- **Preview/approval path**: any reply flow that may actually send content

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
    "message": "Run: python main.py client_workflows automation_tick '{\"period\": \"week\", \"max_items\": 5, \"priority_threshold\": 80, \"mode\": \"review\"}'. Summarize top next action and keep replies on preview/approval.",
    "timeoutSeconds": 120
  },
  "delivery": {
    "mode": "announce"
  }
}
```
