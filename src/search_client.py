"""Search client for Bilibili discovery and lookup workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client_base import BilibiliClientBase, bili_search


class BilibiliSearchClient(BilibiliClientBase):
    """Structured search surface over bilibili_api.search."""

    @staticmethod
    def _normalize_search_type(search_type: str):
        normalized = (search_type or "video").strip().lower()
        mapping = {
            "video": bili_search.SearchObjectType.VIDEO,
            "videos": bili_search.SearchObjectType.VIDEO,
            "user": bili_search.SearchObjectType.USER,
            "users": bili_search.SearchObjectType.USER,
            "live": bili_search.SearchObjectType.LIVE,
            "article": bili_search.SearchObjectType.ARTICLE,
            "articles": bili_search.SearchObjectType.ARTICLE,
            "topic": bili_search.SearchObjectType.TOPIC,
            "topics": bili_search.SearchObjectType.TOPIC,
            "photo": bili_search.SearchObjectType.PHOTO,
            "photos": bili_search.SearchObjectType.PHOTO,
            "bangumi": bili_search.SearchObjectType.BANGUMI,
            "ft": bili_search.SearchObjectType.FT,
            "live_user": bili_search.SearchObjectType.LIVEUSER,
            "liveuser": bili_search.SearchObjectType.LIVEUSER,
        }
        if normalized not in mapping:
            raise ValueError(f"Unsupported search type: {search_type}")
        return mapping[normalized]

    @staticmethod
    def _normalize_order(search_type: str, order: Optional[str]):
        if not order:
            return None
        normalized_type = (search_type or "video").strip().lower()
        normalized_order = order.strip().lower()

        if normalized_type in {"video", "videos"}:
            mapping = {
                "totalrank": bili_search.OrderVideo.TOTALRANK,
                "rank": bili_search.OrderVideo.TOTALRANK,
                "click": bili_search.OrderVideo.CLICK,
                "view": bili_search.OrderVideo.CLICK,
                "pubdate": bili_search.OrderVideo.PUBDATE,
                "date": bili_search.OrderVideo.PUBDATE,
                "dm": bili_search.OrderVideo.DM,
                "danmaku": bili_search.OrderVideo.DM,
                "stow": bili_search.OrderVideo.STOW,
                "favorite": bili_search.OrderVideo.STOW,
                "scores": bili_search.OrderVideo.SCORES,
            }
            return mapping.get(normalized_order)

        if normalized_type in {"user", "users"}:
            mapping = {
                "fans": bili_search.OrderUser.FANS,
                "level": bili_search.OrderUser.LEVEL,
            }
            return mapping.get(normalized_order)

        if normalized_type in {"article", "articles"}:
            mapping = {
                "totalrank": bili_search.OrderArticle.TOTALRANK,
                "pubdate": bili_search.OrderArticle.PUBDATE,
                "click": bili_search.OrderArticle.CLICK,
                "attention": bili_search.OrderArticle.ATTENTION,
                "scores": bili_search.OrderArticle.SCORES,
            }
            return mapping.get(normalized_order)

        if normalized_type == "live":
            mapping = {
                "newlive": bili_search.OrderLiveRoom.NEWLIVE,
                "live_time": bili_search.OrderLiveRoom.NEWLIVE,
                "online": bili_search.OrderLiveRoom.ONLINE,
            }
            return mapping.get(normalized_order)

        return None

    @staticmethod
    def _normalize_items(search_type: str, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = raw.get("result") if isinstance(raw, dict) else None
        if data is None:
            data = raw.get("data", {}).get("result") if isinstance(raw.get("data"), dict) else None
        if data is None:
            data = raw if isinstance(raw, list) else []

        items = data if isinstance(data, list) else []
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            out.append(
                {
                    "id": item.get("id") or item.get("aid") or item.get("mid") or item.get("roomid") or item.get("season_id"),
                    "type": search_type,
                    "title": item.get("title") or item.get("uname") or item.get("author") or item.get("roomname"),
                    "description": item.get("description") or item.get("desc") or item.get("sign") or item.get("uname"),
                    "author": item.get("author") or item.get("uname") or item.get("upic") or "",
                    "url": item.get("arcurl") or item.get("uri") or item.get("url"),
                    "bvid": item.get("bvid"),
                    "mid": item.get("mid"),
                    "raw": item,
                }
            )
        return out

    async def search(self, keyword: str, page: int = 1) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        data = await bili_search.search(keyword=keyword, page=page)
        return self._success(keyword=keyword, page=page, search_type="all", items=self._normalize_items("all", data), raw=data)

    async def search_by_type(
        self,
        keyword: str,
        search_type: str = "video",
        order: Optional[str] = None,
        page: int = 1,
        page_size: int = 42,
        time_range: int = -1,
        order_sort: Optional[int] = None,
        category_id: Optional[int] = None,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        try:
            search_type_enum = self._normalize_search_type(search_type)
            order_enum = self._normalize_order(search_type, order)
            data = await bili_search.search_by_type(
                keyword=keyword,
                search_type=search_type_enum,
                order_type=order_enum,
                time_range=time_range,
                order_sort=order_sort,
                category_id=category_id,
                time_start=time_start,
                time_end=time_end,
                page=page,
                page_size=page_size,
            )
            return self._success(
                keyword=keyword,
                page=page,
                page_size=page_size,
                search_type=search_type_enum.value,
                order=order,
                items=self._normalize_items(search_type_enum.value, data),
                raw=data,
            )
        except Exception as exc:
            return self._failure("Search failed.", detail=str(exc), keyword=keyword, search_type=search_type)

    async def suggest_keywords(self, keyword: str) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        data = await bili_search.get_suggest_keywords(keyword)
        return self._success(keyword=keyword, items=data)

    async def search_games(self, keyword: str) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        data = await bili_search.search_games(keyword=keyword)
        items = data.get("result") if isinstance(data, dict) else data
        return self._success(keyword=keyword, search_type="game", items=items, raw=data)

    async def search_manga(self, keyword: str, page: int = 1, page_size: int = 9) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        data = await bili_search.search_manga(
            keyword=keyword,
            page_num=page,
            page_size=page_size,
            credential=self._credential(require_auth=False),
        )
        return self._success(keyword=keyword, page=page, page_size=page_size, search_type="manga", items=data.get("list") or data.get("result") or [], raw=data)

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "search": self.search,
            "search_by_type": self.search_by_type,
            "search_videos": lambda **kw: self.search_by_type(search_type="video", **kw),
            "search_users": lambda **kw: self.search_by_type(search_type="user", **kw),
            "search_live": lambda **kw: self.search_by_type(search_type="live", **kw),
            "search_articles": lambda **kw: self.search_by_type(search_type="article", **kw),
            "search_topics": lambda **kw: self.search_by_type(search_type="topic", **kw),
            "search_photos": lambda **kw: self.search_by_type(search_type="photo", **kw),
            "suggest_keywords": self.suggest_keywords,
            "search_games": self.search_games,
            "search_manga": self.search_manga,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown search_client action: {action}")
        return await handler(**kwargs)
