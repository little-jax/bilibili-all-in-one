"""Higher-level client workflows built on the Bilibili client-kernel modules."""

from __future__ import annotations

from typing import Any, Dict, Optional, List

import re

from .auth import BilibiliAuth
from .entity_resolver import BilibiliEntityResolver
from .search_client import BilibiliSearchClient
from .user_intel import BilibiliUserIntel
from .message_center import BilibiliMessageCenter
from .creative_center_client import BilibiliCreativeCenterClient


class BilibiliClientWorkflows:
    """Composite workflows for investigation, reply preparation, and creator operations."""

    @staticmethod
    def _pick_list(data: Any) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "item", "results", "messages", "sessions", "cards", "list"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
            for value in data.values():
                found = BilibiliClientWorkflows._pick_list(value)
                if found:
                    return found
        return []

    @staticmethod
    def _snip(value: Any, limit: int = 240) -> str:
        text = "" if value is None else str(value)
        text = " ".join(text.split())
        return text[:limit]

    @staticmethod
    def _normalize_interaction_item(item: Dict[str, Any]) -> Dict[str, Any]:
        user = item.get("user") or item.get("sender") or {}
        target = item.get("item") or item.get("target") or {}
        return {
            "id": item.get("id") or item.get("reply_id") or item.get("mid"),
            "user": {
                "uid": user.get("mid") or user.get("uid"),
                "name": user.get("nickname") or user.get("uname") or user.get("name"),
            },
            "text": BilibiliClientWorkflows._snip(
                target.get("message")
                or target.get("source_content")
                or target.get("target_reply_content")
                or target.get("root_reply_content")
                or target.get("desc")
                or item.get("text")
            ),
            "url": target.get("uri") or target.get("url") or target.get("native_uri"),
            "title": target.get("title") or target.get("detail_title") or target.get("desc"),
            "source_content": BilibiliClientWorkflows._snip(target.get("source_content") or ""),
            "target_reply_content": BilibiliClientWorkflows._snip(target.get("target_reply_content") or ""),
            "root_reply_content": BilibiliClientWorkflows._snip(target.get("root_reply_content") or ""),
            "business": target.get("business"),
            "raw": item,
        }

    @staticmethod
    def _extract_urls(value: Any) -> list:
        text = "" if value is None else str(value)
        return re.findall(r"https?://[^\s\]\)>'\"]+", text)

    @staticmethod
    def _pick_first_nonempty(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return None

    @staticmethod
    def _to_number(value: Any) -> Optional[float]:
        try:
            if value in (None, "", [], {}):
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _risk_level(priority: Optional[float]) -> str:
        if priority is None:
            return "low"
        if priority >= 90:
            return "high"
        if priority >= 70:
            return "medium"
        return "low"

    def _normalize_priority_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "kind": item.get("kind"),
            "user": item.get("user") or item.get("name"),
            "text": self._snip(item.get("text") or item.get("rawText")),
            "priority": item.get("topPriority") or item.get("priority") or 0,
            "uri": item.get("uri") or item.get("url"),
            "raw": item,
        }

    async def _resolve_focus_entity(self, focus: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not focus:
            return None
        candidates = []
        if focus.get("url"):
            candidates.append(focus["url"])
        candidates.extend(self._extract_urls(focus.get("text")))
        candidates.extend(self._extract_urls(focus.get("source_content")))
        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            resolved = await self.entity_resolver.resolve(target=candidate)
            if resolved.get("success"):
                return resolved.get("entity")
        return None

    async def _creator_metrics_bundle(self, period: str = "week") -> Dict[str, Any]:
        creative = await self.creative_center.dashboard_snapshot(period=period)
        return {
            "success": creative.get("success", False),
            "period": period,
            "kpis": creative.get("kpis") or {},
            "modules": creative.get("modules") or {},
            "status": creative.get("status") or {},
            "message": creative.get("message"),
        }

    def _build_creator_profile(self, profile: Dict[str, Any], signals: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        kpis = metrics.get("kpis") or {}
        return {
            "uid": profile.get("uid"),
            "name": profile.get("name"),
            "sign": profile.get("sign"),
            "fans": self._pick_first_nonempty(profile.get("fans"), signals.get("fans"), kpis.get("fans")),
            "new_fans": kpis.get("new_fans"),
            "play": kpis.get("play"),
            "visitor": kpis.get("visitor"),
            "engagement": {
                "comment": kpis.get("comment"),
                "like": kpis.get("like"),
                "share": kpis.get("share"),
            },
        }

    def _build_audience_fit(self, inspected: Dict[str, Any], related_search_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        signals = inspected.get("signals") or {}
        recent_videos = inspected.get("recent_videos") or []
        recent_dynamics = inspected.get("recent_dynamics") or []
        return {
            "creator_activity_level": "high" if len(recent_videos) + len(recent_dynamics) >= 4 else "medium" if len(recent_videos) + len(recent_dynamics) >= 2 else "low",
            "likely_role": signals.get("likely_role") or ("creator" if recent_videos else "audience"),
            "recent_content_density": {
                "videos": len(recent_videos),
                "dynamics": len(recent_dynamics),
                "search_hits": len(related_search_hits),
            },
            "operator_hint": "engage-as-creator-peer" if recent_videos else "reply-as-audience-community",
        }

    def _build_investigation_brief(self, profile: Dict[str, Any], audience_fit: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        kpis = metrics.get("kpis") or {}
        lines = []
        if profile.get("name"):
            lines.append(f"对象：{profile.get('name')}")
        if audience_fit.get("likely_role"):
            lines.append(f"角色倾向：{audience_fit.get('likely_role')}")
        if kpis:
            lines.append(
                "创作指标：播放 {play} / 访客 {visitor} / 粉丝 {fans} / 新增粉 {new_fans}".format(
                    play=kpis.get("play"),
                    visitor=kpis.get("visitor"),
                    fans=kpis.get("fans"),
                    new_fans=kpis.get("new_fans"),
                )
            )
        return {
            "text": "；".join([x for x in lines if x]),
            "operator_hint": audience_fit.get("operator_hint"),
        }

    def _build_task(self, *, task_type: str, title: str, priority: int, reason: str, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": task_type,
            "title": title,
            "priority": priority,
            "risk": self._risk_level(priority),
            "reason": reason,
            "source": source,
            "payload": payload,
        }

    def _classify_interest(self, text: str = "", entity: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        lowered = (text or "").lower()
        entity_type = (entity or {}).get("type")
        rules = [
            ("cooperation", ["合作", "商务", "商单", "联动", "collab", "cooperate", "sponsor", "合作投稿"]),
            ("licensing", ["授权", "转载", "搬运", "许可", "license", "licensing", "reprint"]),
            ("support", ["怎么", "如何", "请问", "问题", "帮忙", "教程", "bug", "报错", "help"]),
            ("fan_praise", ["喜欢", "支持", "太强", "牛", "厉害", "好看", "爱了", "awesome", "great"]),
            ("troll_or_low_value", ["傻", "垃圾", "引流", "骗子", "滚", "弱智", "傻逼", "sb"]),
        ]
        interest = "general"
        for label, keywords in rules:
            if any(k in lowered for k in keywords):
                interest = label
                break
        urgency = "normal"
        if interest in {"cooperation", "licensing"}:
            urgency = "high"
        elif interest == "support":
            urgency = "medium"
        elif interest == "troll_or_low_value":
            urgency = "low"
        tone = {
            "cooperation": "professional-warm",
            "licensing": "careful-professional",
            "support": "helpful-clear",
            "fan_praise": "warm-brief",
            "troll_or_low_value": "do-not-escalate",
            "general": "neutral-clear",
        }[interest]
        review_required = interest in {"cooperation", "licensing"}
        if entity_type in {"article", "note", "opus"} and interest in {"licensing", "cooperation"}:
            review_required = True
        canned_refs = []
        if interest == "cooperation":
            canned_refs = ["ask-for-scope", "ask-for-budget-or-goal", "move-to-private-channel-if-needed"]
        elif interest == "licensing":
            canned_refs = ["confirm-original-source", "state-reuse-policy", "request-specific-usage-details"]
        elif interest == "support":
            canned_refs = ["clarify-problem", "ask-for-link-or-screenshot", "offer-step-by-step-help"]
        elif interest == "fan_praise":
            canned_refs = ["thank-briefly", "optionally-point-to-related-work"]
        elif interest == "troll_or_low_value":
            canned_refs = ["avoid-argument", "deprioritize-or-ignore"]
        return {
            "interest": interest,
            "urgency": urgency,
            "tone": tone,
            "review_required": review_required,
            "canned_refs": canned_refs,
        }

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        self.auth = auth or BilibiliAuth()
        self.search_client = BilibiliSearchClient(auth=self.auth)
        self.user_intel = BilibiliUserIntel(auth=self.auth)
        self.entity_resolver = BilibiliEntityResolver(auth=self.auth)
        self.message_center = BilibiliMessageCenter(auth=self.auth)
        self.creative_center = BilibiliCreativeCenterClient(auth=self.auth)

    async def content_object_lookup(self, target: str) -> Dict[str, Any]:
        resolved = await self.entity_resolver.resolve(target=target)
        if not resolved.get("success"):
            return resolved

        entity = resolved.get("entity") or {}
        entity_type = entity.get("type")
        result = {
            "success": True,
            "target": target,
            "entity": entity,
            "lookup": {},
        }

        if entity_type == "video" and entity.get("bvid"):
            search = await self.search_client.search_by_type(
                keyword=entity.get("title") or entity.get("bvid"),
                search_type="video",
                page_size=5,
            )
            result["lookup"] = {
                "discoverability": (search.get("items") or [])[:5],
                "search_status": search.get("success", False),
            }
        elif entity_type == "user" and entity.get("uid"):
            profile = await self.user_intel.get_user_profile(uid=entity["uid"])
            result["lookup"] = {
                "profile": profile.get("profile"),
            }
        elif entity_type in {"dynamic", "opus", "note", "article"}:
            author_uid = ((entity.get("author") or {}).get("uid")) or entity.get("uid")
            author_profile = None
            if author_uid:
                intel = await self.user_intel.get_user_profile(uid=int(author_uid))
                author_profile = intel.get("profile") if intel.get("success") else None
            result["lookup"] = {
                "author_profile": author_profile,
                "content_brief": {
                    "title": entity.get("title"),
                    "summary": entity.get("summary") or entity.get("text"),
                    "url": entity.get("url"),
                },
            }

        return result

    async def investigate_user(
        self,
        uid: Optional[int] = None,
        name: Optional[str] = None,
        keyword: Optional[str] = None,
        include_creator_metrics: bool = True,
        period: str = "week",
    ) -> Dict[str, Any]:
        inspected = await self.user_intel.inspect_user(uid=uid, name=name)
        if not inspected.get("success"):
            return inspected

        profile = inspected.get("profile") or {}
        query = keyword or profile.get("name")
        search_hits = None
        if query:
            search_hits = await self.search_client.search_by_type(
                keyword=query,
                search_type="video",
                page_size=5,
            )

        creator_metrics = {
            "success": False,
            "period": period,
            "kpis": {},
            "modules": {},
            "status": {},
        }
        if include_creator_metrics:
            creator_metrics = await self._creator_metrics_bundle(period=period)

        related_search_hits = (search_hits or {}).get("items") or []
        audience_fit = self._build_audience_fit(inspected, related_search_hits)
        creator_profile = self._build_creator_profile(profile, inspected.get("signals") or {}, creator_metrics)
        brief = self._build_investigation_brief(profile, audience_fit, creator_metrics)

        return {
            "success": True,
            "schema": "bilibili.client_workflows.investigate_user.v1",
            "profile": profile,
            "recent_videos": inspected.get("recent_videos") or [],
            "recent_dynamics": inspected.get("recent_dynamics") or [],
            "signals": inspected.get("signals") or {},
            "related_search_hits": related_search_hits,
            "search_status": (search_hits or {}).get("success"),
            "creator_profile": creator_profile,
            "creator_metrics": creator_metrics,
            "audience_fit": audience_fit,
            "brief": brief,
            "status": {
                "intel": inspected.get("success", False),
                "search": (search_hits or {}).get("success", False) if search_hits is not None else None,
                "creator_metrics": creator_metrics.get("success", False) if include_creator_metrics else None,
            },
        }

    async def prepare_reply_context(
        self,
        target: Optional[str] = None,
        uid: Optional[int] = None,
        receiver_id: Optional[int] = None,
        source: str = "dm",
        limit: int = 10,
    ) -> Dict[str, Any]:
        entity = None
        if target:
            resolved = await self.entity_resolver.resolve(target=target)
            if resolved.get("success"):
                entity = resolved.get("entity")

        interaction_context = None
        interaction_user_uid = None
        normalized_source = (source or "dm").strip().lower()

        if normalized_source == "dm" and receiver_id is not None:
            history = await self.message_center.dm_history(talker_id=int(receiver_id))
            if history.get("success"):
                items = self._pick_list(history.get("result") or history)
                interaction_context = {
                    "kind": "dm",
                    "receiver_id": int(receiver_id),
                    "history": items[:limit],
                }
                interaction_user_uid = int(receiver_id)

        elif normalized_source == "reply":
            replies = await self.message_center.replies()
            if replies.get("success"):
                items = [self._normalize_interaction_item(x) for x in self._pick_list(replies.get("result") or replies)]
                interaction_context = {
                    "kind": "reply",
                    "items": items[:limit],
                    "focus": items[0] if items else None,
                }
                interaction_user_uid = (((interaction_context.get("focus") or {}).get("user") or {}).get("uid"))

        elif normalized_source in {"at", "mention"}:
            mentions = await self.message_center.at_me()
            if mentions.get("success"):
                items = [self._normalize_interaction_item(x) for x in self._pick_list(mentions.get("result") or mentions)]
                interaction_context = {
                    "kind": "mention",
                    "items": items[:limit],
                    "focus": items[0] if items else None,
                }
                interaction_user_uid = (((interaction_context.get("focus") or {}).get("user") or {}).get("uid"))

        focus_entity = await self._resolve_focus_entity((interaction_context or {}).get("focus"))
        if focus_entity and not entity:
            entity = focus_entity

        user_context = None
        intel_status = None
        resolved_uid = uid or interaction_user_uid or (entity or {}).get("uid") or (((entity or {}).get("author") or {}).get("uid"))
        if resolved_uid:
            intel = await self.user_intel.inspect_user(uid=int(resolved_uid), video_limit=3, dynamics_limit=3)
            intel_status = {
                "success": intel.get("success", False),
                "message": intel.get("message"),
                "partial_failures": intel.get("partial_failures"),
            }
            if intel.get("success"):
                user_context = {
                    "profile": intel.get("profile"),
                    "signals": intel.get("signals"),
                    "recent_videos": intel.get("recent_videos"),
                    "recent_dynamics": intel.get("recent_dynamics"),
                    "partial_failures": intel.get("partial_failures"),
                }

        focus = (interaction_context or {}).get("focus") or {}
        reply_targets = {
            "entity_url": (entity or {}).get("url"),
            "entity_title": (entity or {}).get("title"),
            "source_kind": normalized_source,
            "focus_text": self._snip(focus.get("text")),
            "focus_user_name": ((focus.get("user") or {}).get("name")),
            "business": focus.get("business"),
        }

        thread_context = {
            "focus": {
                "text": self._snip(focus.get("text")),
                "source_content": self._snip(focus.get("source_content")),
                "target_reply_content": self._snip(focus.get("target_reply_content")),
                "root_reply_content": self._snip(focus.get("root_reply_content")),
                "title": focus.get("title"),
                "url": focus.get("url"),
            },
            "resolved_entity": {
                "type": (entity or {}).get("type"),
                "title": (entity or {}).get("title"),
                "summary": self._snip((entity or {}).get("summary") or (entity or {}).get("text")),
                "url": (entity or {}).get("url"),
            },
        }

        reply_guidance = {
            "reply_to": reply_targets["focus_user_name"] or ((user_context or {}).get("profile") or {}).get("name"),
            "context_summary": self._snip(
                focus.get("target_reply_content")
                or focus.get("root_reply_content")
                or reply_targets["focus_text"]
                or ((entity or {}).get("summary"))
                or ((entity or {}).get("text"))
                or ((entity or {}).get("title"))
            ),
            "recommended_tone": "helpful-creator",
            "suggested_next_step": "answer-or-clarify",
            "thread_strategy": "reply-to-latest-with-parent-awareness" if normalized_source in {"reply", "at", "mention"} else "direct-dm-response",
        }

        candidate_reply_input = {
            "who_to_reply": reply_guidance["reply_to"],
            "what_they_said": self._snip(focus.get("text") or focus.get("source_content")),
            "what_object_this_is_about": {
                "type": (entity or {}).get("type"),
                "title": (entity or {}).get("title"),
                "url": (entity or {}).get("url"),
            },
            "parent_context": {
                "target_reply_content": self._snip(focus.get("target_reply_content")),
                "root_reply_content": self._snip(focus.get("root_reply_content")),
                "source_content": self._snip(focus.get("source_content")),
            },
            "suggested_style": {
                "tone": reply_guidance["recommended_tone"],
                "strategy": reply_guidance["thread_strategy"],
                "next_step": reply_guidance["suggested_next_step"],
            },
        }

        interest_profile = self._classify_interest(
            text=self._pick_first_nonempty(focus.get("text"), focus.get("source_content"), focus.get("target_reply_content"), ""),
            entity=entity,
        )

        return {
            "success": True,
            "schema": "bilibili.client_workflows.prepare_reply_context.v1",
            "entity": entity,
            "user_context": user_context,
            "interaction_context": interaction_context,
            "thread_context": thread_context,
            "reply_targets": reply_targets,
            "reply_guidance": reply_guidance,
            "candidate_reply_input": candidate_reply_input,
            "interest_profile": interest_profile,
            "status": {
                "intel": intel_status,
                "entity_resolved": bool(entity),
            },
            "reply_brief": {
                "target_type": (entity or {}).get("type"),
                "user_name": ((user_context or {}).get("profile") or {}).get("name"),
                "source_kind": normalized_source,
                "has_context_history": bool(interaction_context),
                "risk": "medium" if interaction_context else "low",
            },
        }

    async def creator_dashboard_snapshot(self, period: str = "week", max_items: int = 5) -> Dict[str, Any]:
        inbox = await self.message_center.inbox_digest(max_items=max_items)
        priority = await self.message_center.priority_digest(max_items=max_items)
        creative = await self.creative_center.dashboard_snapshot(period=period)

        counts = (inbox.get("counts") or {}) if inbox.get("success") else {}
        top_sessions = (inbox.get("top_sessions") or [])[:max_items] if inbox.get("success") else []
        raw_priority_items = (priority.get("notifyCandidates") or priority.get("items") or [])[:max_items] if priority.get("success") else []
        priority_items = [self._normalize_priority_item(x) for x in raw_priority_items]
        creative_kpis = creative.get("kpis") if creative.get("success") else {}

        summary_lines = []
        if counts:
            summary_lines.append(
                f"消息：私信 {counts.get('sessions', 0)} / 回复 {counts.get('replies', 0)} / @我 {counts.get('at', 0)} / 赞我 {counts.get('likes', 0)}"
            )
        if creative_kpis:
            summary_lines.append(
                "创作：播放 {play} / 访客 {visitor} / 粉丝 {fans} / 新增粉 {new_fans}".format(
                    play=creative_kpis.get("play"),
                    visitor=creative_kpis.get("visitor"),
                    fans=creative_kpis.get("fans"),
                    new_fans=creative_kpis.get("new_fans"),
                )
            )
        if priority_items:
            first = priority_items[0]
            label = first.get("user") or "unknown"
            summary_lines.append(f"最高优先级：p{first.get('priority', 0)} {label} - {self._snip(first.get('text'))}")

        return {
            "success": True,
            "schema": "bilibili.client_workflows.creator_dashboard_snapshot.v1",
            "period": period,
            "dashboard": {
                "inbox": {
                    "counts": counts,
                    "top_sessions": top_sessions,
                    "status": inbox.get("success", False),
                },
                "priority": {
                    "items": priority_items,
                    "threshold": priority.get("threshold"),
                    "status": priority.get("success", False),
                },
                "creative_center": {
                    "kpis": creative_kpis,
                    "status": creative.get("success", False),
                    "modules": creative.get("modules") if creative.get("success") else None,
                },
            },
            "status": {
                "inbox": inbox.get("success", False),
                "priority": priority.get("success", False),
                "creative_center": creative.get("success", False),
            },
            "text": "\n".join(summary_lines),
        }

    async def creator_task_queue(self, period: str = "week", max_items: int = 5) -> Dict[str, Any]:
        dashboard = await self.creator_dashboard_snapshot(period=period, max_items=max_items)
        if not dashboard.get("success"):
            return dashboard

        priority_items = (((dashboard.get("dashboard") or {}).get("priority") or {}).get("items") or [])[:max_items]
        kpis = (((dashboard.get("dashboard") or {}).get("creative_center") or {}).get("kpis") or {})
        tasks = []

        for item in priority_items:
            priority = int(item.get("priority") or 0)
            tasks.append(self._build_task(
                task_type="reply_queue",
                title=f"回复 {item.get('user') or 'unknown'}",
                priority=priority,
                reason=self._snip(item.get("text")) or "high-priority inbound item",
                source="message_center.priority_digest",
                payload={
                    "user": item.get("user"),
                    "text": item.get("text"),
                    "uri": item.get("uri"),
                    "kind": item.get("kind"),
                },
            ))

        play = self._to_number(kpis.get("play"))
        new_fans = self._to_number(kpis.get("new_fans"))
        visitor = self._to_number(kpis.get("visitor"))

        if play is not None and play < 100:
            tasks.append(self._build_task(
                task_type="content_review",
                title="复盘近期内容表现",
                priority=72,
                reason=f"当前周期播放偏低：{play}",
                source="creative_center.dashboard_snapshot",
                payload={"kpis": kpis, "period": period},
            ))
        if new_fans is not None and new_fans <= 0:
            tasks.append(self._build_task(
                task_type="growth_review",
                title="检查涨粉停滞",
                priority=74,
                reason=f"当前周期新增粉偏弱：{new_fans}",
                source="creative_center.dashboard_snapshot",
                payload={"kpis": kpis, "period": period},
            ))
        if visitor is not None and play is not None and visitor > 0 and play / visitor < 1.2:
            tasks.append(self._build_task(
                task_type="conversion_review",
                title="检查访客到播放转化",
                priority=68,
                reason=f"访客/播放转化一般：visitor={visitor}, play={play}",
                source="creative_center.dashboard_snapshot",
                payload={"kpis": kpis, "period": period},
            ))

        tasks = sorted(tasks, key=lambda x: x.get("priority", 0), reverse=True)[:max_items]
        return {
            "success": True,
            "schema": "bilibili.client_workflows.creator_task_queue.v1",
            "period": period,
            "tasks": tasks,
            "summary": {
                "count": len(tasks),
                "highest_priority": tasks[0].get("priority") if tasks else None,
            },
            "text": "\n".join(f"- p{t['priority']} {t['title']}: {t['reason']}" for t in tasks),
        }

    async def recommend_reply_targets(self, max_items: int = 5) -> Dict[str, Any]:
        priority = await self.message_center.priority_digest(max_items=max_items)
        if not priority.get("success"):
            return priority

        items = [self._normalize_priority_item(x) for x in (priority.get("notifyCandidates") or priority.get("items") or [])[:max_items]]
        recommendations = []
        for item in items:
            priority_score = int(item.get("priority") or 0)
            recommendations.append({
                "target": item.get("user"),
                "priority": priority_score,
                "why_now": self._snip(item.get("text")) or "priority-labeled inbound item",
                "reply_strategy": "reply-fast-with-context" if priority_score >= 85 else "reply-when-convenient-with-clarity",
                "uri": item.get("uri"),
                "kind": item.get("kind"),
            })

        return {
            "success": True,
            "schema": "bilibili.client_workflows.recommend_reply_targets.v1",
            "recommendations": recommendations,
            "summary": {
                "count": len(recommendations),
                "top_target": recommendations[0].get("target") if recommendations else None,
            },
            "text": "\n".join(f"- p{x['priority']} {x['target']}: {x['why_now']}" for x in recommendations),
        }

    async def content_opportunity_brief(self, period: str = "week", max_items: int = 5) -> Dict[str, Any]:
        creative = await self.creative_center.dashboard_snapshot(period=period)
        if not creative.get("success"):
            return creative

        modules = creative.get("modules") or {}
        candidates = []
        for bucket_name in ("video_survey", "video_playanalysis"):
            bucket = modules.get(bucket_name)
            for item in self._pick_list(bucket)[:max_items]:
                title = self._pick_first_nonempty(item.get("title"), item.get("name"), item.get("bvid"), item.get("aid"))
                score = self._pick_first_nonempty(item.get("play"), item.get("view"), item.get("rate"), item.get("value"))
                if title in (None, ""):
                    continue
                candidates.append({
                    "source": bucket_name,
                    "title": title,
                    "score": score,
                    "raw": item,
                })

        opportunities = []
        for item in candidates[:max_items]:
            opportunities.append({
                "title": item.get("title"),
                "source": item.get("source"),
                "signal": item.get("score"),
                "suggested_action": "amplify-or-review",
                "reason": f"creative-center {item.get('source')} surfaced this content",
            })

        return {
            "success": True,
            "schema": "bilibili.client_workflows.content_opportunity_brief.v1",
            "period": period,
            "opportunities": opportunities,
            "summary": {
                "count": len(opportunities),
                "sources": sorted({x.get("source") for x in opportunities if x.get("source")}),
            },
            "text": "\n".join(f"- {x['title']} ({x['source']}): {x['reason']}" for x in opportunities),
        }


    async def classify_inbound_intent(
        self,
        text: str = "",
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        entity = None
        if target:
            resolved = await self.entity_resolver.resolve(target=target)
            if resolved.get("success"):
                entity = resolved.get("entity")
        profile = self._classify_interest(text=text, entity=entity)
        return {
            "success": True,
            "schema": "bilibili.client_workflows.classify_inbound_intent.v1",
            "text": text,
            "entity": entity,
            "classification": profile,
        }

    async def operator_triage(
        self,
        text: str = "",
        target: Optional[str] = None,
        source: str = "reply",
        receiver_id: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        context = await self.prepare_reply_context(target=target, source=source, receiver_id=receiver_id, limit=limit)
        if not context.get("success"):
            return context
        interest_profile = context.get("interest_profile") or self._classify_interest(text=text, entity=context.get("entity"))
        guidance = context.get("reply_guidance") or {}
        candidate = context.get("candidate_reply_input") or {}
        triage = {
            "interest": interest_profile.get("interest"),
            "urgency": interest_profile.get("urgency"),
            "tone": interest_profile.get("tone"),
            "review_required": interest_profile.get("review_required"),
            "canned_refs": interest_profile.get("canned_refs") or [],
            "reply_strategy": guidance.get("thread_strategy"),
            "next_step": guidance.get("suggested_next_step"),
        }
        return {
            "success": True,
            "schema": "bilibili.client_workflows.operator_triage.v1",
            "triage": triage,
            "reply_guidance": guidance,
            "candidate_reply_input": candidate,
            "context": {
                "entity": context.get("entity"),
                "reply_targets": context.get("reply_targets"),
                "reply_brief": context.get("reply_brief"),
            },
        }

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "content_object_lookup": self.content_object_lookup,
            "investigate_user": self.investigate_user,
            "prepare_reply_context": self.prepare_reply_context,
            "classify_inbound_intent": self.classify_inbound_intent,
            "operator_triage": self.operator_triage,
            "creator_dashboard_snapshot": self.creator_dashboard_snapshot,
            "operator_dashboard_snapshot": self.creator_dashboard_snapshot,
            "creator_task_queue": self.creator_task_queue,
            "operator_task_queue": self.creator_task_queue,
            "recommend_reply_targets": self.recommend_reply_targets,
            "content_opportunity_brief": self.content_opportunity_brief,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "message": f"Unknown client_workflows action: {action}"}
        return await handler(**kwargs)
