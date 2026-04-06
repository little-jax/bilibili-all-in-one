"""Shared client base for Bilibili client-kernel modules."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .auth import BilibiliAuth
from .utils import API_VIDEO_DETAIL, API_VIDEO_INFO, DEFAULT_HEADERS, extract_bvid, format_duration, format_number

try:
    from bilibili_api import Credential
    from bilibili_api import ResourceType
    from bilibili_api import parse_link
    from bilibili_api import search as bili_search
    from bilibili_api import user as bili_user
    from bilibili_api import video as bili_video
    from bilibili_api import dynamic as bili_dynamic
    from bilibili_api import comment as bili_comment
    from bilibili_api import note as bili_note
    from bilibili_api import opus as bili_opus
    from bilibili_api import article as bili_article
    BILIBILI_API_AVAILABLE = True
    BILIBILI_API_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    Credential = None
    ResourceType = None
    parse_link = None
    bili_search = None
    bili_user = None
    bili_video = None
    bili_dynamic = None
    bili_comment = None
    bili_note = None
    bili_opus = None
    bili_article = None
    BILIBILI_API_AVAILABLE = False
    BILIBILI_API_IMPORT_ERROR = str(exc)


class BilibiliClientBase:
    """Common auth, library, and object helpers for Bilibili client modules."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        self.auth = auth or BilibiliAuth()

    def _require_library(self) -> Optional[Dict[str, Any]]:
        if BILIBILI_API_AVAILABLE:
            return None
        return {
            "success": False,
            "message": (
                "bilibili_api library is required for this action. "
                "Install with: pip install bilibili-api-python aiohttp"
            ),
            "detail": BILIBILI_API_IMPORT_ERROR,
        }

    def _require_auth(self) -> Optional[Dict[str, Any]]:
        if self.auth and self.auth.is_authenticated:
            return None
        return {
            "success": False,
            "message": "Authenticated Bilibili cookies are required for this action.",
        }

    def _credential(self, require_auth: bool = False):
        lib_error = self._require_library()
        if lib_error:
            raise RuntimeError(lib_error["message"])
        if require_auth and (auth_error := self._require_auth()):
            raise RuntimeError(auth_error["message"])
        return Credential(
            sessdata=self.auth.sessdata or "",
            bili_jct=self.auth.bili_jct or "",
            buvid3=self.auth.buvid3 or "",
        )

    def _get_client(self) -> httpx.AsyncClient:
        if self.auth:
            return self.auth.get_client()
        return httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    def _resolve_bvid(self, url: Optional[str] = None, bvid: Optional[str] = None) -> Optional[str]:
        return extract_bvid(bvid or url or "")

    def _video(self, url: Optional[str] = None, bvid: Optional[str] = None, require_auth: bool = False):
        resolved = self._resolve_bvid(url=url, bvid=bvid)
        if not resolved:
            raise ValueError("A valid Bilibili BV id or video URL is required.")
        return bili_video.Video(bvid=resolved, credential=self._credential(require_auth=require_auth))

    def _user(self, uid: int, require_auth: bool = False):
        return bili_user.User(int(uid), credential=self._credential(require_auth=require_auth))

    def _dynamic(self, dynamic_id: int, require_auth: bool = False):
        return bili_dynamic.Dynamic(dynamic_id=int(dynamic_id), credential=self._credential(require_auth=require_auth))

    def _note(self, note_id: int, require_auth: bool = False):
        return bili_note.Note(note_id=int(note_id), credential=self._credential(require_auth=require_auth))

    def _opus(self, opus_id: int, require_auth: bool = False):
        return bili_opus.Opus(opus_id=int(opus_id), credential=self._credential(require_auth=require_auth))

    def _article(self, cvid: int, require_auth: bool = False):
        return bili_article.Article(cvid=int(cvid), credential=self._credential(require_auth=require_auth))

    async def _fetch_video_info_data(self, bvid: str) -> Dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.get(API_VIDEO_INFO, params={"bvid": bvid})
            try:
                data = resp.json()
            except Exception:
                preview = (resp.text or "")[:200]
                raise RuntimeError(f"Non-JSON response from video info API: {preview}")
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "API error"))
        return data.get("data") or {}

    async def _fetch_video_detail_data(self, bvid: str) -> Dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.get(API_VIDEO_DETAIL, params={"bvid": bvid})
            try:
                data = resp.json()
            except Exception:
                preview = (resp.text or "")[:200]
                raise RuntimeError(f"Non-JSON response from video detail API: {preview}")
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "API error"))
        return data.get("data") or {}

    @staticmethod
    def _normalize_video_summary(video: Dict[str, Any]) -> Dict[str, Any]:
        stat = video.get("stat", {})
        owner = video.get("owner", {})
        pages = [
            {
                "page": p.get("page"),
                "cid": p.get("cid"),
                "title": p.get("part"),
                "duration": format_duration(p.get("duration", 0)),
                "duration_seconds": p.get("duration", 0),
            }
            for p in video.get("pages", [])
        ]
        return {
            "bvid": video.get("bvid"),
            "aid": video.get("aid"),
            "title": video.get("title"),
            "description": video.get("desc"),
            "cover": video.get("pic"),
            "duration": format_duration(video.get("duration", 0)),
            "duration_seconds": video.get("duration", 0),
            "author": {
                "mid": owner.get("mid"),
                "name": owner.get("name"),
                "face": owner.get("face"),
            },
            "stats": {
                "views": stat.get("view", 0),
                "views_formatted": format_number(stat.get("view", 0)),
                "likes": stat.get("like", 0),
                "likes_formatted": format_number(stat.get("like", 0)),
                "coins": stat.get("coin", 0),
                "coins_formatted": format_number(stat.get("coin", 0)),
                "favorites": stat.get("favorite", 0),
                "favorites_formatted": format_number(stat.get("favorite", 0)),
                "danmaku": stat.get("danmaku", 0),
                "shares": stat.get("share", 0),
                "comments": stat.get("reply", 0),
            },
            "pages": pages,
            "page_count": len(pages),
            "url": f"https://www.bilibili.com/video/{video.get('bvid')}" if video.get("bvid") else None,
            "raw": video,
        }

    @staticmethod
    def _success(**kwargs) -> Dict[str, Any]:
        return {"success": True, **kwargs}

    @staticmethod
    def _failure(message: str, **kwargs) -> Dict[str, Any]:
        return {"success": False, "message": message, **kwargs}
