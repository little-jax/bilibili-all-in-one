"""Account asset surfaces: favorites, watch-later, and channel-series collections."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .auth import BilibiliAuth
from .client_base import BilibiliClientBase

try:
    from bilibili_api import favorite_list as bili_favorite_list
    from bilibili_api import user as bili_user
    from bilibili_api import video as bili_video
    from bilibili_api import channel_series as bili_channel_series
    BILI_ASSET_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    bili_favorite_list = None
    bili_user = None
    bili_video = None
    bili_channel_series = None
    BILI_ASSET_IMPORT_ERROR = str(exc)


class BilibiliAssetClient(BilibiliClientBase):
    """Asset/account-oriented Bilibili client surface."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        super().__init__(auth=auth)

    def _require_asset_library(self) -> Optional[Dict[str, Any]]:
        base_error = self._require_library()
        if base_error:
            return base_error
        if BILI_ASSET_IMPORT_ERROR:
            return self._failure(
                "bilibili_api asset modules are unavailable.",
                detail=BILI_ASSET_IMPORT_ERROR,
            )
        return None

    @staticmethod
    def _pick_items(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if not isinstance(data, dict):
            return []
        for key in (
            "items",
            "list",
            "medias",
            "archives",
            "videos",
            "series",
            "seasons",
            "favorites",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        return []

    @staticmethod
    def _norm_favorite_list(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id") or item.get("media_id") or item.get("mlid"),
            "media_id": item.get("media_id") or item.get("id") or item.get("mlid"),
            "title": item.get("title") or item.get("name"),
            "intro": item.get("intro") or item.get("introduction"),
            "count": item.get("media_count") or item.get("count") or item.get("fav_state"),
            "cover": item.get("cover") or item.get("cover_url"),
            "private": item.get("attr") == 1 or item.get("private") is True,
            "raw": item,
        }

    @staticmethod
    def _norm_archive(item: Dict[str, Any]) -> Dict[str, Any]:
        upper = item.get("upper") or item.get("owner") or {}
        return {
            "aid": item.get("aid"),
            "bvid": item.get("bvid"),
            "title": item.get("title"),
            "cover": item.get("cover") or item.get("pic"),
            "duration": item.get("duration"),
            "author": {
                "mid": upper.get("mid"),
                "name": upper.get("name") or upper.get("uname"),
            },
            "fav_time": item.get("fav_time") or item.get("mtime"),
            "pubtime": item.get("pubtime"),
            "raw": item,
        }

    @staticmethod
    def _norm_watch_later(item: Dict[str, Any]) -> Dict[str, Any]:
        owner = item.get("owner") or {}
        return {
            "aid": item.get("aid"),
            "bvid": item.get("bvid"),
            "title": item.get("title"),
            "cover": item.get("pic") or item.get("cover"),
            "duration": item.get("duration"),
            "author": {
                "mid": owner.get("mid"),
                "name": owner.get("name"),
            },
            "state": item.get("state"),
            "progress": item.get("progress"),
            "raw": item,
        }

    @staticmethod
    def _norm_channel(item: Dict[str, Any]) -> Dict[str, Any]:
        meta = item.get("meta") or item
        return {
            "id": meta.get("series_id") or meta.get("season_id") or meta.get("id"),
            "series_id": meta.get("series_id") or meta.get("id"),
            "season_id": meta.get("season_id"),
            "type": meta.get("type") or meta.get("season_type") or meta.get("series_type"),
            "name": meta.get("name") or meta.get("title"),
            "description": meta.get("description") or meta.get("intro"),
            "cover": meta.get("cover"),
            "count": meta.get("total") or meta.get("archives") or meta.get("count"),
            "raw": item,
        }

    async def list_video_favorite_lists(self, uid: int, bvid: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        error = self._require_asset_library()
        if error:
            return error
        try:
            video_obj = self._video(url=url, bvid=bvid) if (bvid or url) else None
            data = await bili_favorite_list.get_video_favorite_list(
                uid=int(uid),
                video=video_obj,
                credential=self._credential(),
            )
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.asset_client.list_video_favorite_lists.v1",
                uid=int(uid),
                count=len(items),
                items=[self._norm_favorite_list(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to list video favorite lists: {exc}")

    async def get_video_favorite_list_content(
        self,
        media_id: int,
        page: int = 1,
        keyword: Optional[str] = None,
        order: str = "mtime",
        tid: int = 0,
        mode: str = "only",
    ) -> Dict[str, Any]:
        error = self._require_asset_library()
        if error:
            return error
        try:
            order_enum = getattr(bili_favorite_list.FavoriteListContentOrder, (order or "mtime").upper(), bili_favorite_list.FavoriteListContentOrder.MTIME)
            mode_enum = getattr(bili_favorite_list.SearchFavoriteListMode, (mode or "only").upper(), bili_favorite_list.SearchFavoriteListMode.ONLY)
            data = await bili_favorite_list.get_video_favorite_list_content(
                media_id=int(media_id),
                page=int(page),
                keyword=keyword,
                order=order_enum,
                tid=int(tid),
                mode=mode_enum,
                credential=self._credential(),
            )
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.asset_client.get_video_favorite_list_content.v1",
                media_id=int(media_id),
                page=int(page),
                count=len(items),
                items=[self._norm_archive(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get favorite list content: {exc}")

    async def create_video_favorite_list(self, title: str, introduction: str = "", private: bool = False) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_favorite_list.create_video_favorite_list(
                title=title,
                introduction=introduction,
                private=bool(private),
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.create_video_favorite_list.v1", title=title, private=bool(private), raw=data)
        except Exception as exc:
            return self._failure(f"Failed to create favorite list: {exc}")

    async def modify_video_favorite_list(self, media_id: int, title: str, introduction: str = "", private: bool = False) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_favorite_list.modify_video_favorite_list(
                media_id=int(media_id),
                title=title,
                introduction=introduction,
                private=bool(private),
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.modify_video_favorite_list.v1", media_id=int(media_id), raw=data)
        except Exception as exc:
            return self._failure(f"Failed to modify favorite list: {exc}")

    async def delete_video_favorite_list(self, media_ids: List[int]) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_favorite_list.delete_video_favorite_list(
                media_ids=[int(x) for x in media_ids],
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.delete_video_favorite_list.v1", media_ids=[int(x) for x in media_ids], raw=data)
        except Exception as exc:
            return self._failure(f"Failed to delete favorite list: {exc}")

    async def set_video_favorite(
        self,
        bvid: Optional[str] = None,
        url: Optional[str] = None,
        add_media_ids: Optional[List[int]] = None,
        del_media_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            v = self._video(url=url, bvid=bvid, require_auth=True)
            data = await v.set_favorite(
                add_media_ids=[int(x) for x in (add_media_ids or [])],
                del_media_ids=[int(x) for x in (del_media_ids or [])],
            )
            return self._success(
                schema="bilibili.asset_client.set_video_favorite.v1",
                bvid=self._resolve_bvid(url=url, bvid=bvid),
                add_media_ids=[int(x) for x in (add_media_ids or [])],
                del_media_ids=[int(x) for x in (del_media_ids or [])],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to update video favorite state: {exc}")

    async def list_watch_later(self) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_user.get_toview_list(self._credential(require_auth=True))
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.asset_client.list_watch_later.v1",
                count=len(items),
                items=[self._norm_watch_later(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to list watch-later items: {exc}")

    async def add_to_watch_later(self, bvid: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            v = self._video(url=url, bvid=bvid, require_auth=True)
            data = await v.add_to_toview()
            return self._success(schema="bilibili.asset_client.add_to_watch_later.v1", bvid=self._resolve_bvid(url=url, bvid=bvid), raw=data)
        except Exception as exc:
            return self._failure(f"Failed to add video to watch-later: {exc}")

    async def remove_from_watch_later(self, bvid: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            v = self._video(url=url, bvid=bvid, require_auth=True)
            data = await v.delete_from_toview()
            return self._success(schema="bilibili.asset_client.remove_from_watch_later.v1", bvid=self._resolve_bvid(url=url, bvid=bvid), raw=data)
        except Exception as exc:
            return self._failure(f"Failed to remove video from watch-later: {exc}")

    async def list_channel_series(self, uid: int) -> Dict[str, Any]:
        error = self._require_asset_library()
        if error:
            return error
        try:
            user_obj = self._user(uid=uid)
            data = await user_obj.get_channel_list()
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.asset_client.list_channel_series.v1",
                uid=int(uid),
                count=len(items),
                items=[self._norm_channel(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to list channel series: {exc}")

    async def get_channel_series_videos(
        self,
        uid: int,
        series_id: int,
        channel_type: str = "series",
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        error = self._require_asset_library()
        if error:
            return error
        try:
            user_obj = self._user(uid=uid)
            normalized = (channel_type or "series").strip().lower()
            if normalized == "season":
                data = await user_obj.get_channel_videos_season(sid=int(series_id), pn=int(page), ps=int(page_size))
            else:
                data = await user_obj.get_channel_videos_series(sid=int(series_id), pn=int(page), ps=int(page_size))
            items = self._pick_items(data)
            return self._success(
                schema="bilibili.asset_client.get_channel_series_videos.v1",
                uid=int(uid),
                series_id=int(series_id),
                channel_type=normalized,
                page=int(page),
                count=len(items),
                items=[self._norm_archive(x) for x in items],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get channel series videos: {exc}")

    async def create_channel_series(
        self,
        name: str,
        aids: Optional[List[int]] = None,
        keywords: Optional[List[str]] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_channel_series.create_channel_series(
                name=name,
                aids=[int(x) for x in (aids or [])],
                keywords=keywords or [],
                description=description,
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.create_channel_series.v1", name=name, raw=data)
        except Exception as exc:
            return self._failure(f"Failed to create channel series: {exc}")

    async def add_videos_to_channel_series(self, series_id: int, aids: List[int]) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_channel_series.add_aids_to_series(
                series_id=int(series_id),
                aids=[int(x) for x in aids],
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.add_videos_to_channel_series.v1", series_id=int(series_id), aids=[int(x) for x in aids], raw=data)
        except Exception as exc:
            return self._failure(f"Failed to add videos to channel series: {exc}")

    async def remove_videos_from_channel_series(self, series_id: int, aids: List[int]) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_channel_series.del_aids_from_series(
                series_id=int(series_id),
                aids=[int(x) for x in aids],
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.remove_videos_from_channel_series.v1", series_id=int(series_id), aids=[int(x) for x in aids], raw=data)
        except Exception as exc:
            return self._failure(f"Failed to remove videos from channel series: {exc}")

    async def delete_channel_series(self, series_id: int) -> Dict[str, Any]:
        error = self._require_asset_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_channel_series.del_channel_series(
                series_id=int(series_id),
                credential=self._credential(require_auth=True),
            )
            return self._success(schema="bilibili.asset_client.delete_channel_series.v1", series_id=int(series_id), raw=data)
        except Exception as exc:
            return self._failure(f"Failed to delete channel series: {exc}")

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "list_video_favorite_lists": self.list_video_favorite_lists,
            "get_video_favorite_list_content": self.get_video_favorite_list_content,
            "create_video_favorite_list": self.create_video_favorite_list,
            "modify_video_favorite_list": self.modify_video_favorite_list,
            "delete_video_favorite_list": self.delete_video_favorite_list,
            "set_video_favorite": self.set_video_favorite,
            "list_watch_later": self.list_watch_later,
            "add_to_watch_later": self.add_to_watch_later,
            "remove_from_watch_later": self.remove_from_watch_later,
            "list_channel_series": self.list_channel_series,
            "get_channel_series_videos": self.get_channel_series_videos,
            "create_channel_series": self.create_channel_series,
            "add_videos_to_channel_series": self.add_videos_to_channel_series,
            "remove_videos_from_channel_series": self.remove_videos_from_channel_series,
            "delete_channel_series": self.delete_channel_series,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown asset_client action: {action}")
        return await handler(**kwargs)
