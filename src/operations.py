"""Bilibili operations/community-management module.

Built for creator/community ops tasks such as:
- account auth verification
- follower / following inspection
- follow / unfollow / remove fan
- like a video
- post/repost/delete dynamics
- send comments / reply to comments
- like / pin / delete comments
- set space notice

This module intentionally prefers the `bilibili_api` library for account-side
operations instead of reimplementing fragile endpoints by hand.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .auth import BilibiliAuth
from .client_base import BilibiliClientBase, bili_comment, bili_dynamic, bili_user


class BilibiliOperations(BilibiliClientBase):
    """Creator/community operations for Bilibili accounts."""

    def __init__(self, auth: BilibiliAuth):
        super().__init__(auth=auth)

    @staticmethod
    def _comment_type_from_string(type_name: str):
        normalized = (type_name or "video").strip().lower()
        mapping = {
            "video": bili_comment.CommentResourceType.VIDEO,
            "article": bili_comment.CommentResourceType.ARTICLE,
            "dynamic": bili_comment.CommentResourceType.DYNAMIC,
            "dynamic_draw": bili_comment.CommentResourceType.DYNAMIC_DRAW,
            "audio": bili_comment.CommentResourceType.AUDIO,
            "audio_list": bili_comment.CommentResourceType.AUDIO_LIST,
            "cheese": bili_comment.CommentResourceType.CHEESE,
            "black_room": bili_comment.CommentResourceType.BLACK_ROOM,
            "manga": bili_comment.CommentResourceType.MANGA,
            "activity": bili_comment.CommentResourceType.ACTIVITY,
        }
        if normalized not in mapping:
            raise ValueError(f"Unsupported comment resource type: {type_name}")
        return mapping[normalized]

    @staticmethod
    def _comment_order_from_string(order: str):
        normalized = (order or "time").strip().lower()
        if normalized == "like":
            return bili_comment.OrderType.LIKE
        return bili_comment.OrderType.TIME

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

    @staticmethod
    def _relation_from_action(action: str):
        normalized = (action or "").strip().lower()
        mapping = {
            "follow": bili_user.RelationType.SUBSCRIBE,
            "subscribe": bili_user.RelationType.SUBSCRIBE,
            "unfollow": bili_user.RelationType.UNSUBSCRIBE,
            "unsubscribe": bili_user.RelationType.UNSUBSCRIBE,
            "remove_fan": bili_user.RelationType.REMOVE_FANS,
            "remove-fan": bili_user.RelationType.REMOVE_FANS,
            "block": bili_user.RelationType.BLOCK,
            "unblock": bili_user.RelationType.UNBLOCK,
        }
        if normalized not in mapping:
            raise ValueError(f"Unsupported relation action: {action}")
        return mapping[normalized]

    async def verify_auth(self) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        cred = self._credential()
        profile = await bili_user.get_self_info(cred)
        return {
            "success": True,
            "uid": profile.get("mid"),
            "username": profile.get("uname"),
            "level": profile.get("level_info", {}).get("current_level"),
            "vip": profile.get("vip", {}),
            "raw": profile,
        }

    async def get_my_profile(self) -> Dict[str, Any]:
        return await self.verify_auth()

    async def list_my_videos(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        order: str = "pubdate",
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        cred = self._credential()
        me = await bili_user.get_self_info(cred)
        u = bili_user.User(me["mid"], credential=cred)
        data = await u.get_videos(
            pn=page,
            ps=page_size,
            keyword=keyword,
            order=self._video_order_from_string(order),
        )
        return {
            "success": True,
            "uid": me["mid"],
            "username": me.get("uname"),
            "page": page,
            "page_size": page_size,
            "items": data,
        }

    async def list_followers(self, uid: Optional[int] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        cred = self._credential()
        if uid is None:
            me = await bili_user.get_self_info(cred)
            uid = me["mid"]
        u = bili_user.User(int(uid), credential=cred)
        data = await u.get_followers(pn=page, ps=page_size)
        return {"success": True, "uid": uid, "page": page, "page_size": page_size, "items": data}

    async def list_followings(self, uid: Optional[int] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        cred = self._credential()
        if uid is None:
            me = await bili_user.get_self_info(cred)
            uid = me["mid"]
        u = bili_user.User(int(uid), credential=cred)
        data = await u.get_followings(pn=page, ps=page_size)
        return {"success": True, "uid": uid, "page": page, "page_size": page_size, "items": data}

    async def operate_user_relation(self, uid: int, action: str) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        relation = self._relation_from_action(action)
        u = bili_user.User(int(uid), credential=self._credential())
        data = await u.modify_relation(relation)
        return {"success": True, "uid": int(uid), "action": action, "result": data}

    async def like_video(self, url: Optional[str] = None, bvid: Optional[str] = None, status: bool = True) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        v = self._video(url=url, bvid=bvid, require_auth=True)
        data = await v.like(status)
        return {"success": True, "bvid": v.get_bvid(), "status": status, "result": data}

    async def list_video_comments(
        self,
        url: Optional[str] = None,
        bvid: Optional[str] = None,
        page: int = 1,
        order: str = "time",
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        v = self._video(url=url, bvid=bvid)
        aid = v.get_aid()
        data = await bili_comment.get_comments(
            oid=aid,
            type_=bili_comment.CommentResourceType.VIDEO,
            page_index=page,
            order=self._comment_order_from_string(order),
            credential=self._credential() if self.auth.is_authenticated else None,
        )
        return {"success": True, "bvid": v.get_bvid(), "aid": aid, "page": page, "order": order, "items": data}

    async def send_video_comment(
        self,
        text: str,
        url: Optional[str] = None,
        bvid: Optional[str] = None,
        root: Optional[int] = None,
        parent: Optional[int] = None,
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        v = self._video(url=url, bvid=bvid, require_auth=True)
        aid = v.get_aid()
        data = await bili_comment.send_comment(
            text=text,
            oid=aid,
            type_=bili_comment.CommentResourceType.VIDEO,
            root=root,
            parent=parent,
            credential=self._credential(),
        )
        return {
            "success": True,
            "bvid": v.get_bvid(),
            "aid": aid,
            "text": text,
            "root": root,
            "parent": parent,
            "result": data,
        }

    async def comment_action(
        self,
        oid: int,
        resource_type: str,
        rpid: int,
        action: str,
        status: bool = True,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        if action in {"like", "pin", "delete"}:
            auth_error = self._require_auth()
            if auth_error:
                return auth_error

        type_enum = self._comment_type_from_string(resource_type)
        c = bili_comment.Comment(oid=int(oid), type_=type_enum, rpid=int(rpid), credential=self._credential())

        normalized = action.strip().lower()
        if normalized == "like":
            data = await c.like(status)
        elif normalized == "pin":
            data = await c.pin(status)
        elif normalized == "delete":
            data = await c.delete()
        elif normalized in {"sub_comments", "subcomments", "list_replies", "replies"}:
            data = await c.get_sub_comments(page_index=page, page_size=page_size)
        else:
            return {"success": False, "message": f"Unsupported comment action: {action}"}

        return {
            "success": True,
            "oid": int(oid),
            "resource_type": resource_type,
            "rpid": int(rpid),
            "action": action,
            "result": data,
        }

    async def post_dynamic(self, text: str) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        build = bili_dynamic.BuildDynamic.empty().add_text(text)
        data = await bili_dynamic.send_dynamic(build, self._credential())
        return {"success": True, "text": text, "result": data}

    async def repost_dynamic(self, dynamic_id: int, text: str = "转发动态") -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        dyn = bili_dynamic.Dynamic(dynamic_id=int(dynamic_id), credential=self._credential())
        data = await dyn.repost(text=text)
        return {"success": True, "dynamic_id": int(dynamic_id), "text": text, "result": data}

    async def delete_dynamic(self, dynamic_id: int) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        dyn = bili_dynamic.Dynamic(dynamic_id=int(dynamic_id), credential=self._credential())
        data = await dyn.delete()
        return {"success": True, "dynamic_id": int(dynamic_id), "result": data}

    async def get_dynamic_info(self, dynamic_id: int) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error

        dyn = bili_dynamic.Dynamic(dynamic_id=int(dynamic_id), credential=self._credential() if self.auth.is_authenticated else None)
        data = await dyn.get_info()
        return {"success": True, "dynamic_id": int(dynamic_id), "result": data}

    async def list_my_dynamics(self, offset: str = "") -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        cred = self._credential()
        me = await bili_user.get_self_info(cred)
        u = bili_user.User(me["mid"], credential=cred)
        data = await u.get_dynamics_new(offset=offset)
        return {"success": True, "uid": me["mid"], "username": me.get("uname"), "offset": offset, "items": data}

    async def set_space_notice(self, content: str) -> Dict[str, Any]:
        lib_error = self._require_library()
        if lib_error:
            return lib_error
        auth_error = self._require_auth()
        if auth_error:
            return auth_error

        cred = self._credential()
        me = await bili_user.get_self_info(cred)
        u = bili_user.User(me["mid"], credential=cred)
        data = await u.set_space_notice(content=content)
        return {"success": True, "uid": me["mid"], "content": content, "result": data}

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            "verify_auth": self.verify_auth,
            "profile": self.get_my_profile,
            "list_my_videos": self.list_my_videos,
            "list_followers": self.list_followers,
            "list_followings": self.list_followings,
            "follow_user": lambda **kw: self.operate_user_relation(action="follow", **kw),
            "unfollow_user": lambda **kw: self.operate_user_relation(action="unfollow", **kw),
            "remove_fan": lambda **kw: self.operate_user_relation(action="remove_fan", **kw),
            "block_user": lambda **kw: self.operate_user_relation(action="block", **kw),
            "unblock_user": lambda **kw: self.operate_user_relation(action="unblock", **kw),
            "like_video": self.like_video,
            "list_video_comments": self.list_video_comments,
            "send_video_comment": self.send_video_comment,
            "reply_video_comment": self.send_video_comment,
            "comment_action": self.comment_action,
            "like_comment": lambda **kw: self.comment_action(action="like", **kw),
            "pin_comment": lambda **kw: self.comment_action(action="pin", **kw),
            "delete_comment": lambda **kw: self.comment_action(action="delete", **kw),
            "list_sub_comments": lambda **kw: self.comment_action(action="sub_comments", **kw),
            "post_dynamic": self.post_dynamic,
            "repost_dynamic": self.repost_dynamic,
            "delete_dynamic": self.delete_dynamic,
            "get_dynamic_info": self.get_dynamic_info,
            "list_my_dynamics": self.list_my_dynamics,
            "set_space_notice": self.set_space_notice,
        }
        handler = actions.get(action)
        if not handler:
            return {"success": False, "message": f"Unknown operations action: {action}"}
        return await handler(**kwargs)
