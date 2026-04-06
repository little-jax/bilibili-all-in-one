"""Unified feed / discovery client for homepage, hot, rank, and topic surfaces."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .auth import BilibiliAuth
from .client_base import BilibiliClientBase

try:
    from bilibili_api import homepage as bili_homepage
    from bilibili_api import hot as bili_hot
    from bilibili_api import rank as bili_rank
    from bilibili_api import topic as bili_topic
    BILI_DISCOVERY_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    bili_homepage = None
    bili_hot = None
    bili_rank = None
    bili_topic = None
    BILI_DISCOVERY_IMPORT_ERROR = str(exc)


class BilibiliDiscoveryClient(BilibiliClientBase):
    """Operator-facing unified discovery surface."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        super().__init__(auth=auth)

    def _require_discovery_library(self) -> Optional[Dict[str, Any]]:
        base_error = self._require_library()
        if base_error:
            return base_error
        if BILI_DISCOVERY_IMPORT_ERROR:
            return self._failure("bilibili_api discovery modules are unavailable.", detail=BILI_DISCOVERY_IMPORT_ERROR)
        return None

    @staticmethod
    def _pick_items(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if not isinstance(data, dict):
            return []
        for key in ("item", "items", "list", "cards"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        return []

    @staticmethod
    def _find_first(data: Any, keys: tuple[str, ...]) -> Any:
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key] not in (None, "", [], {}):
                    return data[key]
            for value in data.values():
                found = BilibiliDiscoveryClient._find_first(value, keys)
                if found not in (None, "", [], {}):
                    return found
        elif isinstance(data, list):
            for item in data:
                found = BilibiliDiscoveryClient._find_first(item, keys)
                if found not in (None, "", [], {}):
                    return found
        return None

    @staticmethod
    def _snip(value: Any, limit: int = 220) -> str:
        text = "" if value is None else str(value)
        text = " ".join(text.split())
        return text[: limit - 1] + "…" if len(text) > limit else text

    def _normalize_video_card(self, item: Dict[str, Any]) -> Dict[str, Any]:
        owner = item.get("owner") or item.get("upper") or {}
        stat = item.get("stat") or {}
        return {
            "aid": item.get("aid") or item.get("id"),
            "bvid": item.get("bvid"),
            "title": item.get("title") or item.get("name"),
            "cover": item.get("pic") or item.get("cover"),
            "uri": item.get("uri") or (f"https://www.bilibili.com/video/{item.get('bvid')}" if item.get("bvid") else None),
            "duration": item.get("duration"),
            "author": {
                "mid": owner.get("mid"),
                "name": owner.get("name") or owner.get("uname"),
            },
            "stats": {
                "views": stat.get("view") or item.get("play") or item.get("view"),
                "likes": stat.get("like") or item.get("like"),
                "comments": stat.get("reply") or item.get("reply"),
                "favorites": stat.get("favorite") or item.get("favorites"),
            },
            "raw": item,
        }

    def _normalize_topic_card(self, item: Dict[str, Any]) -> Dict[str, Any]:
        topic_id = self._find_first(item, ("topic_id", "id"))
        name = self._find_first(item, ("name", "title", "topic_name"))
        return {
            "topic_id": topic_id,
            "id": topic_id,
            "name": name,
            "description": self._snip(self._find_first(item, ("desc", "description", "summary")), 300),
            "uri": self._find_first(item, ("uri", "url", "jump_url")) or (f"https://www.bilibili.com/v/topic/detail?topic_id={topic_id}" if topic_id else None),
            "cover": self._find_first(item, ("icon", "cover", "image", "url")),
            "raw": item,
        }

    async def get_home_feed(self) -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            data = await bili_homepage.get_videos(credential=self._credential())
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.discovery_client.get_home_feed.v1",
                count=len(items),
                items=[self._normalize_video_card(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get home feed: {exc}")

    async def get_hot(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            data = await bili_hot.get_hot_videos(pn=int(page), ps=int(page_size))
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.discovery_client.get_hot.v1",
                page=int(page),
                page_size=int(page_size),
                count=len(items),
                items=[self._normalize_video_card(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get hot videos: {exc}")

    async def get_history_popular(self) -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            data = await bili_hot.get_history_popular_videos()
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.discovery_client.get_history_popular.v1",
                count=len(items),
                items=[self._normalize_video_card(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get history popular videos: {exc}")

    async def get_rank(self, rank_type: str = "All") -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            rank_enum = getattr(bili_rank.RankType, rank_type, bili_rank.RankType.All)
            data = await bili_rank.get_rank(type_=rank_enum)
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.discovery_client.get_rank.v1",
                rank_type=rank_enum.name,
                count=len(items),
                items=[self._normalize_video_card(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get rank: {exc}")

    async def get_hot_topics(self, limit: int = 10) -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            data = await bili_topic.get_hot_topics(numbers=int(limit))
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.discovery_client.get_hot_topics.v1",
                count=len(items),
                items=[self._normalize_topic_card(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get hot topics: {exc}")

    async def get_topic_detail(self, topic_id: int) -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            obj = bili_topic.Topic(topic_id=int(topic_id), credential=self._credential())
            data = await obj.get_info()
            return self._success(
                schema="bilibili.discovery_client.get_topic_detail.v1",
                item=self._normalize_topic_card(data),
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get topic detail: {exc}")

    async def get_topic_cards(self, topic_id: int, page_size: int = 20, offset: Optional[str] = None, sort_by: str = "HOT") -> Dict[str, Any]:
        error = self._require_discovery_library()
        if error:
            return error
        try:
            obj = bili_topic.Topic(topic_id=int(topic_id), credential=self._credential())
            sort_enum = getattr(bili_topic.TopicCardsSortBy, sort_by.upper(), bili_topic.TopicCardsSortBy.HOT)
            data = await obj.get_cards(ps=int(page_size), offset=offset, sort_by=sort_enum)
            items = self._pick_items(data)
            normalized = []
            for x in items:
                if x.get("topic_type") or self._find_first(x, ("topic_id",)):
                    normalized.append(self._normalize_topic_card(x))
                else:
                    normalized.append(self._normalize_video_card(x))
            return self._success(
                schema="bilibili.discovery_client.get_topic_cards.v1",
                topic_id=int(topic_id),
                count=len(normalized),
                items=normalized,
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get topic cards: {exc}")

    async def discovery_snapshot(self, home_limit: int = 6, hot_limit: int = 6, rank_limit: int = 6, topic_limit: int = 6) -> Dict[str, Any]:
        home = await self.get_home_feed()
        hot = await self.get_hot(page_size=max(int(hot_limit), 1))
        rank = await self.get_rank()
        topics = await self.get_hot_topics(limit=max(int(topic_limit), 1))

        home_items = (home.get("items") or [])[: max(int(home_limit), 0)] if home.get("success") else []
        hot_items = (hot.get("items") or [])[: max(int(hot_limit), 0)] if hot.get("success") else []
        rank_items = (rank.get("items") or [])[: max(int(rank_limit), 0)] if rank.get("success") else []
        topic_items = (topics.get("items") or [])[: max(int(topic_limit), 0)] if topics.get("success") else []

        lines = []
        if home_items:
            lines.append("首页推荐：")
            lines.extend([f"- {x.get('title')}" for x in home_items[:3]])
        if hot_items:
            lines.append("热门视频：")
            lines.extend([f"- {x.get('title')}" for x in hot_items[:3]])
        if rank_items:
            lines.append("排行榜：")
            lines.extend([f"- {x.get('title')}" for x in rank_items[:3]])
        if topic_items:
            lines.append("热门话题：")
            lines.extend([f"- {x.get('name') or x.get('title')}" for x in topic_items[:3]])
        if topics.get("success") is False:
            lines.append(f"热门话题获取失败：{topics.get('message')}")

        return self._success(
            schema="bilibili.discovery_client.discovery_snapshot.v1",
            home_feed=home_items,
            hot=hot_items,
            rank=rank_items,
            topics=topic_items,
            topic_status={"success": topics.get("success", False), "message": topics.get("message")},
            text="\n".join(lines),
        )

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "get_home_feed": self.get_home_feed,
            "get_hot": self.get_hot,
            "get_history_popular": self.get_history_popular,
            "get_rank": self.get_rank,
            "get_hot_topics": self.get_hot_topics,
            "get_topic_detail": self.get_topic_detail,
            "get_topic_cards": self.get_topic_cards,
            "discovery_snapshot": self.discovery_snapshot,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown discovery_client action: {action}")
        return await handler(**kwargs)
