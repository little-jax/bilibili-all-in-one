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
- structured `interest_profile` inside `prepare_reply_context`
- schema-tagged workflow outputs for downstream consumers

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

---

## Product Direction Statement

This should become:

**A programmable, agent-friendly Bilibili client kernel for creator operations, audience understanding, publishing, moderation, discovery, and messaging.**

Not just:

**a pile of scripts that can post and reply**.
