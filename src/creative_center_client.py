"""Creator analytics client backed by bilibili_api.creative_center."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .auth import BilibiliAuth
from .client_base import BilibiliClientBase

try:
    from bilibili_api import creative_center as bili_creative_center
    CREATIVE_CENTER_AVAILABLE = True
    CREATIVE_CENTER_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - import guard
    bili_creative_center = None
    CREATIVE_CENTER_AVAILABLE = False
    CREATIVE_CENTER_IMPORT_ERROR = str(exc)


class BilibiliCreativeCenterClient(BilibiliClientBase):
    """Creator-center analytics and dashboard-facing KPI access."""

    def __init__(self, auth: Optional[BilibiliAuth] = None):
        super().__init__(auth=auth)

    def _require_creative_center(self) -> Optional[Dict[str, Any]]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        if CREATIVE_CENTER_AVAILABLE:
            return None
        return self._failure(
            "bilibili_api.creative_center is required for this action.",
            detail=CREATIVE_CENTER_IMPORT_ERROR,
        )

    @staticmethod
    def _enum_member(enum_cls, name: Optional[str], default_name: str):
        candidate = (name or default_name).strip().upper().replace("-", "_").replace(" ", "_")
        return enum_cls.__members__.get(candidate, enum_cls.__members__[default_name])

    @staticmethod
    def _first_dict(data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    return item
        return {}

    @staticmethod
    def _pick_metric(data: Any, keys: tuple[str, ...]) -> Any:
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key] not in (None, "", [], {}):
                    return data[key]
            for value in data.values():
                found = BilibiliCreativeCenterClient._pick_metric(value, keys)
                if found not in (None, "", [], {}):
                    return found
        elif isinstance(data, list):
            for item in data:
                found = BilibiliCreativeCenterClient._pick_metric(item, keys)
                if found not in (None, "", [], {}):
                    return found
        return None

    async def compare(self) -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_creative_center.get_compare(self._credential(require_auth=True))
            return self._success(result=data)
        except Exception as exc:
            return self._failure("Creative-center compare lookup failed.", detail=str(exc))

    async def overview(self, period: str = "week") -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            period_enum = self._enum_member(bili_creative_center.GraphPeriod, period, "WEEK")
            data = await bili_creative_center.get_overview(self._credential(require_auth=True), period=period_enum)
            return self._success(period=period_enum.name.lower(), result=data)
        except Exception as exc:
            return self._failure("Creative-center overview lookup failed.", detail=str(exc), period=period)

    async def graph(self, period: str = "week", graph_type: str = "play") -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            period_enum = self._enum_member(bili_creative_center.GraphPeriod, period, "WEEK")
            type_enum = self._enum_member(bili_creative_center.GraphType, graph_type, "PLAY")
            data = await bili_creative_center.get_graph(
                self._credential(require_auth=True),
                period=period_enum,
                graph_type=type_enum,
            )
            return self._success(period=period_enum.name.lower(), graph_type=type_enum.name.lower(), result=data)
        except Exception as exc:
            return self._failure("Creative-center graph lookup failed.", detail=str(exc), period=period, graph_type=graph_type)

    async def fan_overview(self, period: str = "week") -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            period_enum = self._enum_member(bili_creative_center.FanGraphPeriod, period, "WEEK")
            data = await bili_creative_center.get_fan_overview(self._credential(require_auth=True), period=period_enum)
            return self._success(period=period_enum.name.lower(), result=data)
        except Exception as exc:
            return self._failure("Creative-center fan overview lookup failed.", detail=str(exc), period=period)

    async def fan_graph(self, period: str = "week", graph_type: str = "all_fans") -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            period_enum = self._enum_member(bili_creative_center.FanGraphPeriod, period, "WEEK")
            type_enum = self._enum_member(bili_creative_center.FanGraphType, graph_type, "ALL_FANS")
            data = await bili_creative_center.get_fan_graph(
                self._credential(require_auth=True),
                period=period_enum,
                graph_type=type_enum,
            )
            return self._success(period=period_enum.name.lower(), graph_type=type_enum.name.lower(), result=data)
        except Exception as exc:
            return self._failure("Creative-center fan graph lookup failed.", detail=str(exc), period=period, graph_type=graph_type)

    async def video_survey(self) -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            data = await bili_creative_center.get_video_survey(self._credential(require_auth=True))
            return self._success(result=data)
        except Exception as exc:
            return self._failure("Creative-center video survey lookup failed.", detail=str(exc))

    async def video_playanalysis(self, copyright: str = "all") -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error
        try:
            copyright_enum = self._enum_member(bili_creative_center.Copyright, copyright, "ALL")
            data = await bili_creative_center.get_video_playanalysis(
                self._credential(require_auth=True),
                copyright=copyright_enum,
            )
            return self._success(copyright=copyright_enum.name.lower(), result=data)
        except Exception as exc:
            return self._failure("Creative-center play analysis lookup failed.", detail=str(exc), copyright=copyright)

    async def dashboard_snapshot(self, period: str = "week") -> Dict[str, Any]:
        error = self._require_creative_center() or self._require_auth()
        if error:
            return error

        overview = await self.overview(period=period)
        compare = await self.compare()
        fan = await self.fan_overview(period=period)
        survey = await self.video_survey()
        playanalysis = await self.video_playanalysis()

        overview_data = overview.get("result") or {}
        compare_data = compare.get("result") or {}
        fan_data = fan.get("result") or {}
        survey_data = survey.get("result") or {}
        playanalysis_data = playanalysis.get("result") or {}

        kpis = {
            "play": self._pick_metric(overview_data, ("play", "play_num", "view")),
            "visitor": self._pick_metric(overview_data, ("visitor", "visitor_num")),
            "fans": self._pick_metric(fan_data, ("all_fans", "fans", "follower")),
            "new_fans": self._pick_metric(fan_data, ("new_fans", "fans_inc", "follow")),
            "comment": self._pick_metric(overview_data, ("comment", "reply", "comment_num")),
            "like": self._pick_metric(overview_data, ("like", "like_num")),
            "share": self._pick_metric(overview_data, ("share", "share_num")),
        }

        return self._success(
            period=period,
            kpis=kpis,
            modules={
                "overview": overview_data,
                "compare": compare_data,
                "fan_overview": fan_data,
                "video_survey": survey_data,
                "video_playanalysis": playanalysis_data,
            },
            status={
                "overview": overview.get("success", False),
                "compare": compare.get("success", False),
                "fan_overview": fan.get("success", False),
                "video_survey": survey.get("success", False),
                "video_playanalysis": playanalysis.get("success", False),
            },
        )

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "compare": self.compare,
            "overview": self.overview,
            "graph": self.graph,
            "fan_overview": self.fan_overview,
            "fan_graph": self.fan_graph,
            "video_survey": self.video_survey,
            "video_playanalysis": self.video_playanalysis,
            "dashboard_snapshot": self.dashboard_snapshot,
        }
        handler = actions.get(action)
        if not handler:
            return self._failure(f"Unknown creative_center action: {action}")
        return await handler(**kwargs)
