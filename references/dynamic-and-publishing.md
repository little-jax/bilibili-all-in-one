# Dynamic and Publishing Workflows

Use this when the task is about posting dynamics, reposting, deleting, updating space notice, or video publishing.

## Strong triggers

- 发动态
- 转发动态
- 删动态
- 改空间公告
- 发视频
- 查稿件 / 改稿件

## Default workflow

1. Confirm the target write surface: dynamic / repost / notice / video draft.
2. If final text is missing, draft it first.
3. Execute only after wording is clear.
4. Return object id / url / result.

## Core commands

```bash
python main.py operations post_dynamic '{"text": "今晚八点直播，来。"}'
python main.py operations repost_dynamic '{"dynamic_id": 1234567890123456789, "text": "这个值得一看"}'
python main.py operations delete_dynamic '{"dynamic_id": 1234567890123456789}'
python main.py operations set_space_notice '{"content": "合作请私信 / 直播时间见动态"}'
```

## Publishing note

Use the publisher surfaces when the task is a real video upload / draft / schedule flow, not a community post.
