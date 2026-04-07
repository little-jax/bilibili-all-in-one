
<p align="center">
  <h1 align="center">🎬 Bilibili All-in-One</h1>
  <p align="center">一站式 B站工具箱 — 热门监控 · 视频下载 · 数据追踪 · 字幕提取 · 视频播放 · 投稿发布</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-%3E%3D3.8-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT--0-green" />
  <img src="https://img.shields.io/badge/version-1.0.18-orange" />
  <img src="https://img.shields.io/badge/platform-Bilibili-pink" />
</p>

---

> Fork / ownership note:
> - Current maintained version in this workspace: **Little Jax / Mozi A.**
> - Published fork / reference repo: **https://github.com/little-jax/bilibili-all-in-one**
> - Original upstream author: **wscats**
> - Upstream source is preserved for attribution; this workspace copy is now independently maintained and extended.

## 🚀 Why this fork is powerful

This is not just a bag of Bilibili scripts anymore. The maintained OpenClaw fork now behaves like a compact creator-ops platform:

- **Creator operations**: followers, comments, moderation, dynamics, space notice, and authenticated account workflows
- **Inbox / DM surface**: replies, mentions, likes, sessions, DM history, inbox digests, priority filtering, and automation snapshots
- **Search + entity resolution**: resolve BV / UID / opus / dynamic / note / article targets into normalized objects
- **Creator intelligence**: investigate a user with profile, recent content, creator metrics, audience-fit hints, and a compact briefing
- **Reply preparation**: build thread-aware `reply_guidance` and `candidate_reply_input` that downstream agents can actually use
- **Operator triage**: classify inbound intent, estimate urgency, suggest tone, and flag review-required cases
- **Reply execution loop**: `operator_decision_loop` → `draft_reply_candidate` → `send_or_queue_reply`
- **Safe public auto-send**: DMs can send directly; public reply auto-send only fires when thread mapping is proven from reply metadata
- **Automation-facing workflows**: `automation_brief` and `automation_tick` give cron/sub-agent friendly snapshots and next-action queues
- **Live orchestration**: Bilibili live preflight/start/stop, RTMP retrieval validation, OBS websocket control, room-profile inspection, announcement updates, pre-start patch planning, and stop-session summary stats (`StopLiveData`)
- **Dashboard / analytics**: KPI snapshots, reply target ranking, task queues, and content opportunity briefs
- **Asset surfaces**: video favorite folders, watch-later, and channel-series collections
- **Native emoji surface**: inspect and suggest built-in Bilibili emoji packs for more natural-feeling replies/DMs
- **Content-object surface**: treat dynamics, opus, notes, and articles as first-class objects instead of URL crumbs, including unified image extraction (`images`, `primary_image`) for better reply context
- **Unified discovery surface**: homepage feed, hot videos, rank, and topic workflows behind one client instead of scattered modules
- **Productized outputs**: high-level workflows expose stable schema tags like `bilibili.client_workflows.<action>.v1`

In short: it now feels like a real operator-facing skill, not a random endpoint wrapper.

## Quick Power Showcase

