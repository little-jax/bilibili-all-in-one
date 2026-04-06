"""Bilibili All-in-One Skill - Main Entry Point.

A comprehensive Bilibili toolkit that integrates:
- Hot/trending video monitoring
- Video downloading
- Video watching & stats tracking
- Subtitle downloading & processing
- Video playback & danmaku
- Video uploading & publishing
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional

from src.auth import BilibiliAuth
from src.hot_monitor import HotMonitor
from src.downloader import BilibiliDownloader
from src.watcher import BilibiliWatcher
from src.subtitle import SubtitleDownloader
from src.player import BilibiliPlayer
from src.publisher import BilibiliPublisher
from src.operations import BilibiliOperations
from src.message_center import BilibiliMessageCenter
from src.search_client import BilibiliSearchClient
from src.user_intel import BilibiliUserIntel
from src.entity_resolver import BilibiliEntityResolver
from src.client_workflows import BilibiliClientWorkflows
from src.creative_center_client import BilibiliCreativeCenterClient
from src.auth_client import BilibiliAuthClient


class BilibiliAllInOne:
    """Unified interface for all Bilibili skill capabilities."""

    def __init__(
        self,
        sessdata: Optional[str] = None,
        bili_jct: Optional[str] = None,
        buvid3: Optional[str] = None,
        credential_file: Optional[str] = None,
        persist: Optional[bool] = None,
    ):
        """Initialize BilibiliAllInOne.

        Args:
            sessdata: Bilibili SESSDATA cookie.
            bili_jct: Bilibili bili_jct (CSRF) cookie.
            buvid3: Bilibili buvid3 cookie.
            credential_file: Path to JSON credential file.
            persist: Whether to persist credentials to disk (default: False).
                Set to True or env BILIBILI_PERSIST=1 to auto-save/load
                credentials from .credentials.json.
        """
        self.auth = BilibiliAuth(
            sessdata=sessdata,
            bili_jct=bili_jct,
            buvid3=buvid3,
            credential_file=credential_file,
            persist=persist,
        )

        # Initialize all modules
        self.hot_monitor = HotMonitor(auth=self.auth)
        self.downloader = BilibiliDownloader(auth=self.auth)
        self.watcher = BilibiliWatcher(auth=self.auth)
        self.player = BilibiliPlayer(auth=self.auth)
        self.subtitle = SubtitleDownloader(
            auth=self.auth,
            downloader=self.downloader,
            player=self.player,
        )
        self.operations = BilibiliOperations(auth=self.auth)
        self.message_center = BilibiliMessageCenter(auth=self.auth)
        self.search_client = BilibiliSearchClient(auth=self.auth)
        self.user_intel = BilibiliUserIntel(auth=self.auth)
        self.entity_resolver = BilibiliEntityResolver(auth=self.auth)
        self.client_workflows = BilibiliClientWorkflows(auth=self.auth)
        self.creative_center = BilibiliCreativeCenterClient(auth=self.auth)
        self.auth_client = BilibiliAuthClient(auth=self.auth)
        self._publisher = None  # Lazy init (requires auth)

    @property
    def publisher(self) -> BilibiliPublisher:
        """Get the publisher module (requires authentication).

        Returns:
            BilibiliPublisher instance.

        Raises:
            ValueError: If not authenticated.
        """
        if self._publisher is None:
            self._publisher = BilibiliPublisher(auth=self.auth)
        return self._publisher

    async def execute(self, skill_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Execute any skill action through a unified interface.

        Args:
            skill_name: Name of the skill module.
            action: Action to perform.
            **kwargs: Additional parameters.

        Returns:
            Action result dict.
        """
        skill_map = {
            "bilibili_hot_monitor": lambda: self.hot_monitor,
            "hot_monitor": lambda: self.hot_monitor,
            "hot": lambda: self.hot_monitor,

            "bilibili_downloader": lambda: self.downloader,
            "downloader": lambda: self.downloader,
            "download": lambda: self.downloader,

            "bilibili_watcher": lambda: self.watcher,
            "watcher": lambda: self.watcher,
            "watch": lambda: self.watcher,

            "bilibili_subtitle": lambda: self.subtitle,
            "subtitle": lambda: self.subtitle,

            "bilibili_player": lambda: self.player,
            "player": lambda: self.player,
            "play": lambda: self.player,

            "bilibili_publisher": lambda: self.publisher,
            "publisher": lambda: self.publisher,
            "publish": lambda: self.publisher,

            "bilibili_operations": lambda: self.operations,
            "operations": lambda: self.operations,
            "ops": lambda: self.operations,

            "bilibili_message_center": lambda: self.message_center,
            "message_center": lambda: self.message_center,
            "inbox": lambda: self.message_center,

            "bilibili_search_client": lambda: self.search_client,
            "search_client": lambda: self.search_client,
            "search": lambda: self.search_client,

            "bilibili_user_intel": lambda: self.user_intel,
            "user_intel": lambda: self.user_intel,
            "intel": lambda: self.user_intel,

            "bilibili_entity_resolver": lambda: self.entity_resolver,
            "entity_resolver": lambda: self.entity_resolver,
            "resolver": lambda: self.entity_resolver,
            "resolve": lambda: self.entity_resolver,

            "bilibili_client_workflows": lambda: self.client_workflows,
            "client_workflows": lambda: self.client_workflows,
            "workflows": lambda: self.client_workflows,

            "bilibili_creative_center": lambda: self.creative_center,
            "creative_center": lambda: self.creative_center,
            "creative_center_client": lambda: self.creative_center,
            "creator_analytics": lambda: self.creative_center,

            "bilibili_auth_client": lambda: self.auth_client,
            "auth_client": lambda: self.auth_client,
            "auth": lambda: self.auth_client,
        }

        skill_factory = skill_map.get(skill_name)
        if not skill_factory:
            return {
                "success": False,
                "message": f"Unknown skill: {skill_name}. Available: {list(skill_map.keys())}",
            }

        skill = skill_factory()

        return await skill.execute(action=action, **kwargs)


