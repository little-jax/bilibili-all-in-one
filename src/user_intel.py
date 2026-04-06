"""User-intel client for profile lookup and creator-facing investigation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .client_base import BilibiliClientBase, bili_user
from .utils import API_STAT


class BilibiliUserIntel(BilibiliClientBase):
    """User profile, content, and lightweight investigation workflows."""

    async def get_my_profile(self) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        profile = await bili_user.get_self_info(self._credential(require_auth=True))
        return self._success(profile=self._normalize_profile(profile), raw=profile)

    async def resolve_name_to_uid(self, name: str) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        data = await bili_user.name2uid(name)
        return self._success(name=name, matches=data)

    async def get_user_profile(self, uid: int) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        try:
            user = self._user(uid)
            info = await user.get_user_info()
            relation = await self._get_relation_stat(uid)
            return self._success(profile=self._normalize_profile(info, relation), raw=info, relation=relation)
        except Exception as exc:
            return self._failure("User profile lookup failed.", uid=int(uid), detail=str(exc))

    async def get_user_videos(
        self,
        uid: int,
        page: int = 1,
        page_size: int = 10,
        keyword: str = "",
        order: str = "pubdate",
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        try:
            user = self._user(uid)
            data = await user.get_videos(
                pn=page,
                ps=page_size,
                keyword=keyword,
                order=self._video_order_from_string(order),
            )
            items = self._normalize_video_items(data)
            return self._success(uid=int(uid), page=page, page_size=page_size, items=items, raw=data)
        except Exception as exc:
            return self._failure("User videos lookup failed.", uid=int(uid), detail=str(exc))

    async def get_user_dynamics(self, uid: int, offset: int = 0, need_top: bool = False) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        try:
            user = self._user(uid)
            data = await user.get_dynamics(offset=offset, need_top=need_top)
            items = self._normalize_dynamic_items(data)
            return self._success(uid=int(uid), offset=offset, need_top=need_top, items=items, raw=data)
        except Exception as exc:
            return self._failure("User dynamics lookup failed.", uid=int(uid), detail=str(exc))

    async def inspect_user(
        self,
        uid: Optional[int] = None,
        name: Optional[str] = None,
        video_limit: int = 5,
        dynamics_limit: int = 5,
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        if uid is None:
            if not name:
                return self._failure("Provide uid or name for inspect_user.")
            resolved = await self.resolve_name_to_uid(name)
            matches = resolved.get("matches") or []
            if not matches:
                return self._failure("Could not resolve username to uid.", name=name)
            uid = int(matches[0]) if not isinstance(matches[0], dict) else int(matches[0].get("uid") or matches[0].get("mid"))

        profile = await self.get_user_profile(uid)
        if not profile.get("success"):
            return profile
        videos = await self.get_user_videos(uid=uid, page_size=max(1, min(video_limit, 30)))
        dynamics = await self.get_user_dynamics(uid=uid)

        recent_videos = (videos.get("items") or [])[:video_limit] if videos.get("success") else []
        recent_dynamics = (dynamics.get("items") or [])[:dynamics_limit] if dynamics.get("success") else []

        return self._success(
            uid=int(uid),
            profile=profile.get("profile"),
            recent_videos=recent_videos,
            recent_dynamics=recent_dynamics,
            partial_failures={
                "videos": None if videos.get("success") else videos.get("message") or videos.get("detail"),
                "dynamics": None if dynamics.get("success") else dynamics.get("message") or dynamics.get("detail"),
            },
            signals=self._infer_signals(
                profile=profile.get("profile") or {},
                videos=recent_videos,
                dynamics=recent_dynamics,
            ),
        )

    async def _get_relation_stat(self, uid: int) -> Dict[str, Any]:
        async with self.auth.get_client() as client:
            resp = await client.get(API_STAT, params={"vmid": int(uid)})
            data = resp.json()
        if data.get("code") != 0:
            return {}
        return data.get("data") or {}

    @staticmethod
    def _normalize_profile(info: Dict[str, Any], relation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        uid = info.get("mid") or info.get("uid")
        relation = relation or {}
        return {
            "uid": uid,
            "name": info.get("name") or info.get("uname"),
            "sign": info.get("sign") or "",
            "avatar": info.get("face"),
            "level": info.get("level") or info.get("level_info", {}).get("current_level"),
            "vip": info.get("vip") or {},
            "sex": info.get("sex"),
            "birthday": info.get("birthday"),
            "fans": relation.get("follower") or info.get("fans"),
            "following": relation.get("following") or info.get("friend"),
            "archive_count": info.get("archive_count"),
            "article_count": info.get("article_count"),
            "url": f"https://space.bilibili.com/{uid}" if uid else None,
        }

    @staticmethod
    def _normalize_video_items(data: Dict[str, Any]):
        items = []
        raw_items = data.get("list", {}).get("vlist") or data.get("vlist") or []
        for item in raw_items:
            items.append(
                {
                    "aid": item.get("aid"),
                    "bvid": item.get("bvid"),
                    "title": item.get("title"),
                    "description": item.get("description") or item.get("desc"),
                    "created": item.get("created"),
                    "length": item.get("length"),
                    "play": item.get("play"),
                    "comment": item.get("comment"),
                    "url": f"https://www.bilibili.com/video/{item.get('bvid')}" if item.get("bvid") else None,
                    "raw": item,
                }
            )
        return items

    @staticmethod
    def _normalize_dynamic_items(data: Dict[str, Any]):
        cards = data.get("cards") or data.get("items") or []
        items = []
        for item in cards:
            desc = item.get("desc") or item.get("modules") or item.get("basic") or {}
            items.append(
                {
                    "id": desc.get("dynamic_id") or desc.get("dynamic_id_str") or item.get("id_str") or item.get("id"),
                    "type": item.get("type") or desc.get("type"),
                    "text": str(item)[:500],
                    "raw": item,
                }
            )
        return items

    @staticmethod
    def _infer_signals(profile: Dict[str, Any], videos: list, dynamics: list) -> Dict[str, Any]:
        fans = profile.get("fans") or 0
        archive_count = profile.get("archive_count") or 0
        likely_creator = archive_count > 0 or len(videos) > 0 or fans >= 100
        active = len(videos) > 0 or len(dynamics) > 0
        return {
            "likely_creator": bool(likely_creator),
            "active_account": bool(active),
            "audience_size": "large" if fans >= 100000 else "medium" if fans >= 5000 else "small",
            "has_recent_content": bool(videos or dynamics),
        }

    @staticmethod
    def _video_order_from_string(order: str):
        normalized = (order or "pubdate").strip().lower()
        mapping = {
            "pubdate": bili_user.VideoOrder.PUBDATE,
            "favorite": bili_user.VideoOrder.FAVORITE,
            "fav": bili_user.VideoOrder.FAVORITE,
            "view": bili_user.VideoOrder.VIEW,
            "click": bili_user.VideoOrder.VIEW,
        }
        return mapping.get(normalized, bili_user.VideoOrder.PUBDATE)

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "get_my_profile": self.get_my_profile,
            "resolve_name_to_uid": self.resolve_name_to_uid,
            "get_user_profile": self.get_user_profile,
            "get_user_videos": self.get_user_videos,
            "get_user_dynamics": self.get_user_dynamics,
            "inspect_user": self.inspect_user,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown user_intel action: {action}")
        return await handler(**kwargs)
