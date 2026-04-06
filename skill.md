---
name: bilibili-all-in-one
description: >
  A Bilibili creator-operations toolkit for account/community workflows:
  follower management, video likes, comment/reply handling, dynamic posting,
  dynamic repost/delete, space-notice updates, plus download/watch/subtitle/
  publishing support. Use when operating a Bilibili creator account or doing
  audience/community management with authenticated cookies.
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

# Bilibili All-in-One Skill

A comprehensive Bilibili toolkit that integrates hot trending monitoring, video downloading, video watching/playback, subtitle downloading, and video publishing capabilities into a single unified skill.

> **⚠️ Optional Environment Variables:** `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT` (optional), `BILIBILI_BUVID3` (optional), `BILIBILI_PERSIST` (optional)
> These are sensitive Bilibili session cookies needed **only** for publishing and high-quality (1080p+/4K) downloads.
> **Most features work WITHOUT any credentials:** hot monitoring, standard-quality downloads, subtitle listing, danmaku, stats viewing.
>
> **📦 Install:** `pip install -r requirements.txt` (all standard PyPI packages: httpx, aiohttp, beautifulsoup4, lxml, requests)
>
> **🔗 Source:** [github.com/wscats/bilibili-all-in-one](https://github.com/wscats/bilibili-all-in-one)

---
### 何时激活

当用户**明确请求**以下 Bilibili 相关操作时，本 Skill 可被激活：

| 触发场景 | 匹配的模块 | 典型触发词 |
|---|---|---|
| 查看B站热门、热搜、排行榜、必看榜 | 🔥 Hot Monitor | "热门"、"热搜"、"排行"、"趋势"、"必看"、"流行"、"榜单" |
| 下载B站视频、提取音频、批量下载 | ⬇️ Downloader | "下载"、"保存视频"、"提取音频"、"导出MP4"、"批量下载" |
| 查看视频播放量、点赞数、数据追踪、对比 | 👀 Watcher | "播放量"、"点赞"、"数据"、"统计"、"对比"、"监控"、"追踪"、"观看量" |
| 下载字幕、转换字幕格式、合并字幕 | 📝 Subtitle | "字幕"、"CC"、"SRT"、"ASS"、"字幕下载"、"字幕转换"、"翻译" |
| 播放视频、获取弹幕、播放列表 | ▶️ Player | "播放"、"弹幕"、"播放地址"、"分P"、"播放列表"、"danmaku" |
| 上传视频、发布、定时发布、草稿、编辑 | 📤 Publisher | "上传"、"发布"、"投稿"、"定时发布"、"草稿"、"编辑视频" |
| 粉丝运营、评论管理、回复评论、点赞视频、发动态、删动态、空间公告 | 💼 Operations | "运营"、"粉丝"、"评论"、"回复评论"、"点赞"、"发动态"、"删动态"、"关注"、"移除粉丝"、"公告" |
| 私信/评论/@我/赞我/系统通知收件箱 | 📬 Message Center | "消息中心"、"私信"、"评论通知"、"@我"、"赞我"、"未读"、"通知"、"收件箱" |

> ⚠️ **注意**：本 Skill 不会仅因消息中出现 Bilibili 链接或 BV 号就自动激活。只有当用户明确表达了操作意图（如"下载这个视频"、"查看热门"等）时才会被调用。涉及写操作（发布/编辑）时，需要用户显式提供凭证。

---

## Features
| Module | Description |
|---|---|
| 🔥 **Hot Monitor** | Monitor Bilibili hot/trending videos and topics in real-time |
| ⬇️ **Downloader** | Download Bilibili videos with multiple quality and format options |
| 👀 **Watcher** | Watch and track video engagement metrics (supports Bilibili) |
| 📝 **Subtitle** | Download and process subtitles in multiple formats and languages |
| ▶️ **Player** | Get playback URLs, danmaku (bullet comments), and playlist info |
| 📤 **Publisher** | Upload, schedule, edit, and manage videos on Bilibili |
| 💼 **Operations** | Community/account operations: followers, comments, likes, dynamics, notices |
| 📬 **Message Center** | Inbox + DM workflow for reading sessions/history, sending plain-text DMs, replies, @mentions, likes, unread counts, and system notifications |

## Installation

### Requirements

- Python >= 3.8
- ffmpeg (optional, for merging video/audio streams)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Dependencies

- `httpx >= 0.24.0`
- `aiohttp >= 3.8.0`
- `beautifulsoup4 >= 4.12.0`
- `lxml >= 4.9.0`
- `requests >= 2.31.0`

## Configuration

Some features (downloading high-quality videos, publishing, etc.) require Bilibili authentication. You can provide credentials in three ways:

### 1. Environment Variables

```bash
export BILIBILI_SESSDATA="your_sessdata"
export BILIBILI_BILI_JCT="your_bili_jct"
export BILIBILI_BUVID3="your_buvid3"
```

### 2. Credential File

Create a JSON file (e.g., `credentials.json`):

```json
{
  "sessdata": "your_sessdata",
  "bili_jct": "your_bili_jct",
  "buvid3": "your_buvid3"
}
```

### 3. Direct Parameters

Pass credentials directly when initializing:

```python
from main import BilibiliAllInOne

app = BilibiliAllInOne(
    sessdata="your_sessdata",
    bili_jct="your_bili_jct",
    buvid3="your_buvid3",
)
```

### 4. Persistent Storage (Optional)

By default, credentials are kept **in-memory only** and are not saved to disk. To enable automatic persistence across sessions:

```bash
# Via environment variable
export BILIBILI_PERSIST=1
```

```python
# Or via code
app = BilibiliAllInOne(persist=True)
```

When persistence is enabled:
- Credentials are auto-saved to `.credentials.json` (with `0600` permissions) after initialization
- On next startup, credentials are auto-loaded from this file
- You can toggle persistence at runtime: `app.auth.persist = True` / `app.auth.persist = False`
- To delete the persisted file: `app.auth.clear_persisted()`

> **How to get cookies:** Log in to [bilibili.com](https://www.bilibili.com), open browser DevTools (F12) → Application → Cookies, and copy the values of `SESSDATA`, `bili_jct`, and `buvid3`.

## ⚠️ Security & Privacy

### Credential Handling

This skill handles **sensitive Bilibili session cookies**. Please read the following carefully:

| Concern | Detail |
|---|---|
| **What credentials are needed?** | `SESSDATA`, `bili_jct`, `buvid3` — Bilibili **full browser session cookies** (not limited API keys). Providing them grants broad access to your Bilibili account. |
| **Which features require authentication?** | Publishing (upload/edit/schedule/draft), downloading 1080p+/4K quality videos |
| **Which features work WITHOUT credentials?** | Hot monitoring, standard-quality downloads, subtitle listing, danmaku fetching, stats viewing |
| **Where are credentials sent?** | To official Bilibili API endpoints (`api.bilibili.com`, `member.bilibili.com`) over HTTPS only |
| **Are credentials persisted to disk?** | **NO** by default — credentials stay in memory. Set `persist=True` or `BILIBILI_PERSIST=1` to opt-in to automatic persistence (saved to `.credentials.json` with `0600` permissions). You can also manually call `auth.save_to_file()` |
| **File permissions for saved credentials** | `0600` (owner read/write only) — restrictive by default |

### Best Practices

1. 🧪 **Use a test account** — Do NOT provide your primary Bilibili account cookies for evaluation/testing purposes. These are **full session cookies** that grant broad account access (not limited API keys).
2. 🔒 **Prefer in-memory credentials** — Pass credentials via environment variables or direct parameters rather than saving to a file. Only enable `persist=True` if you need credentials to survive across sessions.
3. 📁 **If you enable persistence** — Credentials are saved with `0600` permissions. Use `auth.clear_persisted()` or `auth.persist = False` to remove the file when no longer needed.
4. 🐳 **Run in isolation** — When possible, run this skill in an isolated container/environment and inspect network traffic.
5. 🌐 **Verify network traffic** — All HTTP requests go to Bilibili's official domains only. You can verify by monitoring outbound connections.
6. ❌ **No exfiltration** — This skill does NOT send credentials to any third-party service, analytics endpoint, or telemetry server.
7. 🔑 **Credential scope** — `SESSDATA` and `bili_jct` are full session cookies. They are NOT scoped/limited API keys. Treat them with the same care as your account password.

### Network Endpoints Used

| Domain | Purpose |
|---|---|
| `api.bilibili.com` | Video info, stats, hot lists, subtitles, danmaku, playback URLs |
| `member.bilibili.com` | Video publishing (upload, edit) |
| `upos-sz-upcdnbda2.bilivideo.com` | Video file upload CDN |
| `www.bilibili.com` | Web page scraping fallback |

### Credential Requirement by Module

| Module | Auth Required? | Notes |
|---|---|---|
| 🔥 Hot Monitor | ❌ No | All public APIs |
| ⬇️ Downloader | ⚠️ Optional | Required only for 1080p+ / 4K quality |
| 👀 Watcher | ❌ No | Public stats APIs |
| 📝 Subtitle | ❌ No | Public subtitle APIs |
| ▶️ Player | ⚠️ Optional | Required for high-quality playback URLs |
| 📤 Publisher | ✅ **Required** | All operations need `SESSDATA` + `bili_jct` |
| 💼 Operations | ✅ **Required** | Follow/remove-fan, like, comment/reply, dynamic posting, space notice |
| 📬 Message Center | ✅ **Required** | Creator inbox polling, DM history, plain-text DM send, and automation entrypoints |

## Usage

### CLI

```bash
python main.py <skill_name> <action> [params_json]
```

For creator/account operations, use `operations` / `ops` as the module name.

### Python API

```python
import asyncio
from main import BilibiliAllInOne

app = BilibiliAllInOne()

async def demo():
    result = await app.execute("hot_monitor", "get_hot", limit=5)
    print(result)

asyncio.run(demo())
```

### Operations Quick Examples

```bash
# Verify authenticated creator account
python main.py operations verify_auth

# List followers
python main.py operations list_followers '{"page": 1, "page_size": 20}'

# Follow / remove fan
python main.py operations follow_user '{"uid": 123456}'
python main.py operations remove_fan '{"uid": 123456}'

# Like a video
python main.py operations like_video '{"bvid": "BV1xx411c7mD"}'

# List comments and reply to one
python main.py operations list_video_comments '{"bvid": "BV1xx411c7mD", "page": 1}'
python main.py operations reply_video_comment '{"bvid": "BV1xx411c7mD", "text": "感谢支持", "root": 123456789, "parent": 123456789}'

# Comment moderation
python main.py operations like_comment '{"oid": 243922477, "resource_type": "video", "rpid": 123456789}'
python main.py operations pin_comment '{"oid": 243922477, "resource_type": "video", "rpid": 123456789}'
python main.py operations delete_comment '{"oid": 243922477, "resource_type": "video", "rpid": 123456789}'

# Dynamics
python main.py operations post_dynamic '{"text": "今晚八点直播，来。"}'
python main.py operations repost_dynamic '{"dynamic_id": 1234567890123456789, "text": "这个值得一看"}'
python main.py operations delete_dynamic '{"dynamic_id": 1234567890123456789}'

# Space notice
python main.py operations set_space_notice '{"content": "合作请私信 / 直播时间见动态"}'
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
# Default config file: ~/.openclaw/workspace/bilibili-message-center.json (actual workspace root file)
# Template reference: skills/bilibili-all-in-one/config/message-center.example.json
# Optional override: export BILIBILI_MESSAGE_CENTER_CONFIG=/path/to/override.json

# System notifications
python main.py message_center system_messages
```

### Client Workflows Quick Examples

```bash
# Resolve a content object into a normalized entity + lookup bundle
python main.py client_workflows content_object_lookup '{"target": "https://www.bilibili.com/opus/1187451323683962904"}'

# Build reply/thread context for a latest reply / @ mention / DM flow
python main.py client_workflows prepare_reply_context '{"source": "reply", "limit": 3}'
python main.py client_workflows prepare_reply_context '{"source": "at", "limit": 3}'
python main.py client_workflows prepare_reply_context '{"source": "dm", "receiver_id": 123456, "limit": 20}'

# Operator / creator dashboard snapshot
python main.py client_workflows creator_dashboard_snapshot '{"period": "week", "max_items": 5}'
# Alias
python main.py client_workflows operator_dashboard_snapshot '{"period": "week", "max_items": 5}'
```

### Creative Center Quick Examples

```bash
# Creator analytics overview
python main.py creative_center overview '{"period": "week"}'
python main.py creative_center compare
python main.py creative_center graph '{"period": "week", "graph_type": "play"}'

# Audience / fan analytics
python main.py creative_center fan_overview '{"period": "week"}'
python main.py creative_center fan_graph '{"period": "week", "graph_type": "all_fans"}'

# Content analytics panels
python main.py creative_center video_survey
python main.py creative_center video_playanalysis '{"copyright": "all"}'

# Unified creator analytics snapshot for dashboards
python main.py creative_center dashboard_snapshot '{"period": "week"}'
```

---

## Skills Reference

### 1. 🔥 Hot Monitor (`bilibili_hot_monitor`)

Monitor Bilibili hot/trending videos and topics in real-time. Supports filtering by category, tracking rank changes.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `get_hot` | Get popular/hot videos | `page`, `page_size` |
| `get_trending` | Get trending series/topics | `limit` |
| `get_weekly` | Get weekly must-watch list | `number` (week number, optional) |
| `get_rank` | Get category ranking videos | `category`, `limit` |

#### Supported Categories

`all`, `anime`, `music`, `dance`, `game`, `tech`, `life`, `food`, `car`, `fashion`, `entertainment`, `movie`, `tv`

#### Examples

```bash
# Get top 10 hot videos
python main.py hot_monitor get_hot '{"page_size": 10}'

# Get trending topics
python main.py hot_monitor get_trending '{"limit": 5}'

# Get this week's must-watch
python main.py hot_monitor get_weekly

# Get game category rankings
python main.py hot_monitor get_rank '{"category": "game", "limit": 10}'
```

```python
# Python API
result = await app.execute("hot_monitor", "get_hot", page_size=10)
result = await app.execute("hot_monitor", "get_rank", category="game", limit=10)
```

---

### 1.5 🧠 Client Workflows (`client_workflows`)

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
- `creator_dashboard_snapshot` merges `message_center` + `creative_center`
- `creator_task_queue` produces structured work items with `type`, `priority`, `risk`, `reason`, and `payload`
- Workflow actions increasingly include a `schema` field like `bilibili.client_workflows.<action>.v1` for downstream consumers
- Use this layer when the task is operational, not just raw endpoint access

---

### 1.6 📈 Creative Center (`creative_center`)

Creator analytics client backed by `bilibili_api.creative_center`, intended for operator dashboards, KPI snapshots, and creator-performance workflows.

#### High-value actions

| Action | Description |
|---|---|
| `overview` | Creator overview metrics for a time window |
| `compare` | Compare-period metrics |
| `graph` | Graph series by metric type |
| `fan_overview` | Fan / audience summary |
| `fan_graph` | Fan trend graph |
| `video_survey` | Content survey panel |
| `video_playanalysis` | Play-analysis panel |
| `dashboard_snapshot` | Unified creative-center KPI snapshot |

#### Notes

- Period values map to creative-center enums like `week`, `month`, `three_month`, `total`
- `dashboard_snapshot` is the preferred input for creator/operator dashboards
- If Bilibili auth or creator permissions are missing, expect structured failure output instead of raw tracebacks

---

### 2. ⬇️ Downloader (`bilibili_downloader`)

Download Bilibili videos with support for multiple quality options, batch downloading, and format selection.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `get_info` | Get video information | `url` |
| `get_formats` | List available qualities/formats | `url` |
| `download` | Download a single video | `url`, `quality`, `output_dir`, `format`, `page` |
| `batch_download` | Download multiple videos | `urls`, `quality`, `output_dir`, `format` |

#### Quality Options

`360p`, `480p`, `720p`, `1080p` (default), `1080p+`, `4k`

#### Format Options

`mp4` (default), `flv`, `mp3` (audio only)

#### Examples

```bash
# Get video info
python main.py downloader get_info '{"url": "BV1xx411c7mD"}'

# List available formats
python main.py downloader get_formats '{"url": "BV1xx411c7mD"}'

# Download in 1080p MP4
python main.py downloader download '{"url": "BV1xx411c7mD", "quality": "1080p", "format": "mp4"}'

# Extract audio only
python main.py downloader download '{"url": "BV1xx411c7mD", "format": "mp3"}'

# Batch download
python main.py downloader batch_download '{"urls": ["BV1xx411c7mD", "BV1yy411c8nE"], "quality": "720p"}'
```

```python
# Python API
info = await app.execute("downloader", "get_info", url="BV1xx411c7mD")
result = await app.execute("downloader", "download", url="BV1xx411c7mD", quality="1080p")
```

---

### 3. 👀 Watcher (`bilibili_watcher`)

Watch and monitor Bilibili videos. Track view counts, comments, likes, and other engagement metrics over time.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `watch` | Get detailed video information | `url` |
| `get_stats` | Get current engagement statistics | `url` |
| `track` | Track metrics over time | `url`, `interval` (minutes), `duration` (hours) |
| `compare` | Compare multiple videos | `urls` |

#### Supported Platforms

- **Bilibili**: `https://www.bilibili.com/video/BVxxxxxx` or `BVxxxxxx`

#### Examples

```bash
# Get video details
python main.py watcher watch '{"url": "BV1xx411c7mD"}'

# Get current stats
python main.py watcher get_stats '{"url": "BV1xx411c7mD"}'

# Track views every 30 minutes for 12 hours
python main.py watcher track '{"url": "BV1xx411c7mD", "interval": 30, "duration": 12}'

# Compare multiple videos
python main.py watcher compare '{"urls": ["BV1xx411c7mD", "BV1yy411c8nE"]}'
```

```python
# Python API

comparison = await app.execute("watcher", "compare", urls=["BV1xx411c7mD", "BV1yy411c8nE"])
```

---

### 4. 📝 Subtitle (`bilibili_subtitle`)

Download and process subtitles/CC from Bilibili videos. Supports multiple subtitle formats and languages.

**When no CC subtitles are available**, the module falls back to:
1. **Local STT API** — Downloads the video's audio, converts it to wav, and sends it to the local OpenAI-compatible STT endpoint using model path `./models/Qwen3-ASR-0.6B-bf16`
2. **Danmaku Extraction** — Fetches bullet comments from the video as a text reference

Whisper/faster-whisper fallback was intentionally removed because low-quality output produced misleading subtitles. When debugging or changing this path, explicitly use the `local-stt-workflow` skill instead of reintroducing Whisper.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `list` | List available subtitles | `url` |
| `download` | Download subtitles (with auto-fallback) | `url`, `language`, `format`, `output_dir` |
| `convert` | Convert subtitle format | `input_path`, `output_format`, `output_dir` |
| `merge` | Merge multiple subtitle files | `input_paths`, `output_path`, `output_format` |

#### Supported Formats

`srt` (default), `ass`, `vtt`, `txt`, `json`

#### Supported Languages

`zh-CN` (default), `en`, `ja`, and other language codes available on the video.

#### Fallback Strategy

When `download` is called and no CC subtitles exist:

```
CC Subtitle Available? ──Yes──▶ Download CC subtitle
        │
       No
        │
        ▼
┌─────────────────────────────────────┐
│  Fallback 1: Local STT API          │
│  Download audio → wav → local STT   │
│  Output: {title}_local_stt.srt      │
├─────────────────────────────────────┤
│  Fallback 2: Danmaku Extraction     │
│  Fetch bullet comments → SRT        │
│  Output: {title}_danmaku.srt        │
└─────────────────────────────────────┘
```

#### Examples

```bash
# List available subtitles
python main.py subtitle list '{"url": "BV1xx411c7mD"}'

# Download Chinese subtitles in SRT format (auto-fallback if no CC)
python main.py subtitle download '{"url": "BV1xx411c7mD", "language": "zh-CN", "format": "srt"}'

# Download English subtitles in ASS format
python main.py subtitle download '{"url": "BV1xx411c7mD", "language": "en", "format": "ass"}'

# Convert SRT to VTT
python main.py subtitle convert '{"input_path": "./subtitles/video.srt", "output_format": "vtt"}'

# Merge subtitle files
python main.py subtitle merge '{"input_paths": ["part1.srt", "part2.srt"], "output_path": "merged.srt"}'
```

```python
# Python API
subs = await app.execute("subtitle", "list", url="BV1xx411c7mD")
result = await app.execute("subtitle", "download", url="BV1xx411c7mD", language="zh-CN", format="srt")

# When no CC subtitles, result may include both fallback outputs:
# result["transcription"]["filepath"]  → local STT SRT
# result["danmaku"]["filepath"]        → danmaku SRT
```

---

### 5. ▶️ Player (`bilibili_player`)

Play Bilibili videos with support for playback control, playlist management, and danmaku (bullet comments) display.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `play` | Get complete playback info | `url`, `quality`, `page` |
| `get_playurl` | Get direct play URLs | `url`, `quality`, `page` |
| `get_danmaku` | Get danmaku/bullet comments | `url`, `page`, `segment` |
| `get_playlist` | Get playlist/multi-part info | `url` |

#### Danmaku Modes

| Mode | Description |
|---|---|
| 1 | Scroll (right to left) |
| 4 | Bottom fixed |
| 5 | Top fixed |

#### Examples

```bash
# Get playback info
python main.py player play '{"url": "BV1xx411c7mD", "quality": "1080p"}'

# Get direct play URLs
python main.py player get_playurl '{"url": "BV1xx411c7mD", "quality": "720p"}'

# Get danmaku
python main.py player get_danmaku '{"url": "BV1xx411c7mD"}'

# Get playlist for multi-part video
python main.py player get_playlist '{"url": "BV1xx411c7mD"}'

# Get page 3 of a multi-part video
python main.py player play '{"url": "BV1xx411c7mD", "quality": "1080p", "page": 3}'
```

```python
# Python API
play_info = await app.execute("player", "play", url="BV1xx411c7mD", quality="1080p")
danmaku = await app.execute("player", "get_danmaku", url="BV1xx411c7mD")
playlist = await app.execute("player", "get_playlist", url="BV1xx411c7mD")
```

---

### 6. 📤 Publisher (`bilibili_publisher`)

Publish videos to Bilibili. Supports uploading videos, setting metadata, scheduling publications, and managing drafts.

> ⚠️ **Authentication Required**: All publisher actions require valid Bilibili credentials.

#### Actions

| Action | Description | Parameters |
|---|---|---|
| `upload` | Upload and publish a video | `file_path`, `title`, `description`, `tags`, `category`, `cover_path`, `dynamic`, `no_reprint`, `open_elec` |
| `draft` | Save as draft | `file_path`, `title`, `description`, `tags`, `category`, `cover_path` |
| `schedule` | Schedule future publication | `file_path`, `title`, `schedule_time`, `description`, `tags`, `category`, `cover_path` |
| `edit` | Edit existing video metadata | `bvid`, `file_path`, `title`, `description`, `tags`, `cover_path` |

#### Upload Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `file_path` | string | *required* | Path to the video file |
| `title` | string | *required* | Video title (max 80 chars) |
| `description` | string | `""` | Video description (max 2000 chars) |
| `tags` | string[] | `["bilibili"]` | Tags (max 12, each max 20 chars) |
| `category` | string | `"171"` | Category TID |
| `cover_path` | string | `null` | Path to cover image (JPG/PNG) |
| `no_reprint` | int | `1` | 1 = original content, 0 = repost |
| `open_elec` | int | `0` | 1 = enable charging, 0 = disable |

#### Examples

```bash
# Preflight a publish without actually submitting
python main.py publisher preview_upload '{"file_path": "./video.mp4", "title": "My Video"}'

# Inspect an existing video before edit flows
python main.py publisher inspect_video '{"bvid": "BV1xx411c7mD"}'

# Upload and publish
python main.py publisher upload '{"file_path": "./video.mp4", "title": "My Video", "description": "Hello World", "tags": ["test", "demo"], "category": "171"}'

# Save as draft
python main.py publisher draft '{"file_path": "./video.mp4", "title": "Draft Video"}'

# Schedule publication
python main.py publisher schedule '{"file_path": "./video.mp4", "title": "Scheduled Video", "schedule_time": "2025-12-31T20:00:00+08:00"}'

# Edit video metadata (requires re-uploading the video file)
python main.py publisher edit '{"bvid": "BV1xx411c7mD", "file_path": "./video.mp4", "title": "New Title", "tags": ["updated"]}'
```

```python
# Python API (authentication required)
app = BilibiliAllInOne(sessdata="xxx", bili_jct="xxx", buvid3="xxx")

result = await app.execute("publisher", "preview_upload",
    file_path="./video.mp4",
    title="My Video",
)

result = await app.execute("publisher", "upload",
    file_path="./video.mp4",
    title="My Video",
    description="Published via bilibili-all-in-one",
    tags=["python", "bilibili"],
)

# Edit video (requires file_path for re-upload)
result = await app.execute("publisher", "edit",
    bvid="BV1xx411c7mD",
    file_path="./video.mp4",
    title="New Title",
    tags=["updated"],
)
```

Notes:
- `preview_upload` is the safest first step for operator workflows
- `inspect_video` is useful before edit/update flows
- publisher success payloads may include `mode` and `stage`
- publisher failures are increasingly structured with `stage`, `error_type`, `message`, and optional `detail`

---

## Project Structure

```
bilibili-all-in-one/
├── skill.json              # Skill configuration & parameter schema
├── skill.md                # This documentation file
├── README.md               # Project README (Chinese)
├── LICENSE                  # MIT-0 License
├── requirements.txt        # Python dependencies
├── .gitignore              # Git ignore rules
├── main.py                 # Entry point & unified BilibiliAllInOne class
└── src/
    ├── __init__.py         # Package exports
    ├── auth.py             # Authentication & credential management
    ├── utils.py            # Shared utilities, API constants, helpers
    ├── hot_monitor.py      # Hot/trending video monitoring
    ├── downloader.py       # Video downloading
    ├── watcher.py          # Video watching & stats tracking
    ├── client_base.py      # Shared auth/fetch helpers
    ├── client_workflows.py # Composite workflow layer
    ├── creative_center_client.py # Creator analytics / KPI client
    ├── subtitle.py         # Subtitle downloading & processing
    ├── player.py           # Video playback & danmaku
    └── publisher.py        # Video uploading & publishing
```

## Response Format

All skill actions return a JSON object with a unified structure:

```json
{
  "success": true,
  "...": "action-specific fields"
}
```

On error:

```json
{
  "success": false,
  "message": "Error description",
  "stage": "validate|inspect|submit|...",
  "error_type": "validation_error|file_missing|api_error|risk_control|non_json_response|..."
}
```

Some composite workflow actions also return higher-level helper payloads:
- `prepare_reply_context` → `thread_context`, `reply_guidance`, `candidate_reply_input`
- `creator_dashboard_snapshot` → merged inbox / priority / creative-center dashboard bundle
- publisher actions → `mode`, `stage`, and richer result metadata

## License

MIT