async def main():
    """CLI entry point for testing."""
    if len(sys.argv) < 3:
        print("Usage: python main.py <skill_name> <action> [params_json]")
        print()
        print("Skills:")
        print("  hot_monitor      - Monitor hot/trending videos")
        print("  downloader       - Download videos")
        print("  watcher          - Watch and track video stats")
        print("  subtitle         - Download subtitles")
        print("  player           - Play videos and get danmaku")
        print("  publisher        - Upload, preview, inspect, draft, schedule, and edit videos")
        print("  operations       - Community/account operations")
        print("  message_center   - Inbox, DMs, mentions, replies, likes, notifications")
        print("  search_client    - Search videos/users/topics/articles/live/manga")
        print("  user_intel       - Profile lookup, recent content, audience investigation")
        print("  entity_resolver  - Resolve URLs / BV / UID / dynamic / opus / note entities")
        print("  client_workflows - High-level lookup / investigate / reply-prep / operator workflows")
        print("  creative_center  - Creator analytics / KPI / dashboard snapshots")
        print("  auth_client      - QR-first login, session inspection, and auth cleanup")
        print()
        print("Examples:")
        print("  python main.py hot_monitor get_hot '{\"limit\": 5}'")
        print("  python main.py downloader get_info '{\"url\": \"BV1xx411c7mD\"}'")
        print("  python main.py subtitle list '{\"url\": \"BV1xx411c7mD\"}'")
        print("  python main.py player get_danmaku '{\"url\": \"BV1xx411c7mD\"}'")
        print("  python main.py operations verify_auth")
        print("  python main.py operations post_dynamic '{\"text\": \"今晚八点直播，来。\"}'")
        print("  python main.py message_center inbox_summary")
        print("  python main.py message_center priority_digest")
        print("  python main.py search_client search_videos '{\"keyword\": \"Rig2\", \"page_size\": 5}'")
        print("  python main.py user_intel inspect_user '{\"uid\": 434156493}'")
        print("  python main.py entity_resolver resolve '{\"target\": \"https://www.bilibili.com/video/BV1KQPyzcEhH\"}'")
        print("  python main.py publisher preview_upload '{\"file_path\": \"./video.mp4\", \"title\": \"My Video\"}'")
        print("  python main.py publisher inspect_video '{\"bvid\": \"BV1KQPyzcEhH\"}'")
        print("  python main.py client_workflows investigate_user '{\"uid\": 434156493, \"include_creator_metrics\": true, \"period\": \"week\"}'")
        print("  python main.py client_workflows classify_inbound_intent '{\"text\": \"想合作推广一下这个项目\", \"target\": \"https://www.bilibili.com/video/BV1KQPyzcEhH\"}'")
        print("  python main.py client_workflows operator_triage '{\"source\": \"reply\", \"limit\": 5}'")
        print("  python main.py client_workflows creator_dashboard_snapshot '{\"period\": \"week\", \"max_items\": 5}'")
        print("  python main.py client_workflows creator_task_queue '{\"period\": \"week\", \"max_items\": 5}'")
        print("  python main.py client_workflows recommend_reply_targets '{\"max_items\": 5}'")
        print("  python main.py client_workflows content_opportunity_brief '{\"period\": \"week\", \"max_items\": 5}'")
        print("  python main.py creative_center dashboard_snapshot '{\"period\": \"week\"}'")
        print("  python main.py auth_client start_qr_login")
        print("  python main.py auth_client poll_qr_login '{\"persist\": true}'")
        print("  python main.py auth_client verify_auth")
    skill_name = sys.argv[1]
    action = sys.argv[2]
    params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

    app = BilibiliAllInOne()
    result = await app.execute(skill_name=skill_name, action=action, **params)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
