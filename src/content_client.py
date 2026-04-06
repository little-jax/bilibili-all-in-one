"""Content object clients for dynamics, opus, notes, and articles."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .auth import BilibiliAuth
from .client_base import BilibiliClientBase

try:
    from bilibili_api import dynamic as bili_dynamic
    from bilibili_api import opus as bili_opus
    from bilibili_api import note as bili_note
    from bilibili_api import article as bili_article
    BILI_CONTENT_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    bili_dynamic = None
    bili_opus = None
    bili_note = None
    bili_article = None
    BILI_CONTENT_IMPORT_ERROR = str(exc)


class BilibiliContentClient(BilibiliClientBase):
    """First-class content-object client surface."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        super().__init__(auth=auth)

    def _require_content_library(self) -> Optional[Dict[str, Any]]:
        base_error = self._require_library()
        if base_error:
            return base_error
        if BILI_CONTENT_IMPORT_ERROR:
            return self._failure("bilibili_api content modules are unavailable.", detail=BILI_CONTENT_IMPORT_ERROR)
        return None

    @staticmethod
    def _find_first(data: Any, keys: Tuple[str, ...]) -> Any:
        if isinstance(data, dict):
            for key in keys:
                if key in data and data.get(key) not in (None, ""):
                    return data.get(key)
            for value in data.values():
                found = BilibiliContentClient._find_first(value, keys)
                if found not in (None, ""):
                    return found
        elif isinstance(data, list):
            for item in data:
                found = BilibiliContentClient._find_first(item, keys)
                if found not in (None, ""):
                    return found
        return None

    @staticmethod
    def _pick_items(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if not isinstance(data, dict):
            return []
        for key in ("items", "list", "cards", "archives"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        return []

    @staticmethod
    def _snip(value: Any, limit: int = 240) -> str:
        if isinstance(value, dict):
            text = str(value)
        elif isinstance(value, list):
            text = " ".join(str(x) for x in value)
        else:
            text = str(value or "")
        text = " ".join(text.split())
        return text[: limit - 1] + "…" if len(text) > limit else text

    def _normalize_dynamic(self, info: Dict[str, Any], source: Optional[int] = None) -> Dict[str, Any]:
        dynamic_id = self._find_first(info, ("dynamic_id_str", "dynamic_id", "id_str", "id")) or source
        author_uid = self._find_first(info, ("uid", "mid"))
        author_name = self._find_first(info, ("name", "uname", "nickname"))
        text = self._find_first(info, ("text", "desc", "content", "summary")) or info.get("modules") or info.get("item")
        return {
            "type": "dynamic",
            "id": dynamic_id,
            "dynamic_id": dynamic_id,
            "url": self._find_first(info, ("jump_url", "url")),
            "text": self._snip(text, 500),
            "author": {"uid": author_uid, "name": author_name},
            "stats": {
                "likes": self._find_first(info, ("like", "like_count")),
                "comments": self._find_first(info, ("reply", "reply_count")),
                "shares": self._find_first(info, ("repost", "repost_count")),
            },
            "raw": info,
        }

    def _normalize_opus(self, info: Dict[str, Any], source: Optional[int] = None) -> Dict[str, Any]:
        opus_id = self._find_first(info, ("opus_id", "id_str", "id")) or source
        return {
            "type": "opus",
            "id": opus_id,
            "opus_id": opus_id,
            "title": self._find_first(info, ("title", "summary", "desc")) or "",
            "url": self._find_first(info, ("jump_url", "url")),
            "summary": self._snip(self._find_first(info, ("summary", "content", "desc")), 500),
            "author": {
                "uid": self._find_first(info, ("uid", "mid")),
                "name": self._find_first(info, ("name", "uname", "nickname")),
            },
            "stats": {
                "likes": self._find_first(info, ("like", "like_count")),
                "comments": self._find_first(info, ("reply", "reply_count")),
                "shares": self._find_first(info, ("repost", "repost_count")),
            },
            "raw": info,
        }

    def _normalize_note(self, info: Dict[str, Any], source: Optional[int] = None) -> Dict[str, Any]:
        note_id = self._find_first(info, ("note_id", "cvid", "id")) or source
        return {
            "type": "note",
            "id": note_id,
            "note_id": note_id,
            "title": self._find_first(info, ("title", "subject")),
            "url": self._find_first(info, ("jump_url", "url")),
            "summary": self._snip(self._find_first(info, ("summary", "content", "desc")), 500),
            "author": {
                "uid": self._find_first(info, ("uid", "mid")),
                "name": self._find_first(info, ("name", "uname", "nickname")),
            },
            "raw": info,
        }

    def _normalize_article(self, info: Dict[str, Any], source: Optional[int] = None) -> Dict[str, Any]:
        cvid = info.get("cvid") or source
        return {
            "type": "article",
            "id": cvid,
            "cvid": cvid,
            "title": info.get("title"),
            "url": info.get("url") or (f"https://www.bilibili.com/read/cv{cvid}" if cvid else None),
            "summary": self._snip(info.get("summary") or info.get("content") or "", 500),
            "author": {
                "uid": self._find_first(info, ("mid", "uid")),
                "name": self._find_first(info, ("name", "uname", "author_name")),
            },
            "raw": info,
        }

    async def list_user_dynamics(self, uid: int, offset: str = "", need_top: bool = False) -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            user_obj = self._user(uid=uid)
            if offset:
                data = await user_obj.get_dynamics_new(offset=offset)
            else:
                data = await user_obj.get_dynamics(need_top=bool(need_top))
            items = self._pick_items(data)
            normalized = [self._normalize_dynamic(x) for x in items]
            return self._success(
                schema="bilibili.content_client.list_user_dynamics.v1",
                uid=int(uid),
                count=len(normalized),
                items=normalized,
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to list user dynamics: {exc}")

    async def get_dynamic_detail(self, dynamic_id: int) -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            obj = self._dynamic(dynamic_id)
            info = await obj.get_info()
            return self._success(
                schema="bilibili.content_client.get_dynamic_detail.v1",
                item=self._normalize_dynamic(info, source=int(dynamic_id)),
                raw=info,
            )
        except Exception as exc:
            return self._failure(f"Failed to get dynamic detail: {exc}")

    async def dynamic_action(self, dynamic_id: int, operation: str = "reposts", status: bool = True, offset: str = "0") -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            obj = self._dynamic(dynamic_id, require_auth=(operation in {"like", "delete"}))
            normalized = (operation or "reposts").strip().lower()
            if normalized in {"reposts", "list_reposts", "repost_list"}:
                data = await obj.get_reposts(offset=offset)
                items = self._pick_items(data)
                return self._success(
                    schema="bilibili.content_client.dynamic_action.v1",
                    dynamic_id=int(dynamic_id),
                    action="reposts",
                    count=len(items),
                    items=items,
                    raw=data,
                )
            if normalized == "like":
                auth_error = self._require_auth()
                if auth_error:
                    return auth_error
                data = await obj.set_like(status=bool(status))
                return self._success(schema="bilibili.content_client.dynamic_action.v1", dynamic_id=int(dynamic_id), action="like", status=bool(status), raw=data)
            if normalized == "delete":
                auth_error = self._require_auth()
                if auth_error:
                    return auth_error
                data = await obj.delete()
                return self._success(schema="bilibili.content_client.dynamic_action.v1", dynamic_id=int(dynamic_id), action="delete", raw=data)
            return self._failure(f"Unsupported dynamic action: {operation}")
        except Exception as exc:
            return self._failure(f"Failed dynamic action: {exc}")

    async def get_opus_detail(self, opus_id: int) -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            obj = self._opus(opus_id)
            info = await obj.get_info()
            return self._success(
                schema="bilibili.content_client.get_opus_detail.v1",
                item=self._normalize_opus(info, source=int(opus_id)),
                raw=info,
            )
        except Exception as exc:
            return self._failure(f"Failed to get opus detail: {exc}")

    async def get_note_detail(self, note_id: int) -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            obj = self._note(note_id)
            info = await obj.get_info()
            return self._success(
                schema="bilibili.content_client.get_note_detail.v1",
                item=self._normalize_note(info, source=int(note_id)),
                raw=info,
            )
        except Exception as exc:
            return self._failure(f"Failed to get note detail: {exc}")

    async def list_user_articles(self, uid: int, page: int = 1, page_size: int = 30) -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            user_obj = self._user(uid=uid)
            data = await user_obj.get_articles(pn=int(page), ps=int(page_size))
            items = self._pick_items(data)
            normalized = [self._normalize_article(x) for x in items]
            return self._success(
                schema="bilibili.content_client.list_user_articles.v1",
                uid=int(uid),
                page=int(page),
                count=len(normalized),
                items=normalized,
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to list user articles: {exc}")

    async def get_article_detail(self, cvid: int) -> Dict[str, Any]:
        error = self._require_content_library()
        if error:
            return error
        try:
            obj = self._article(cvid)
            data = await obj.get_all()
            return self._success(
                schema="bilibili.content_client.get_article_detail.v1",
                item=self._normalize_article(data, source=int(cvid)),
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get article detail: {exc}")

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "list_user_dynamics": self.list_user_dynamics,
            "get_dynamic_detail": self.get_dynamic_detail,
            "dynamic_action": self.dynamic_action,
            "get_opus_detail": self.get_opus_detail,
            "get_note_detail": self.get_note_detail,
            "list_user_articles": self.list_user_articles,
            "get_article_detail": self.get_article_detail,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown content_client action: {action}")
        if action == "dynamic_action":
            if "operation" not in kwargs:
                for key in ("action_name", "actionType", "action_type", "actionKind", "action_kind"):
                    if key in kwargs:
                        kwargs["operation"] = kwargs.pop(key)
                        break
        return await handler(**kwargs)
