"""Bilibili message center module.

Creator-facing inbox surface for operations automation.

Scope:
- unread counters
- replies / @ / likes / system notifications
- session list and DM thread history
- sending plain-text DMs
- digest/summary entrypoints suitable for cron and downstream notification bridges
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .auth import BilibiliAuth
from .automation_config import load_message_center_config

try:
    from bilibili_api import Credential
    from bilibili_api import session as bili_session
    from bilibili_api import user as bili_user
    BILIBILI_API_AVAILABLE = True
    BILIBILI_API_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    Credential = None
    bili_session = None
    bili_user = None
    BILIBILI_API_AVAILABLE = False
    BILIBILI_API_IMPORT_ERROR = str(exc)


class BilibiliMessageCenter:
    """Unified inbox and DM helper for Bilibili creator ops."""

    def __init__(self, auth: BilibiliAuth):
        self.auth = auth
        self.config = load_message_center_config()

    def _require_library(self) -> Optional[Dict[str, Any]]:
        if BILIBILI_API_AVAILABLE:
            return None
        return {
            "success": False,
            "message": "bilibili_api library is required for message center actions.",
            "detail": BILIBILI_API_IMPORT_ERROR,
        }

    def _require_auth(self) -> Optional[Dict[str, Any]]:
        if self.auth and self.auth.is_authenticated:
            return None
        return {
            "success": False,
            "message": "Authenticated Bilibili cookies are required for message center actions.",
        }

    def _credential(self):
        return Credential(
            sessdata=self.auth.sessdata or "",
            bili_jct=self.auth.bili_jct or "",
            buvid3=self.auth.buvid3 or "",
            dedeuserid=getattr(self.auth, "dedeuserid", "") or "",
        )

    @staticmethod
    def _count_candidates(value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for key in (
                "items",
                "item",
                "list",
                "lists",
                "messages",
                "message_list",
                "session_list",
                "replies",
                "notifications",
            ):
                inner = value.get(key)
                if isinstance(inner, list):
                    return len(inner)
                if isinstance(inner, dict):
                    nested = BilibiliMessageCenter._count_candidates(inner)
                    if nested:
                        return nested
        return 0

    @staticmethod
    def _truncate(text: Any, max_len: int = 80) -> str:
        if text is None:
            return ""
        s = str(text).replace("\n", " ").strip()
        if len(s) <= max_len:
            return s
        return s[: max_len - 1] + "…"

    @staticmethod
    def _extract_sessions_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(data, dict):
            return []
        for key in ("session_list", "sessions", "items", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = BilibiliMessageCenter._extract_sessions_list(value)
                if nested:
                    return nested
        return []

    @staticmethod
    def _extract_messages_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(data, dict):
            return []
        for key in ("messages", "message_list", "items", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = BilibiliMessageCenter._extract_messages_list(value)
                if nested:
                    return nested
        return []

    @staticmethod
    def _extract_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in (
                "content",
                "text",
                "msg_content",
                "message",
                "title",
                "notice",
                "desc",
            ):
                inner = value.get(key)
                if isinstance(inner, str) and inner.strip():
                    return inner
                if isinstance(inner, dict):
                    nested = BilibiliMessageCenter._extract_text(inner)
                    if nested:
                        return nested
        return ""

    @staticmethod
    def _priority_sort_key(item: Dict[str, Any]):
        return (-int(item.get("priority", 0)), str(item.get("label", "")), str(item.get("matchedText", "")))

    def _digest_max_items(self, override: Optional[int] = None) -> int:
        if override is not None:
            return int(override)
        return int(self.config.get("digest", {}).get("maxItems", 5))

    def _preview_length(self) -> int:
        return int(self.config.get("digest", {}).get("previewLength", 100))

    def _priority_rules(self) -> List[Dict[str, Any]]:
        rules = self.config.get("priorityRules", [])
        return rules if isinstance(rules, list) else []

    def _notification_routes(self) -> List[Dict[str, Any]]:
        routes = self.config.get("notificationRoutes", [])
        return routes if isinstance(routes, list) else []

    def _classify_text(self, text: str) -> List[Dict[str, Any]]:
        haystack = (text or "").lower()
        matches: List[Dict[str, Any]] = []
        for rule in self._priority_rules():
            keywords = rule.get("keywords", [])
            if not isinstance(keywords, list):
                continue
            hit_keywords = [kw for kw in keywords if isinstance(kw, str) and kw and kw.lower() in haystack]
            if hit_keywords:
                matches.append({
                    "id": rule.get("id", ""),
                    "label": rule.get("label", rule.get("id", "rule")),
                    "priority": int(rule.get("priority", 0)),
                    "keywords": hit_keywords,
                })
        matches.sort(key=self._priority_sort_key)
        return matches

    def _extract_reply_candidates(self, replies: Dict[str, Any], max_items: int) -> List[Dict[str, Any]]:
        items = replies.get("items", []) if isinstance(replies, dict) else []
        if not isinstance(items, list):
            return []
        out = []
        for item in items[:max_items * 3]:
            user = item.get("user", {}) if isinstance(item, dict) else {}
            payload = item.get("item", {}) if isinstance(item, dict) else {}
            text = self._extract_text(payload)
            matched = self._classify_text(text)
            out.append({
                "kind": "reply",
                "user": user.get("nickname") or user.get("uname") or "",
                "mid": user.get("mid"),
                "text": self._truncate(text, self._preview_length()),
                "rawText": text,
                "priorityMatches": matched,
                "topPriority": matched[0]["priority"] if matched else 0,
                "uri": payload.get("uri") or payload.get("native_uri") or "",
            })
        out.sort(key=lambda x: (-int(x.get("topPriority", 0)), x.get("user", ""), x.get("text", "")))
        return out[:max_items]

    def _extract_session_candidates(self, sessions: Dict[str, Any], max_items: int) -> List[Dict[str, Any]]:
        items = self._extract_sessions_list(sessions)
        out = []
        for item in items[:max_items * 4]:
            last_msg = item.get("last_msg", {}) if isinstance(item, dict) else {}
            raw_content = self._extract_text(last_msg)
            matched = self._classify_text(raw_content)
            out.append({
                "kind": "session",
                "talker_id": item.get("talker_id") or item.get("talkerId") or item.get("uid"),
                "name": item.get("session_name") or item.get("uname") or item.get("nick_name") or "",
                "unread": item.get("unread_count") or item.get("unread") or 0,
                "text": self._truncate(raw_content, self._preview_length()),
                "rawText": raw_content,
                "priorityMatches": matched,
                "topPriority": matched[0]["priority"] if matched else 0,
            })
        out.sort(key=lambda x: (-int(x.get("topPriority", 0)), -int(x.get("unread", 0)), str(x.get("talker_id", ""))))
        return out[:max_items]

    def _base_checks(self) -> Optional[Dict[str, Any]]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error
        return None

    async def unread(self) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_unread_messages(self._credential())
        return {"success": True, "result": data}

    async def replies(self, last_reply_id: int = None, reply_time: int = None) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_replies(
            self._credential(),
            last_reply_id=last_reply_id,
            reply_time=reply_time,
        )
        return {
            "success": True,
            "last_reply_id": last_reply_id,
            "reply_time": reply_time,
            "result": data,
        }

    async def at_me(self, last_uid: int = None, at_time: int = None, last_id: int = None) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_at(
            self._credential(),
            last_uid=last_uid,
            at_time=at_time,
            last_id=last_id,
        )
        return {
            "success": True,
            "last_uid": last_uid,
            "at_time": at_time,
            "last_id": last_id,
            "result": data,
        }

    async def likes(self, last_id: int = None, like_time: int = None) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_likes(
            self._credential(),
            last_id=last_id,
            like_time=like_time,
        )
        return {
            "success": True,
            "last_id": last_id,
            "like_time": like_time,
            "result": data,
        }

    async def system_messages(self) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_system_messages(self._credential())
        return {"success": True, "result": data}

    async def session_settings(self) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_session_settings(self._credential())
        return {"success": True, "result": data}

    async def sessions(self, session_type: int = 4) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_sessions(self._credential(), session_type=session_type)
        items = self._extract_sessions_list(data)
        return {
            "success": True,
            "session_type": session_type,
            "count": len(items),
            "result": data,
        }

    async def session_detail(self, talker_id: int, session_type: int = 1) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.get_session_detail(
            self._credential(),
            talker_id=int(talker_id),
            session_type=session_type,
        )
        return {
            "success": True,
            "talker_id": int(talker_id),
            "session_type": session_type,
            "result": data,
        }

    async def fetch_messages(
        self,
        talker_id: int,
        session_type: int = 1,
        begin_seqno: int = 0,
    ) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        data = await bili_session.fetch_session_msgs(
            talker_id=int(talker_id),
            credential=self._credential(),
            session_type=session_type,
            begin_seqno=begin_seqno,
        )
        messages = self._extract_messages_list(data)
        return {
            "success": True,
            "talker_id": int(talker_id),
            "session_type": session_type,
            "begin_seqno": begin_seqno,
            "count": len(messages),
            "result": data,
        }

    async def dm_history(
        self,
        talker_id: int,
        session_type: int = 1,
        begin_seqno: int = 0,
        include_detail: bool = True,
    ) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        detail = None
        if include_detail:
            detail = await bili_session.get_session_detail(
                self._credential(),
                talker_id=int(talker_id),
                session_type=session_type,
            )
        messages = await bili_session.fetch_session_msgs(
            talker_id=int(talker_id),
            credential=self._credential(),
            session_type=session_type,
            begin_seqno=begin_seqno,
        )
        message_list = self._extract_messages_list(messages)
        return {
            "success": True,
            "talker_id": int(talker_id),
            "session_type": session_type,
            "begin_seqno": begin_seqno,
            "count": len(message_list),
            "detail": detail,
            "messages": messages,
        }

    async def send_text(self, receiver_id: int, text: str) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        text = (text or "").strip()
        if not text:
            return {"success": False, "message": "text is required"}
        result = await bili_session.send_msg(
            credential=self._credential(),
            receiver_id=int(receiver_id),
            msg_type=bili_session.EventType.TEXT,
            content=text,
        )
        return {
            "success": True,
            "receiver_id": int(receiver_id),
            "text": text,
            "result": result,
        }

    async def new_sessions(self, begin_ts: int = None) -> Dict[str, Any]:
        error = self._base_checks()
        if error:
            return error
        if begin_ts is None:
            begin_ts = int(time.time() * 1000000)
        data = await bili_session.new_sessions(self._credential(), begin_ts=begin_ts)
        return {"success": True, "begin_ts": begin_ts, "result": data}

    async def inbox_summary(self) -> Dict[str, Any]:
        """Convenience entrypoint for scheduled polling jobs."""
        error = self._base_checks()
        if error:
            return error

        cred = self._credential()
        me = await bili_user.get_self_info(cred)
        unread = await bili_session.get_unread_messages(cred)
        replies = await bili_session.get_replies(cred)
        likes = await bili_session.get_likes(cred)
        at_me = await bili_session.get_at(cred)
        sessions = await bili_session.get_sessions(cred, session_type=4)

        session_items = self._extract_sessions_list(sessions)

        return {
            "success": True,
            "uid": me.get("mid"),
            "username": me.get("uname"),
            "counts": {
                "sessions": len(session_items),
                "replies": self._count_candidates(replies),
                "likes": self._count_candidates(likes),
                "at": self._count_candidates(at_me),
            },
            "unread": unread,
            "replies": replies,
            "likes": likes,
            "at": at_me,
            "sessions": sessions,
        }

    async def inbox_digest(self, max_items: int = None) -> Dict[str, Any]:
        """Compact creator-friendly digest for dashboards and cron jobs."""
        summary = await self.inbox_summary()
        if not summary.get("success"):
            return summary

        max_items = self._digest_max_items(max_items)
        session_items = self._extract_sessions_list(summary.get("sessions", {}))[:max_items]
        top_sessions = []
        for item in session_items:
            talker_id = item.get("talker_id") or item.get("talkerId") or item.get("uid")
            name = (
                item.get("talker_name")
                or item.get("talkerName")
                or item.get("uname")
                or self._extract_text(item.get("talker_info") or item.get("user") or {})
            )
            preview = self._extract_text(item)
            unread_count = item.get("unread_count") or item.get("unreadCount") or item.get("unread") or 0
            top_sessions.append(
                {
                    "talker_id": talker_id,
                    "name": name,
                    "unread": unread_count,
                    "preview": self._truncate(preview, self._preview_length()),
                }
            )

        lines = [
            f"B站消息中心：私信会话 {summary['counts']['sessions']}，回复 {summary['counts']['replies']}，@我 {summary['counts']['at']}，赞我 {summary['counts']['likes']}。"
        ]
        if top_sessions:
            lines.append("最近私信：")
            for item in top_sessions:
                label = item['name'] or item['talker_id'] or 'unknown'
                unread = f" unread={item['unread']}" if item['unread'] else ""
                lines.append(f"- {label}{unread}: {item['preview']}")

        return {
            "success": True,
            "counts": summary["counts"],
            "top_sessions": top_sessions,
            "text": "\n".join(lines),
            "summary": summary,
            "config": self.config.get("_meta", {}),
        }

    async def priority_digest(self, max_items: int = None) -> Dict[str, Any]:
        summary = await self.inbox_summary()
        if not summary.get("success"):
            return summary

        max_items = self._digest_max_items(max_items)
        reply_hits = self._extract_reply_candidates(summary.get("replies", {}), max_items)
        session_hits = self._extract_session_candidates(summary.get("sessions", {}), max_items)
        combined = sorted(reply_hits + session_hits, key=lambda x: (-int(x.get("topPriority", 0)), x.get("kind", "")))[:max_items]
        min_priority = int(self.config.get("automation", {}).get("minPriorityToNotify", 80))
        notify_candidates = [item for item in combined if int(item.get("topPriority", 0)) >= min_priority]

        lines = [f"高优先级消息候选 {len(notify_candidates)} 条（阈值 {min_priority}）。"]
        for item in combined:
            label = item.get("name") or item.get("user") or item.get("talker_id") or item.get("mid") or "unknown"
            tags = ", ".join(match.get("label", "") for match in item.get("priorityMatches", [])[:2])
            lines.append(f"- [{item.get('kind')}] p{item.get('topPriority',0)} {label}: {item.get('text','')} {('['+tags+']') if tags else ''}")

        return {
            "success": True,
            "threshold": min_priority,
            "items": combined,
            "notifyCandidates": notify_candidates,
            "text": "\n".join(lines),
            "routes": self._notification_routes(),
            "config": self.config,
        }

    async def automation_snapshot(self, max_items: int = None) -> Dict[str, Any]:
        """Config-driven snapshot for cron / notifier bridges."""
        digest = await self.inbox_digest(max_items=max_items)
        if not digest.get("success"):
            return digest
        priority = await self.priority_digest(max_items=max_items)
        return {
            "success": True,
            "digest": digest,
            "priority": priority,
            "routes": self._notification_routes(),
            "automation": self.config.get("automation", {}),
            "text": priority.get("text") or digest.get("text") or "",
        }

    async def show_config(self) -> Dict[str, Any]:
        return {"success": True, "config": self.config}

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "unread": self.unread,
            "replies": self.replies,
            "at_me": self.at_me,
            "likes": self.likes,
            "system_messages": self.system_messages,
            "session_settings": self.session_settings,
            "sessions": self.sessions,
            "session_detail": self.session_detail,
            "fetch_messages": self.fetch_messages,
            "dm_history": self.dm_history,
            "send_text": self.send_text,
            "new_sessions": self.new_sessions,
            "inbox_summary": self.inbox_summary,
            "inbox_digest": self.inbox_digest,
            "priority_digest": self.priority_digest,
            "automation_snapshot": self.automation_snapshot,
            "show_config": self.show_config,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "message": f"Unknown message_center action: {action}"}
        return await handler(**kwargs)
