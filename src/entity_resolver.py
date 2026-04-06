"""Unified entity resolver for Bilibili URLs and identifiers."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .client_base import (
    BilibiliClientBase,
    ResourceType,
    parse_link,
    bili_video,
    bili_user,
    bili_dynamic,
    bili_note,
    bili_opus,
    bili_article,
)
from .utils import extract_aid, extract_bvid


class BilibiliEntityResolver(BilibiliClientBase):
    """Resolve Bilibili URLs / IDs into normalized entities."""

    @staticmethod
    def _find_first(data: Any, keys: Tuple[str, ...]) -> Any:
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key] not in (None, "", [], {}):
                    return data[key]
            for value in data.values():
                found = BilibiliEntityResolver._find_first(value, keys)
                if found not in (None, "", [], {}):
                    return found
        elif isinstance(data, list):
            for item in data:
                found = BilibiliEntityResolver._find_first(item, keys)
                if found not in (None, "", [], {}):
                    return found
        return None

    @staticmethod
    def _snip(value: Any, limit: int = 280) -> str:
        text = "" if value is None else str(value)
        text = " ".join(text.split())
        return text[:limit]

    async def resolve(
        self,
        target: Optional[str] = None,
        url: Optional[str] = None,
        bvid: Optional[str] = None,
        aid: Optional[int] = None,
        uid: Optional[int] = None,
        dynamic_id: Optional[int] = None,
        opus_id: Optional[int] = None,
        note_id: Optional[int] = None,
        cvid: Optional[int] = None,
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        target = target or url
        try:
            if bvid or aid or (target and (extract_bvid(target) or extract_aid(target))):
                resolved_bvid = bvid or (extract_bvid(target or ""))
                resolved_aid = aid or extract_aid(target or "")
                obj = bili_video.Video(
                    bvid=resolved_bvid,
                    aid=resolved_aid,
                    credential=self._credential(require_auth=False),
                )
                return await self._normalize_resource(obj, "video", source=target or resolved_bvid or resolved_aid)

            if uid is not None:
                return await self._normalize_resource(self._user(uid), "user", source=uid)
            if dynamic_id is not None:
                return await self._normalize_resource(self._dynamic(dynamic_id), "dynamic", source=dynamic_id)
            if opus_id is not None:
                return await self._normalize_resource(self._opus(opus_id), "opus", source=opus_id)
            if note_id is not None:
                return await self._normalize_resource(self._note(note_id), "note", source=note_id)
            if cvid is not None:
                return await self._normalize_resource(self._article(cvid), "article", source=cvid)

            if not target:
                return self._failure("Provide target/url/bvid/uid/dynamic_id/opus_id/note_id/cvid to resolve.")

            obj, resource_type = await parse_link(target, credential=self._credential(require_auth=False))
            if resource_type == ResourceType.FAILED or obj == -1:
                return self._failure("Could not resolve target.", target=target)
            return await self._normalize_resource(obj, resource_type.value, source=target)
        except Exception as exc:
            return self._failure("Entity resolution failed.", detail=str(exc), target=target)

    async def resolve_url(self, url: str) -> Dict[str, Any]:
        return await self.resolve(url=url)

    async def _normalize_resource(self, obj: Any, resource_type: str, source: Any = None) -> Dict[str, Any]:
        normalized_type = (resource_type or "unknown").lower()

        if normalized_type in {"video", "interactive_video"}:
            info = await obj.get_info()
            owner = info.get("owner", {})
            stat = info.get("stat", {})
            return self._success(
                entity={
                    "type": "video",
                    "id": info.get("aid"),
                    "bvid": info.get("bvid"),
                    "title": info.get("title"),
                    "url": f"https://www.bilibili.com/video/{info.get('bvid')}",
                    "author": {
                        "uid": owner.get("mid"),
                        "name": owner.get("name"),
                    },
                    "stats": stat,
                },
                source=source,
                raw=info,
            )

        if normalized_type == "user":
            info = await obj.get_user_info()
            uid = info.get("mid") or info.get("uid")
            return self._success(
                entity={
                    "type": "user",
                    "id": uid,
                    "uid": uid,
                    "name": info.get("name") or info.get("uname"),
                    "url": f"https://space.bilibili.com/{uid}" if uid else None,
                    "sign": info.get("sign"),
                    "level": info.get("level"),
                    "fans": info.get("fans"),
                    "friend": info.get("friend"),
                },
                source=source,
                raw=info,
            )

        if normalized_type == "dynamic":
            info = await obj.get_info()
            dynamic_id = self._find_first(info, ("dynamic_id_str", "dynamic_id", "id_str", "id")) or source
            author_uid = self._find_first(info, ("uid", "mid"))
            author_name = self._find_first(info, ("name", "uname", "nickname"))
            text = self._find_first(info, ("text", "desc", "content", "summary")) or info.get("modules") or info.get("item")
            jump_url = self._find_first(info, ("jump_url", "url"))
            return self._success(
                entity={
                    "type": "dynamic",
                    "id": dynamic_id,
                    "dynamic_id": dynamic_id,
                    "url": jump_url,
                    "text": self._snip(text, 500),
                    "author": {
                        "uid": author_uid,
                        "name": author_name,
                    },
                    "stats": {
                        "likes": self._find_first(info, ("like", "like_count")),
                        "comments": self._find_first(info, ("reply", "reply_count")),
                        "shares": self._find_first(info, ("repost", "repost_count")),
                    },
                },
                source=source,
                raw=info,
            )

        if normalized_type == "note":
            info = await obj.get_info()
            note_id_value = self._find_first(info, ("note_id", "cvid", "id")) or source
            author_uid = self._find_first(info, ("uid", "mid"))
            author_name = self._find_first(info, ("name", "uname", "nickname"))
            return self._success(
                entity={
                    "type": "note",
                    "id": note_id_value,
                    "note_id": note_id_value,
                    "title": self._find_first(info, ("title", "subject")),
                    "url": self._find_first(info, ("jump_url", "url")),
                    "summary": self._snip(self._find_first(info, ("summary", "content", "desc")), 500),
                    "author": {
                        "uid": author_uid,
                        "name": author_name,
                    },
                },
                source=source,
                raw=info,
            )

        if normalized_type == "opus":
            info = await obj.get_info()
            opus_id_value = self._find_first(info, ("opus_id", "id_str", "id")) or source
            author_uid = self._find_first(info, ("uid", "mid"))
            author_name = self._find_first(info, ("name", "uname", "nickname"))
            return self._success(
                entity={
                    "type": "opus",
                    "id": opus_id_value,
                    "opus_id": opus_id_value,
                    "title": self._find_first(info, ("title", "summary", "desc")) or "",
                    "url": self._find_first(info, ("jump_url", "url")),
                    "summary": self._snip(self._find_first(info, ("summary", "content", "desc")), 500),
                    "author": {
                        "uid": author_uid,
                        "name": author_name,
                    },
                    "stats": {
                        "likes": self._find_first(info, ("like", "like_count")),
                        "comments": self._find_first(info, ("reply", "reply_count")),
                    },
                },
                source=source,
                raw=info,
            )

        if normalized_type == "article":
            data = await obj.get_all()
            cvid_value = data.get("cvid") or source
            return self._success(
                entity={
                    "type": "article",
                    "id": cvid_value,
                    "cvid": cvid_value,
                    "title": data.get("title"),
                    "url": data.get("url") or (f"https://www.bilibili.com/read/cv{data.get('cvid')}" if data.get("cvid") else None),
                    "summary": self._snip(data.get("summary") or data.get("content") or "", 500),
                    "author": {
                        "uid": self._find_first(data, ("mid", "uid")),
                        "name": self._find_first(data, ("name", "uname", "author_name")),
                    },
                },
                source=source,
                raw=data,
            )

        return self._success(
            entity={
                "type": normalized_type,
                "id": source,
                "title": None,
                "url": None,
            },
            source=source,
            raw={"resource_type": normalized_type},
        )

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "resolve": self.resolve,
            "resolve_url": self.resolve_url,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown entity_resolver action: {action}")
        return await handler(**kwargs)