```bash
# Investigate a creator with profile + recent content + creator metrics
python main.py client_workflows investigate_user '{"uid": 434156493, "include_creator_metrics": true, "period": "week"}'

# Inspect / patch / run live orchestration
python main.py live_orchestrator get_live_room_profile
python main.py live_orchestrator pre_start_room_patch '{"announcement": "今晚八点，来。", "area_id": 216}'
python main.py live_orchestrator prepare_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'
python main.py live_orchestrator start_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "auto_start_obs": true}'
python main.py live_orchestrator stop_live_session '{"live_key": "<live_key>", "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'

# Build reply-ready context from the latest reply thread
python main.py client_workflows prepare_reply_context '{"source": "reply", "limit": 3}'

# Classify inbound intent and produce operator triage
python main.py client_workflows classify_inbound_intent '{"text": "想合作推广一下这个项目", "target": "https://www.bilibili.com/video/BV1KQPyzcEhH"}'
python main.py client_workflows operator_triage '{"source": "reply", "limit": 5}'
python main.py client_workflows operator_decision_loop '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows draft_reply_candidate '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目"}'
python main.py client_workflows send_or_queue_reply '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "execute_send": false, "force_public_send": true}'
python main.py client_workflows reply_preview_card '{"source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "force_public_send": true}'
python main.py client_workflows approve_and_send_reply '{"approved": true, "source": "reply", "limit": 5, "text": "想合作推广一下这个项目", "force_public_send": true}'

# Cron / agent friendly automation snapshot
python main.py client_workflows automation_brief '{"period": "week", "max_items": 5, "priority_threshold": 80}'
python main.py client_workflows automation_tick '{"period": "week", "max_items": 5, "priority_threshold": 80, "mode": "review"}'

# Build dashboard / queue / opportunity views
python main.py client_workflows creator_dashboard_snapshot '{"period": "week", "max_items": 5}'
python main.py client_workflows creator_task_queue '{"period": "week", "max_items": 5}'
python main.py client_workflows content_opportunity_brief '{"period": "week", "max_items": 5}'

# Work with account assets
python main.py asset_client list_video_favorite_lists '{"uid": 434156493}'
python main.py asset_client get_video_favorite_list_content '{"media_id": 123456}'
python main.py asset_client list_watch_later
python main.py emoji_client suggest_emojis '{"business": "reply", "query": "doge", "limit": 5}'
python main.py content_client list_user_dynamics '{"uid": 434156493}'
python main.py content_client list_user_articles '{"uid": 434156493}'
python main.py discovery_client discovery_snapshot
python main.py discovery_client get_hot '{"page_size": 5}'
```

## 📖 简介

**Bilibili All-in-One** 是一个综合性的 B站工具包，将 6 个独立的 B站技能整合为一个统一的 Skill，提供从热门监控到视频投稿的全链路能力。

支持作为 **AI Agent 技能**、**命令行工具** 或 **Python 库** 使用。

## ✨ 功能总览

| 模块 | 功能 | 是否需要登录 |
|:---:|---|:---:|
| 🔥 **热门监控** | 热门视频、热搜话题、每周必看、分区排行榜 | ❌ |
| ⬇️ **视频下载** | 多清晰度下载、批量下载、格式转换、音频提取 | ⚠️ 高清需要 |
| 👀 **数据追踪** | 播放/点赞/收藏统计、数据追踪、多视频对比 | ❌ |
| 📝 **字幕提取** | 字幕下载、格式转换（SRT/ASS/VTT/TXT）、多语言、字幕合并 | ❌ |
| ▶️ **视频播放** | 播放地址获取、弹幕抓取、分P/播放列表信息 | ⚠️ 高清需要 |
| 📤 **视频发布** | 上传投稿、定时发布、草稿管理、编辑视频 | ✅ 必须 |
| 🗂️ **资产面** | 收藏夹、稍后再看、合集/系列管理 | ⚠️ 需要账号 |
| 🔐 **认证工作流** | QR 登录、登录状态检查、会话清理、持久化控制 | ⚠️ 推荐 QR |

## 🚀 快速开始

### 环境要求

- **Python** >= 3.8
- **ffmpeg**（可选，用于合并视频/音频流）

### 安装依赖

```bash
# Maintained fork / reference repo
git clone https://github.com/little-jax/bilibili-all-in-one.git
cd bilibili-all-in-one
pip install -r requirements.txt
```

> This workspace version is a maintained fork/adaptation. If you are working inside Mozi's OpenClaw workspace, prefer the local checked-out copy rather than recloning upstream.

### 30 秒上手

```python
import asyncio
from main import BilibiliAllInOne

app = BilibiliAllInOne()

async def main():
    # 获取 B站热门视频
    hot = await app.execute("hot_monitor", "get_hot", page_size=5)
    print(hot)

asyncio.run(main())
```

## 🔐 Auth Productization

QR login is the preferred path. Default behavior is to generate a QR image and send/show that image directly. Only fall back to HTML / local page / raw URL / other presentation methods when the current session cannot display images or the user explicitly asks for another path.

High-value auth actions:

- `auth_client start_qr_login` → generate QR assets (`image_path`, `html_path`, `qr_url`) plus `agent_delivery` hints
- `auth_client poll_qr_login` → poll state and finalize login
- `auth_client verify_auth` → verify current session
- `auth_client describe_auth` → inspect auth/session/runtime paths
- `auth_client clear_auth` → clear persisted/runtime auth state

