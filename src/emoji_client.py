"""Emoji surface for Bilibili-native expression packs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .auth import BilibiliAuth
from .client_base import BilibiliClientBase

try:
    from bilibili_api import emoji as bili_emoji
    BILI_EMOJI_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    bili_emoji = None
    BILI_EMOJI_IMPORT_ERROR = str(exc)


class BilibiliEmojiClient(BilibiliClientBase):
    """Read/manage Bilibili emoji packs and suggest lightweight usage."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        super().__init__(auth=auth)

    def _require_emoji_library(self) -> Optional[Dict[str, Any]]:
        base_error = self._require_library()
        if base_error:
            return base_error
        if BILI_EMOJI_IMPORT_ERROR:
            return self._failure("bilibili_api emoji module is unavailable.", detail=BILI_EMOJI_IMPORT_ERROR)
        return None

    @staticmethod
    def _packages(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        packages = data.get("packages") or data.get("list") or []
        return [x for x in packages if isinstance(x, dict)]

    @staticmethod
    def _emotes(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
        for key in ("emote", "emoji", "emotes", "items", "list"):
            value = pkg.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return []

    @staticmethod
    def _norm_package(pkg: Dict[str, Any]) -> Dict[str, Any]:
        emotes = BilibiliEmojiClient._emotes(pkg)
        return {
            "id": pkg.get("id") or pkg.get("package_id") or pkg.get("pkg_id"),
            "package_id": pkg.get("package_id") or pkg.get("id") or pkg.get("pkg_id"),
            "name": pkg.get("text") or pkg.get("title") or pkg.get("pkg_name") or pkg.get("name"),
            "cover": pkg.get("url") or pkg.get("cover") or pkg.get("image"),
            "state": pkg.get("state"),
            "count": len(emotes),
            "raw": pkg,
        }

    @staticmethod
    def _norm_emote(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id") or item.get("emote_id"),
            "text": item.get("text") or item.get("emoji") or item.get("name"),
            "url": item.get("url") or item.get("gif_url") or item.get("image"),
            "meta": {
                "type": item.get("type"),
                "size": item.get("size"),
                "flags": item.get("flags"),
            },
            "raw": item,
        }

    async def list_emoji_packages(self, business: str = "reply", include_all: bool = False) -> Dict[str, Any]:
        error = self._require_emoji_library()
        if error:
            return error
        try:
            if include_all:
                auth_error = self._require_auth()
                if auth_error:
                    return auth_error
                data = await bili_emoji.get_all_emoji(business=business, credential=self._credential(require_auth=True))
            else:
                data = await bili_emoji.get_emoji_list(business=business, credential=self._credential())
            packages = self._packages(data)
            return self._success(
                schema="bilibili.emoji_client.list_emoji_packages.v1",
                business=business,
                include_all=bool(include_all),
                count=len(packages),
                items=[self._norm_package(x) for x in packages],
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to list emoji packages: {exc}")

    async def get_emoji_package_detail(self, ids: List[int], business: str = "reply") -> Dict[str, Any]:
        error = self._require_emoji_library()
        if error:
            return error
        try:
            data = await bili_emoji.get_emoji_detail(id=[int(x) for x in ids], business=business)
            packages = self._packages(data)
            normalized = []
            for pkg in packages:
                normalized.append({
                    **self._norm_package(pkg),
                    "emotes": [self._norm_emote(x) for x in self._emotes(pkg)],
                })
            return self._success(
                schema="bilibili.emoji_client.get_emoji_package_detail.v1",
                business=business,
                ids=[int(x) for x in ids],
                count=len(normalized),
                items=normalized,
                raw=data,
            )
        except Exception as exc:
            return self._failure(f"Failed to get emoji package detail: {exc}")

    async def add_emoji_package(self, package_id: int) -> Dict[str, Any]:
        error = self._require_emoji_library() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_emoji.add_emoji(package_id=int(package_id), credential=self._credential(require_auth=True))
            return self._success(schema="bilibili.emoji_client.add_emoji_package.v1", package_id=int(package_id), raw=data)
        except Exception as exc:
            return self._failure(f"Failed to add emoji package: {exc}")

    async def suggest_emojis(
        self,
        business: str = "reply",
        query: Optional[str] = None,
        limit: int = 8,
        include_all: bool = False,
    ) -> Dict[str, Any]:
        listed = await self.list_emoji_packages(business=business, include_all=include_all)
        if not listed.get("success"):
            return listed
        hits: List[Dict[str, Any]] = []
        q = (query or "").strip().lower()
        for pkg in listed.get("items") or []:
            raw_pkg = pkg.get("raw") or {}
            for em in self._emotes(raw_pkg):
                normalized = self._norm_emote(em)
                hay = " ".join(str(x) for x in [normalized.get("text"), em.get("alias"), em.get("name")] if x).lower()
                if not q or q in hay:
                    hits.append({
                        "package": {
                            "id": pkg.get("id"),
                            "name": pkg.get("name"),
                        },
                        **normalized,
                    })
                if len(hits) >= int(limit):
                    break
            if len(hits) >= int(limit):
                break
        return self._success(
            schema="bilibili.emoji_client.suggest_emojis.v1",
            business=business,
            query=query,
            count=len(hits),
            items=hits,
            guidance="Use these sparingly in DMs/replies/comments to feel more native; do not over-decorate every message.",
        )

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "list_emoji_packages": self.list_emoji_packages,
            "get_emoji_package_detail": self.get_emoji_package_detail,
            "add_emoji_package": self.add_emoji_package,
            "suggest_emojis": self.suggest_emojis,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown emoji_client action: {action}")
        return await handler(**kwargs)
