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
from .content_client import BilibiliContentClient
from .discovery_client import BilibiliDiscoveryClient
from .operations import BilibiliOperations


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
            "native_uri": target.get("native_uri"),
            "title": target.get("title") or target.get("detail_title") or target.get("desc"),
            "source_content": BilibiliClientWorkflows._snip(target.get("source_content") or ""),
            "target_reply_content": BilibiliClientWorkflows._snip(target.get("target_reply_content") or ""),
            "root_reply_content": BilibiliClientWorkflows._snip(target.get("root_reply_content") or ""),
            "business": target.get("business"),
            "business_id": target.get("business_id"),
            "type": target.get("type"),
            "subject_id": target.get("subject_id"),
            "root_id": target.get("root_id"),
            "source_id": target.get("source_id"),
            "target_id": target.get("target_id"),
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

    async def _enrich_entity_context(self, entity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not entity:
            return {"success": False, "message": "No entity available."}

        entity_type = entity.get("type")
        try:
            if entity_type == "dynamic" and entity.get("dynamic_id"):
                return await self.content_client.get_dynamic_detail(dynamic_id=int(entity["dynamic_id"]))
            if entity_type == "opus" and entity.get("opus_id"):
                return await self.content_client.get_opus_detail(opus_id=int(entity["opus_id"]))
            if entity_type == "note" and entity.get("note_id"):
                return await self.content_client.get_note_detail(note_id=int(entity["note_id"]))
            if entity_type == "article" and entity.get("cvid"):
                return await self.content_client.get_article_detail(cvid=int(entity["cvid"]))
        except Exception as exc:
            return {"success": False, "message": f"Failed to enrich entity context: {exc}"}

        return {"success": False, "message": f"No content-client enrichment path for entity type: {entity_type}"}

    def _choose_operator_decision(self, *, interest_profile: Dict[str, Any], context: Dict[str, Any], entity_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        focus = (((context or {}).get("interaction_context") or {}).get("focus") or {})
        external_text = (context or {}).get("external_text")
        has_focus_text = bool(self._pick_first_nonempty(focus.get("text"), focus.get("source_content"), focus.get("target_reply_content"), external_text))
        review_required = bool((interest_profile or {}).get("review_required"))
        interest = (interest_profile or {}).get("interest") or "general"
        urgency = (interest_profile or {}).get("urgency") or "normal"
        entity_type = (((context or {}).get("entity") or {}).get("type"))
        entity_ready = bool(entity_context and entity_context.get("success"))

        if interest == "troll_or_low_value":
            action = "deprioritize"
            should_reply = False
            reason = "Low-value or adversarial inbound signal."
            confidence = 0.9
        elif review_required:
            action = "review_before_reply"
            should_reply = True
            reason = "Commercial/licensing-style inbound needs operator review before sending anything."
            confidence = 0.88
        elif has_focus_text and entity_type in {"dynamic", "opus", "note", "article", "video"}:
            action = "reply_now"
            should_reply = True
            reason = "Thread context is concrete enough to draft a direct reply."
            confidence = 0.84 if entity_ready else 0.74
        elif has_focus_text:
            action = "reply_with_clarification"
            should_reply = True
            reason = "Inbound is real, but object context is still thin; ask one clarifying question."
            confidence = 0.72
        else:
            action = "wait_for_more_context"
            should_reply = False
            reason = "Not enough thread detail to make a clean operator decision."
            confidence = 0.62

        return {
            "action": action,
            "should_reply": should_reply,
            "review_required": review_required,
            "confidence": confidence,
            "reason": reason,
            "urgency": urgency,
            "risk": "high" if review_required else ("medium" if should_reply else "low"),
        }

    def _build_reply_operator_brief(self, *, context: Dict[str, Any], interest_profile: Dict[str, Any], decision: Dict[str, Any], entity_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        guidance = (context or {}).get("reply_guidance") or {}
        candidate = (context or {}).get("candidate_reply_input") or {}
        entity = (context or {}).get("entity") or {}
        enriched_item = (entity_context or {}).get("item") if isinstance(entity_context, dict) else None
        object_summary = self._snip(
            ((enriched_item or {}).get("summary"))
            or ((enriched_item or {}).get("text"))
            or (entity.get("summary"))
            or (entity.get("text"))
            or (entity.get("title"))
        )
        checklist = []
        if decision.get("review_required"):
            checklist.extend(["confirm business intent", "confirm scope/usage", "avoid instant commitment"])
        elif decision.get("should_reply"):
            checklist.extend(["answer the core point", "stay brief", "keep parent-thread awareness"])
        else:
            checklist.append("do not spend operator attention unless signal changes")

        return {
            "who": candidate.get("who_to_reply"),
            "why": decision.get("reason"),
            "object": {
                "type": entity.get("type"),
                "title": entity.get("title") or (enriched_item or {}).get("title"),
                "url": entity.get("url") or (enriched_item or {}).get("url"),
                "summary": object_summary,
            },
            "style": candidate.get("suggested_style") or {
                "tone": interest_profile.get("tone"),
                "strategy": guidance.get("thread_strategy"),
                "next_step": guidance.get("suggested_next_step"),
            },
            "checklist": checklist,
            "draft_frame": {
                "opening": "直接回应对方核心点。",
                "body": "如果能直接答就直接答；不够信息就只问一个澄清问题。",
                "close": "必要时给下一步，不装，不绕。",
            },
        }

    def _compose_reply_text(self, *, context: Dict[str, Any], decision: Dict[str, Any], interest_profile: Dict[str, Any], operator_brief: Dict[str, Any]) -> str:
        candidate = (context or {}).get("candidate_reply_input") or {}
        what_they_said = self._snip(candidate.get("what_they_said") or (context or {}).get("external_text") or "")
        context_summary = self._snip(((context or {}).get("reply_guidance") or {}).get("context_summary") or "")
        who = operator_brief.get("who") or "你"
        interest = (interest_profile or {}).get("interest") or "general"
        action = (decision or {}).get("action") or "wait_for_more_context"

        object_info = (operator_brief or {}).get("object") or {}
        object_title = object_info.get("title") or object_info.get("type") or "这个内容"

        if action == "review_before_reply":
            if interest == "licensing":
                return f"{who}，收到。你先把转载/授权用途、投放范围和是否商用说清，我再按这个给你明确回复。"
            return f"{who}，收到。先把合作形式、目标、预算和时间点发我，我看完直接给你明确答复。"
        if action == "reply_with_clarification":
            return f"{who}，我看到了。你这边最想解决的具体点是哪一个？方便的话直接带上链接、截图或者目标内容，我好一次说准。"
        if interest == "fan_praise":
            return f"{who}，谢了，真收到。{object_title} 这块我后面还会继续往上打磨。"
        if interest == "support":
            return f"{who}，我先直接帮你看。你说的是“{what_they_said or context_summary or object_title}”，要是方便就再补一个链接、截图或者复现步骤，我给你更准的处理法。"
        if interest == "cooperation":
            return f"{who}，可以。你把合作形式、预期目标、预算和时间点发我，我按这个直接往下对。"
        if interest == "licensing":
            return f"{who}，可以先聊。你把用途、范围、是否商用，还有想用到 {object_title} 的哪一部分说清，我再给你明确口径。"
        if action == "reply_now":
            base = what_they_said or context_summary or object_title
            return f"{who}，收到。关于“{base}”，我这边先给直接结论：优先按最省事也最稳的方案来；你要更细，我可以继续往下拆。"
        if action == "wait_for_more_context" and (context or {}).get("external_text"):
            return f"{who}，收到。你把具体对象或链接补一下，我直接按那个给你答。"
        return ""

    def _build_send_plan(self, *, context: Dict[str, Any], draft_text: str, force_public_send: bool = False) -> Dict[str, Any]:
        interaction = (context or {}).get("interaction_context") or {}
        source_kind = interaction.get("kind") or (((context or {}).get("reply_targets") or {}).get("source_kind") or "unknown")
        entity = (context or {}).get("entity") or {}
        focus = (interaction.get("focus") or {})

        if source_kind == "dm" and interaction.get("receiver_id"):
            return {
                "mode": "direct_send",
                "channel": "dm",
                "receiver_id": interaction.get("receiver_id"),
                "text": draft_text,
                "supported": True,
            }

        public_target = self._resolve_public_reply_target(context=context)
        if force_public_send and public_target.get("supported"):
            return {
                "mode": "public_comment_send",
                "channel": source_kind,
                "text": draft_text,
                "supported": True,
                **public_target,
            }

        queue_reason = public_target.get("reason") if public_target else "Public reply auto-send is intentionally conservative until thread target mapping is proven reliable."
        return {
            "mode": "queue_only",
            "channel": source_kind,
            "supported": False,
            "reason": queue_reason,
            "text": draft_text,
            "public_target": public_target,
            "entity_type": entity.get("type"),
            "focus_id": focus.get("id"),
        }

    @staticmethod
    def _extract_first_match(pattern: str, value: Any) -> Optional[str]:
        text = "" if value is None else str(value)
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _resolve_public_reply_target(self, *, context: Dict[str, Any]) -> Dict[str, Any]:
        interaction = (context or {}).get("interaction_context") or {}
        focus = (interaction.get("focus") or {})
        entity = (context or {}).get("entity") or {}
        source_kind = interaction.get("kind") or (((context or {}).get("reply_targets") or {}).get("source_kind") or "unknown")
        if source_kind not in {"reply", "mention", "at"}:
            return {"supported": False, "reason": f"Unsupported public source kind: {source_kind}"}

        source_id = focus.get("source_id")
        root_id = focus.get("root_id")
        target_id = focus.get("target_id")
        native_uri = focus.get("native_uri") or ""
        url = focus.get("url") or ""
        business_id = focus.get("business_id")
        focus_type = (focus.get("type") or "").lower()
        entity_type = (entity.get("type") or "").lower()

        root = int(root_id) if root_id not in (None, 0, "0", "") else int(source_id) if source_id not in (None, 0, "0", "") else None
        parent = int(source_id) if source_id not in (None, 0, "0", "") else None

        bvid = self._extract_first_match(r"(BV[0-9A-Za-z]+)", url)
        if entity_type == "video" and bvid and root:
            return {
                "supported": True,
                "resource_type": "video",
                "resource_id": bvid,
                "resource_id_type": "bvid",
                "root": root,
                "parent": parent or root,
                "reason": "Resolved video comment thread from reply metadata.",
            }

        opus_id = self._extract_first_match(r"/opus/(\d+)", url) or self._extract_first_match(r"opus/detail/(\d+)", native_uri)
        if opus_id and root:
            resource_type = "dynamic_draw" if str(business_id) == "11" or focus_type == "album" else "dynamic"
            return {
                "supported": True,
                "resource_type": resource_type,
                "resource_id": int(opus_id),
                "resource_id_type": "oid",
                "root": root,
                "parent": parent or root,
                "reason": "Resolved opus/dynamic thread from reply metadata.",
            }

        article_id = self._extract_first_match(r"/read/cv(\d+)", url) or self._extract_first_match(r"read/(\d+)", native_uri)
        if article_id and root:
            return {
                "supported": True,
                "resource_type": "article",
                "resource_id": int(article_id),
                "resource_id_type": "oid",
                "root": root,
                "parent": parent or root,
                "reason": "Resolved article comment thread from reply metadata.",
            }

        if target_id not in (None, 0, "0", "") and root is not None:
            return {
                "supported": False,
                "reason": "Nested public reply target still lacks a proven parent/root mapping for this object type.",
                "root": root,
                "parent": parent,
                "target_id": int(target_id),
            }

        return {
            "supported": False,
            "reason": f"Could not derive a public comment target from entity={entity_type or 'unknown'} focus_type={focus_type or 'unknown'}.",
            "root": root,
            "parent": parent,
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
        self.content_client = BilibiliContentClient(auth=self.auth)
        self.discovery_client = BilibiliDiscoveryClient(auth=self.auth)
        self.operations = BilibiliOperations(auth=self.auth)

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

        interaction_status = None
        if normalized_source == "dm" and receiver_id is not None:
            try:
                history = await self.message_center.dm_history(talker_id=int(receiver_id))
                if history.get("success"):
                    items = self._pick_list(history.get("result") or history)
                    interaction_context = {
                        "kind": "dm",
                        "receiver_id": int(receiver_id),
                        "history": items[:limit],
                    }
                    interaction_user_uid = int(receiver_id)
                interaction_status = {"success": history.get("success", False), "message": history.get("message")}
            except Exception as exc:
                interaction_status = {"success": False, "message": f"DM history lookup failed: {exc}"}

        elif normalized_source == "reply":
            try:
                replies = await self.message_center.replies()
                if replies.get("success"):
                    items = [self._normalize_interaction_item(x) for x in self._pick_list(replies.get("result") or replies)]
                    interaction_context = {
                        "kind": "reply",
                        "items": items[:limit],
                        "focus": items[0] if items else None,
                    }
                    interaction_user_uid = (((interaction_context.get("focus") or {}).get("user") or {}).get("uid"))
                interaction_status = {"success": replies.get("success", False), "message": replies.get("message")}
            except Exception as exc:
                interaction_status = {"success": False, "message": f"Reply lookup failed: {exc}"}

        elif normalized_source in {"at", "mention"}:
            try:
                mentions = await self.message_center.at_me()
                if mentions.get("success"):
                    items = [self._normalize_interaction_item(x) for x in self._pick_list(mentions.get("result") or mentions)]
                    interaction_context = {
                        "kind": "mention",
                        "items": items[:limit],
                        "focus": items[0] if items else None,
                    }
                    interaction_user_uid = (((interaction_context.get("focus") or {}).get("user") or {}).get("uid"))
                interaction_status = {"success": mentions.get("success", False), "message": mentions.get("message")}
            except Exception as exc:
                interaction_status = {"success": False, "message": f"Mention lookup failed: {exc}"}

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
                "interaction": interaction_status,
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

        discovery = await self.discovery_client.discovery_snapshot(
            home_limit=max_items,
            hot_limit=max_items,
            rank_limit=max_items,
            topic_limit=max_items,
        )

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

        for item in (discovery.get("hot") or [])[:max_items]:
            candidates.append({
                "source": "discovery.hot",
                "title": item.get("title"),
                "score": ((item.get("stats") or {}).get("views")),
                "raw": item,
            })
        for item in (discovery.get("rank") or [])[:max_items]:
            candidates.append({
                "source": "discovery.rank",
                "title": item.get("title"),
                "score": ((item.get("stats") or {}).get("views")),
                "raw": item,
            })
        for item in (discovery.get("topics") or [])[:max_items]:
            candidates.append({
                "source": "discovery.topic",
                "title": item.get("name") or item.get("title"),
                "score": item.get("topic_id"),
                "raw": item,
            })

        seen = set()
        opportunities = []
        for item in candidates:
            title = item.get("title")
            if title in (None, ""):
                continue
            key = (item.get("source"), title)
            if key in seen:
                continue
            seen.add(key)
            source = item.get("source") or "unknown"
            if source.startswith("discovery.topic"):
                suggested_action = "evaluate-topic-fit"
                reason = "discovery layer surfaced a topic worth checking against current creator direction"
            elif source.startswith("discovery"):
                suggested_action = "check-trend-fit"
                reason = f"{source} surfaced an active discovery signal"
            else:
                suggested_action = "amplify-or-review"
                reason = f"creative-center {source} surfaced this content"
            opportunities.append({
                "title": title,
                "source": source,
                "signal": item.get("score"),
                "suggested_action": suggested_action,
                "reason": reason,
            })
            if len(opportunities) >= max_items:
                break

        return {
            "success": True,
            "schema": "bilibili.client_workflows.content_opportunity_brief.v1",
            "period": period,
            "opportunities": opportunities,
            "discovery_status": discovery.get("topic_status") if discovery.get("success") else {"success": False, "message": discovery.get("message")},
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

    async def operator_decision_loop(
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

        enriched_context = dict(context)
        enriched_context["external_text"] = text
        focus = ((context.get("interaction_context") or {}).get("focus") or {})
        focus_text = self._pick_first_nonempty(focus.get("text"), focus.get("source_content"), focus.get("target_reply_content"))
        interest_profile = self._classify_interest(
            text=(focus_text or text or ""),
            entity=context.get("entity"),
        )
        entity_context = await self._enrich_entity_context(context.get("entity")) if context.get("entity") else {"success": False, "message": "No entity"}
        decision = self._choose_operator_decision(
            interest_profile=interest_profile,
            context=enriched_context,
            entity_context=entity_context,
        )
        operator_brief = self._build_reply_operator_brief(
            context=enriched_context,
            interest_profile=interest_profile,
            decision=decision,
            entity_context=entity_context,
        )

        return {
            "success": True,
            "schema": "bilibili.client_workflows.operator_decision_loop.v1",
            "decision": decision,
            "interest_profile": interest_profile,
            "operator_brief": operator_brief,
            "entity_context": entity_context,
            "reply_guidance": enriched_context.get("reply_guidance"),
            "candidate_reply_input": enriched_context.get("candidate_reply_input"),
            "context": {
                "entity": enriched_context.get("entity"),
                "interaction_context": enriched_context.get("interaction_context"),
                "reply_guidance": enriched_context.get("reply_guidance"),
                "candidate_reply_input": enriched_context.get("candidate_reply_input"),
                "reply_targets": enriched_context.get("reply_targets"),
                "reply_brief": enriched_context.get("reply_brief"),
                "thread_context": enriched_context.get("thread_context"),
                "status": enriched_context.get("status"),
                "external_text": enriched_context.get("external_text"),
            },
            "text": "\n".join([
                f"decision: {decision.get('action')}",
                f"reason: {decision.get('reason')}",
                f"reply_to: {operator_brief.get('who')}",
                f"object: {((operator_brief.get('object') or {}).get('title')) or ((operator_brief.get('object') or {}).get('type')) or 'unknown'}",
            ]),
        }

    async def draft_reply_candidate(
        self,
        text: str = "",
        target: Optional[str] = None,
        source: str = "reply",
        receiver_id: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        loop = await self.operator_decision_loop(text=text, target=target, source=source, receiver_id=receiver_id, limit=limit)
        if not loop.get("success"):
            return loop

        draft_text = self._compose_reply_text(
            context=loop.get("context") or {},
            decision=loop.get("decision") or {},
            interest_profile=loop.get("interest_profile") or {},
            operator_brief=loop.get("operator_brief") or {},
        )
        send_plan = self._build_send_plan(context=loop.get("context") or {}, draft_text=draft_text)

        return {
            "success": True,
            "schema": "bilibili.client_workflows.draft_reply_candidate.v1",
            "decision": loop.get("decision"),
            "interest_profile": loop.get("interest_profile"),
            "operator_brief": loop.get("operator_brief"),
            "draft": {
                "text": draft_text,
                "ready": bool(draft_text),
                "tone": ((loop.get("operator_brief") or {}).get("style") or {}).get("tone"),
            },
            "send_plan": send_plan,
            "context": loop.get("context"),
        }

    async def send_or_queue_reply(
        self,
        text: str = "",
        target: Optional[str] = None,
        source: str = "reply",
        receiver_id: Optional[int] = None,
        limit: int = 10,
        draft_text: Optional[str] = None,
        execute_send: bool = False,
        force_public_send: bool = False,
    ) -> Dict[str, Any]:
        draft = await self.draft_reply_candidate(text=text, target=target, source=source, receiver_id=receiver_id, limit=limit)
        if not draft.get("success"):
            return draft

        final_text = (draft_text or ((draft.get("draft") or {}).get("text")) or "").strip()
        send_plan = self._build_send_plan(
            context=draft.get("context") or {},
            draft_text=final_text,
            force_public_send=bool(force_public_send),
        )

        queued_task = self._build_task(
            task_type="reply_queue",
            title=f"回复 {(((draft.get('operator_brief') or {}).get('who')) or 'unknown')}",
            priority=88 if ((draft.get("decision") or {}).get("should_reply")) else 60,
            reason=((draft.get("decision") or {}).get("reason") or "reply draft prepared"),
            source="client_workflows.send_or_queue_reply",
            payload={
                "draft_text": final_text,
                "send_plan": send_plan,
                "context": draft.get("context"),
            },
        )

        if not execute_send:
            return {
                "success": True,
                "schema": "bilibili.client_workflows.send_or_queue_reply.v1",
                "mode": "queued",
                "sent": False,
                "queue_item": queued_task,
                "send_plan": send_plan,
                "draft": {"text": final_text, "ready": bool(final_text)},
            }

        if not final_text:
            return {
                "success": False,
                "message": "No draft text available to send.",
                "send_plan": send_plan,
                "queue_item": queued_task,
            }

        if send_plan.get("mode") == "direct_send" and send_plan.get("receiver_id"):
            result = await self.message_center.send_text(receiver_id=int(send_plan["receiver_id"]), text=final_text)
            return {
                "success": bool(result.get("success")),
                "schema": "bilibili.client_workflows.send_or_queue_reply.v1",
                "mode": "sent",
                "sent": bool(result.get("success")),
                "result": result,
                "send_plan": send_plan,
                "draft": {"text": final_text, "ready": True},
            }

        if send_plan.get("mode") == "public_comment_send":
            if send_plan.get("resource_type") == "video" and send_plan.get("resource_id_type") == "bvid":
                result = await self.operations.send_video_comment(
                    text=final_text,
                    bvid=send_plan.get("resource_id"),
                    root=send_plan.get("root"),
                    parent=send_plan.get("parent"),
                )
            else:
                result = await self.operations.send_resource_comment(
                    text=final_text,
                    oid=int(send_plan.get("resource_id")),
                    resource_type=send_plan.get("resource_type"),
                    root=send_plan.get("root"),
                    parent=send_plan.get("parent"),
                )
            return {
                "success": bool(result.get("success")),
                "schema": "bilibili.client_workflows.send_or_queue_reply.v1",
                "mode": "sent",
                "sent": bool(result.get("success")),
                "result": result,
                "send_plan": send_plan,
                "draft": {"text": final_text, "ready": True},
            }

        return {
            "success": True,
            "schema": "bilibili.client_workflows.send_or_queue_reply.v1",
            "mode": "queued",
            "sent": False,
            "queue_item": queued_task,
            "send_plan": send_plan,
            "draft": {"text": final_text, "ready": bool(final_text)},
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
            "operator_decision_loop": self.operator_decision_loop,
            "draft_reply_candidate": self.draft_reply_candidate,
            "send_or_queue_reply": self.send_or_queue_reply,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "message": f"Unknown client_workflows action: {action}"}
        return await handler(**kwargs)