Recommended presentation order:

1. **Send/show QR PNG directly**
2. If images are not visible in the current session, open/use the generated local HTML file
3. Use raw `qr_url` if HTML presentation is also unavailable
4. Only treat ASCII as a weak fallback, not the default operator experience

## ⚙️ 配置认证

部分功能（高清下载、视频发布等）需要 B站登录凭据。支持三种配置方式：

### 方式一：环境变量（推荐）

```bash
export BILIBILI_SESSDATA="你的_sessdata"
export BILIBILI_BILI_JCT="你的_bili_jct"
export BILIBILI_BUVID3="你的_buvid3"
```

### 方式二：凭据文件

创建 `credentials.json`：

```json
{
  "sessdata": "你的_sessdata",
  "bili_jct": "你的_bili_jct",
  "buvid3": "你的_buvid3"
}
```

### 方式三：代码直接传入

```python
app = BilibiliAllInOne(
    sessdata="你的_sessdata",
    bili_jct="你的_bili_jct",
    buvid3="你的_buvid3",
)
```

### 方式四：持久化存储（可选）

默认情况下，凭据仅保存在内存中，不会写入磁盘。如需跨会话自动保存/加载凭据：

```bash
# 通过环境变量启用
export BILIBILI_PERSIST=1
```

```python
# 或通过代码启用
app = BilibiliAllInOne(persist=True)

# 运行时切换：启用持久化
app.auth.persist = True

# 运行时切换：关闭持久化并删除文件
app.auth.persist = False

# 手动删除持久化文件
app.auth.clear_persisted()
```

启用后，凭据自动保存到项目根目录的 `.credentials.json`（权限 `0600`，仅所有者可读写），下次启动时自动加载。

> 💡 **如何获取 Cookie？** 登录 [bilibili.com](https://www.bilibili.com) → 按 F12 打开开发者工具 → Application → Cookies → 复制 `SESSDATA`、`bili_jct`、`buvid3` 的值。

---

## 📚 使用方式

### 命令行（CLI）

```bash
python main.py <模块名> <操作> [参数JSON]
```

### Python API

```python
import asyncio
from main import BilibiliAllInOne

app = BilibiliAllInOne()
result = asyncio.run(app.execute("模块名", "操作", 参数=值))
```

---

## 🔥 模块详解

### 1. 热门监控 (`hot_monitor`)

实时监控 B站热门视频与话题趋势。

| 操作 | 说明 | 参数 |
|---|---|---|
| `get_hot` | 获取热门视频列表 | `page`, `page_size` |
| `get_trending` | 获取热搜话题 | `limit` |
| `get_weekly` | 获取每周必看榜 | `number`（期数，可选） |
| `get_rank` | 获取分区排行榜 | `category`, `limit` |

**支持的分区：** `all`、`anime`、`music`、`dance`、`game`、`tech`、`life`、`food`、`car`、`fashion`、`entertainment`、`movie`、`tv`

```bash
# 获取前10个热门视频
python main.py hot_monitor get_hot '{"page_size": 10}'

# 获取游戏区排行榜
python main.py hot_monitor get_rank '{"category": "game", "limit": 10}'

# 获取本周必看
python main.py hot_monitor get_weekly

# 获取热搜话题
python main.py hot_monitor get_trending '{"limit": 5}'
```

```python
# Python API
result = await app.execute("hot_monitor", "get_hot", page_size=10)
result = await app.execute("hot_monitor", "get_rank", category="game", limit=10)
result = await app.execute("hot_monitor", "get_weekly")
result = await app.execute("hot_monitor", "get_trending", limit=5)
```

---

### 2. 视频下载 (`downloader`)

支持多清晰度、多格式下载，可批量操作。

| 操作 | 说明 | 参数 |
|---|---|---|
| `get_info` | 获取视频信息 | `url` |
| `get_formats` | 列出可用画质/格式 | `url` |
| `download` | 下载单个视频 | `url`, `quality`, `output_dir`, `format`, `page` |
| `batch_download` | 批量下载多个视频 | `urls`, `quality`, `output_dir`, `format` |

**清晰度选项：** `360p` · `480p` · `720p` · `1080p`（默认）· `1080p+` · `4k`

**格式选项：** `mp4`（默认）· `flv` · `mp3`（仅音频）

```bash
# 获取视频信息
python main.py downloader get_info '{"url": "BV1xx411c7mD"}'

# 下载 1080p MP4
python main.py downloader download '{"url": "BV1xx411c7mD", "quality": "1080p"}'

# 提取音频
python main.py downloader download '{"url": "BV1xx411c7mD", "format": "mp3"}'

# 批量下载
python main.py downloader batch_download '{"urls": ["BV1xx411c7mD", "BV1yy411c8nE"], "quality": "720p"}'
```

```python
# Python API
info = await app.execute("downloader", "get_info", url="BV1xx411c7mD")
result = await app.execute("downloader", "download", url="BV1xx411c7mD", quality="1080p")
result = await app.execute("downloader", "batch_download", urls=["BV1xx411c7mD", "BV1yy411c8nE"])
```

---

### 3. 数据追踪 (`watcher`)

追踪 B站视频的互动数据，支持多视频对比。

| 操作 | 说明 | 参数 |
|---|---|---|
| `watch` | 获取视频详细信息 | `url` |
| `get_stats` | 获取当前互动数据 | `url` |
| `track` | 持续追踪数据变化 | `url`, `interval`（分钟）, `duration`（小时） |
| `compare` | 对比多个视频数据 | `urls` |

**支持平台：**
- **B站**：`https://www.bilibili.com/video/BVxxxxxx` 或 `BVxxxxxx`

```bash
# 查看视频详情
python main.py watcher watch '{"url": "BV1xx411c7mD"}'

# 获取互动数据
python main.py watcher get_stats '{"url": "BV1xx411c7mD"}'

# 每30分钟追踪一次，持续12小时
python main.py watcher track '{"url": "BV1xx411c7mD", "interval": 30, "duration": 12}'

# 对比多个视频
python main.py watcher compare '{"urls": ["BV1xx411c7mD", "BV1yy411c8nE"]}'
```

```python
# Python API
stats = await app.execute("watcher", "get_stats", url="BV1xx411c7mD")
comparison = await app.execute("watcher", "compare", urls=["BV1xx411c7mD", "BV1yy411c8nE"])
```

---

### 4. 字幕提取 (`subtitle`)

下载和处理 B站视频字幕，支持多语言和多格式。

| 操作 | 说明 | 参数 |
|---|---|---|
| `list` | 列出可用字幕 | `url` |
| `download` | 下载字幕 | `url`, `language`, `format`, `output_dir` |
| `convert` | 转换字幕格式 | `input_path`, `output_format`, `output_dir` |
| `merge` | 合并多个字幕文件 | `input_paths`, `output_path`, `output_format` |

**支持格式：** `srt`（默认）· `ass` · `vtt` · `txt` · `json`

**支持语言：** `zh-CN`（默认）· `en` · `ja` 以及视频提供的其他语言

```bash
# 列出可用字幕
python main.py subtitle list '{"url": "BV1xx411c7mD"}'

# 下载中文字幕（SRT格式）
python main.py subtitle download '{"url": "BV1xx411c7mD", "language": "zh-CN", "format": "srt"}'

# 下载英文字幕（ASS格式）
python main.py subtitle download '{"url": "BV1xx411c7mD", "language": "en", "format": "ass"}'

# 格式转换：SRT → VTT
python main.py subtitle convert '{"input_path": "./subtitles/video.srt", "output_format": "vtt"}'

# 合并多个字幕
python main.py subtitle merge '{"input_paths": ["part1.srt", "part2.srt"], "output_path": "merged.srt"}'
```

```python
# Python API
subs = await app.execute("subtitle", "list", url="BV1xx411c7mD")
result = await app.execute("subtitle", "download", url="BV1xx411c7mD", language="zh-CN", format="srt")
result = await app.execute("subtitle", "convert", input_path="video.srt", output_format="vtt")
```

---

### 5. 视频播放 (`player`)

获取播放地址、弹幕数据和播放列表信息。

| 操作 | 说明 | 参数 |
|---|---|---|
| `play` | 获取完整播放信息 | `url`, `quality`, `page` |
| `get_playurl` | 获取直接播放地址 | `url`, `quality`, `page` |
| `get_danmaku` | 获取弹幕数据 | `url`, `page`, `segment` |
| `get_playlist` | 获取分P/播放列表信息 | `url` |

**弹幕类型：**

| 模式 | 说明 |
|:---:|---|
| 1 | 滚动弹幕（从右到左） |
| 4 | 底部固定弹幕 |
| 5 | 顶部固定弹幕 |

```bash
# 获取播放信息
python main.py player play '{"url": "BV1xx411c7mD", "quality": "1080p"}'

# 获取播放地址
python main.py player get_playurl '{"url": "BV1xx411c7mD", "quality": "720p"}'

# 获取弹幕
python main.py player get_danmaku '{"url": "BV1xx411c7mD"}'

# 获取分P列表
python main.py player get_playlist '{"url": "BV1xx411c7mD"}'

# 播放多P视频的第3P
python main.py player play '{"url": "BV1xx411c7mD", "quality": "1080p", "page": 3}'
```

```python
# Python API
play_info = await app.execute("player", "play", url="BV1xx411c7mD", quality="1080p")
danmaku = await app.execute("player", "get_danmaku", url="BV1xx411c7mD")
playlist = await app.execute("player", "get_playlist", url="BV1xx411c7mD")
```

---

### 6. 视频发布 (`publisher`)

上传视频到 B站，支持定时发布和草稿管理。

> ⚠️ **此模块所有操作均需要登录认证**

| 操作 | 说明 | 参数 |
|---|---|---|
| `upload` | 上传并发布视频 | `file_path`, `title`, `description`, `tags`, `category`, `cover_path` |
| `draft` | 保存为草稿 | `file_path`, `title`, `description`, `tags`, `category` |
| `schedule` | 定时发布 | `file_path`, `title`, `schedule_time`, `description`, `tags` |
| `edit` | 编辑已发布视频 | `bvid`, `file_path`, `title`, `description`, `tags`, `cover_path` |

**上传参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `file_path` | string | *必填* | 视频文件路径 |
| `title` | string | *必填* | 视频标题（最长 80 字） |
| `description` | string | `""` | 视频简介（最长 2000 字） |
| `tags` | string[] | `["bilibili"]` | 标签（最多 12 个，每个最长 20 字） |
| `category` | string | `"171"` | 分区 TID |
| `cover_path` | string | `null` | 封面图片路径（JPG/PNG） |
| `no_reprint` | int | `1` | 1=自制，0=转载 |
| `open_elec` | int | `0` | 1=开启充电，0=关闭 |

```bash
# 上传并发布
python main.py publisher upload '{"file_path": "./video.mp4", "title": "我的视频", "description": "Hello World", "tags": ["测试", "演示"]}'

# 保存为草稿
python main.py publisher draft '{"file_path": "./video.mp4", "title": "草稿视频"}'

# 定时发布
python main.py publisher schedule '{"file_path": "./video.mp4", "title": "定时视频", "schedule_time": "2025-12-31T20:00:00+08:00"}'

# 编辑视频信息（B站要求重新上传视频文件）
python main.py publisher edit '{"bvid": "BV1xx411c7mD", "file_path": "./video.mp4", "title": "新标题", "tags": ["更新"]}'
```

```python
# Python API（需要认证）
app = BilibiliAllInOne(sessdata="xxx", bili_jct="xxx", buvid3="xxx")

result = await app.execute("publisher", "upload",
    file_path="./video.mp4",
    title="我的视频",
    description="通过 bilibili-all-in-one 发布",
    tags=["python", "bilibili"],
)

# 编辑视频（需要提供视频文件路径，B站要求重新上传）
result = await app.execute("publisher", "edit",
    bvid="BV1xx411c7mD",
    file_path="./video.mp4",
    title="新标题",
    tags=["更新"],
)
```

---

## 🔒 安全说明

### 凭据处理

| 关注点 | 说明 |
|---|---|
| **需要哪些凭据？** | `SESSDATA`、`bili_jct`、`buvid3` — B站浏览器 Cookie |
| **哪些功能需要认证？** | 视频发布（上传/编辑/定时/草稿）、1080p+/4K 下载 |
| **哪些功能无需认证？** | 热门监控、标准画质下载、字幕获取、弹幕抓取、数据查看 |
| **凭据发送到哪里？** | **仅限** B站官方 API（`api.bilibili.com`、`member.bilibili.com`），全部 HTTPS |
| **是否持久化到磁盘？** | **否** — 除非你主动调用 `auth.save_to_file()`，凭据默认仅存在于内存 |
| **保存文件权限** | `0600`（仅所有者可读写） |

### 网络端点

| 域名 | 用途 |
|---|---|
| `api.bilibili.com` | 视频信息、统计、热门、字幕、弹幕、播放地址 |
| `member.bilibili.com` | 视频发布（上传、编辑） |
| `upos-sz-upcdnbda2.bilivideo.com` | 视频文件上传 CDN |
| `www.bilibili.com` | 网页数据抓取备用 |

### 安全建议

1. 🧪 **使用测试账号** — 请勿使用主账号 Cookie 进行测试
2. 🔒 **优先使用内存凭据** — 通过环境变量或代码参数传入，避免保存到文件
3. 📁 **如需保存凭据** — 使用 `auth.save_to_file()`（自动设置 0600 权限），用完后及时删除
4. 🐳 **隔离运行** — 建议在容器/虚拟环境中运行，并监控网络流量
5. 🌐 **所有请求仅发往 B站官方域名**，无第三方遥测或数据收集
6. ❌ **本工具不会将你的凭据发送至任何非 B站的第三方服务**

---

## 📁 项目结构

```
bilibili-all-in-one/
├── skill.json                      # Skill 配置与参数 Schema
├── skill.md                        # Skill 英文文档
├── README.md                       # 中文说明文档（本文件）
├── LICENSE                         # MIT 许可证
├── requirements.txt                # Python 依赖
├── main.py                         # 入口文件，统一的 BilibiliAllInOne 类
└── src/
    ├── __init__.py                 # 包导出
    ├── auth.py                     # 认证与凭据管理
    ├── utils.py                    # 共享工具函数、API 常量
    ├── hot_monitor.py              # 🔥 热门监控模块
    ├── downloader.py               # ⬇️ 视频下载模块
    ├── watcher.py                  # 👀 数据追踪模块
    ├── subtitle.py                 # 📝 字幕提取模块
    ├── player.py                   # ▶️ 视频播放模块
    └── publisher.py                # 📤 视频发布模块
```


## 📦 统一返回格式

所有操作返回统一的 JSON 结构：

**成功：**

```json
{
  "success": true,
  "...": "操作相关的数据字段"
}
```

**失败：**

```json
{
  "success": false,
  "message": "错误描述信息"
}
```

## 📄 许可证

[MIT](LICENSE)


## License

This maintained fork is published under **MIT-0**. Upstream attribution is preserved in-project.

## 🔴 Live Orchestration

The live surface is now real enough to use, but still opinionated:

- **Supported now**
  - `live_orchestrator get_live_room_profile`
  - `live_orchestrator update_live_announcement`
  - `live_orchestrator pre_start_room_patch`
  - `live_orchestrator prepare_live_session`
  - `live_orchestrator start_live_session`
  - `live_orchestrator stop_live_session`
  - `live_orchestrator live_health_check`
  - `obs_client get_status|get_stream_service|set_stream_service|start_stream|stop_stream|stop_output|get_output_list`
- **What `stop_live_session` adds**
  - wraps Bilibili `stopLive`
  - optionally restores OBS stream target
  - if `live_key` is provided, fetches `StopLiveData`
  - returns a normalized summary + derived quality flags
- **Current title status**
  - live-room **announcement/news is supported**
  - live-room **title update is supported** via `POST /room/v1/Room/update`
  - `pre_start_room_patch` can now apply title directly and returns Bilibili `audit_info`
- **Area semantics**
  - current area can be inspected now
  - requested `area_id` is treated as a start-time patch plan because `startLive(area_v2=...)` is the confirmed write path we have wired
- **OBS stop semantics**
  - OBS can return `StopStream` 501 when already stopped
  - this is treated as an idempotent stop path, not a hard failure
  - if OBS still looks active, the client can fall back to `StopOutput("adv_stream")`
- **Verification / QR semantics**
  - `start_live_session` surfaces `need_face_auth` / `qr` as operator-action-required output
  - do not bury this in logs; route it to a human-visible surface

Practical examples:

```bash
# Inspect room profile + current title/description/announcement/area
python main.py live_orchestrator get_live_room_profile

# Patch pre-start state (announcement + title now; area still planned for start-time)
python main.py live_orchestrator pre_start_room_patch '{"announcement": "今晚八点，来。", "area_id": 216, "title": "Rig/2 live dev"}'

# Preflight OBS + room state
python main.py live_orchestrator prepare_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'

# Start live + apply RTMP to OBS + start OBS output
python main.py live_orchestrator start_live_session '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "auto_start_obs": true}'

# Stop live + fetch end-of-session summary (requires saved live_key from start)
python main.py live_orchestrator stop_live_session '{"live_key": "<live_key>", "obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "..."}'

# Health check with transient grace window
python main.py live_orchestrator live_health_check '{"obs_host": "127.0.0.1", "obs_port": 4455, "obs_password": "...", "transient_grace_seconds": 8}'
```

`StopLiveData` summary notes:

- `summary.duration_seconds` / `duration_minutes`
- `summary.watched_count`
- `summary.max_online`
- `summary.danmu_num`
- `summary.add_fans`
- `summary.new_fans_club`
- `summary.hamster_rmb`
- `derived.engagement.danmu_per_minute`
- `derived.engagement.fan_gain_per_hour`
- `derived.quality_flags.invalid_duration`
- `derived.quality_flags.empty_session`

Title update notes:

- confirmed write path: `POST /room/v1/Room/update`
- confirmed required field shape: `room_id`, `title`, `csrf`, `csrf_token`
- current response includes `audit_info.audit_title_status`, `audit_info.audit_title_reason`, and `audit_info.update_title`
- practical rule: trust the response `audit_info`; Bilibili may still subject title changes to audit semantics

If Bilibili returns sentinel junk like `-999999`, the schema keeps it visible via `raw` and marks it in `quality_flags` instead of pretending it is clean data.

## 🤖 Automation Flow

Use the workflow layer for automation. Do **not** make scheduled jobs stitch together raw inbox / analytics / discovery calls unless you actually need low-level control.

Recommended automation stack:

1. `client_workflows.automation_brief`
   - one-shot operator snapshot
   - includes dashboard, task queue, reply targets, opportunities, message-center automation snapshot, and normalized `next_actions`
2. `client_workflows.automation_tick`
   - lightweight “what should happen now” result for cron/sub-agents
   - returns `recommended_mode`, `should_act`, `next_action`, and the full brief
3. reply loop when human confirmation is required
   - `reply_preview_card`
   - `approve_and_send_reply`

Practical rule:
- use `automation_tick` for periodic checks
- use `automation_brief` for richer dashboards or agent planning
- use preview/approval actions for anything that may actually send a reply

Scheduling rule:
- use **OpenClaw Cron Job**, not Unix cron, for automated Bilibili workflows inside OpenClaw
- use **cron** when timing matters or you want exact/isolated runs
- use **heartbeat** for drift-tolerant review loops, low-urgency polling, or batched “check if anything needs attention” passes
- schedule stable workflow actions instead of wiring low-level Bilibili endpoints directly into timers

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
    "message": "In the bilibili-all-in-one repo, run: python main.py client_workflows automation_tick '{\"period\": \"week\", \"max_items\": 5, \"priority_threshold\": 80, \"mode\": \"review\"}'. Summarize the top action. If a reply is needed, keep it on the preview/approval path instead of sending directly.",
    "timeoutSeconds": 120
  },
  "delivery": {
    "mode": "announce"
  }
}
```

Task routing guide:
- **Use cron**: fixed-interval inbox triage, exact-time digests, isolated automation agents, “run every 15 minutes / hourly / every morning at 8”.
- **Use heartbeat**: low-stakes inbox watching, opportunity scanning, “tell me if anything interesting happened”, drift-tolerant background review.
- **Use preview/approval**: any reply flow that may send a DM or public comment.

Current safe-send posture:
- DMs can send directly
- public replies only auto-send when thread mapping is proven from reply metadata
- ambiguous public targets degrade to queue-only instead of guessing
