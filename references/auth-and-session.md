# Auth and Session Reference

Use this when the task is about login state, QR auth, persisted cookies, or session validation.

## Primary actions

```bash
python main.py auth_client start_qr_login
python main.py auth_client poll_qr_login '{"login_key": "<login_key>"}'
python main.py auth_client verify_auth
python main.py auth_client describe_auth
python main.py auth_client clear_auth
```

## Default workflow

1. Prefer QR login.
2. Verify auth before any write-heavy creator workflow.
3. If auth is missing or stale, repair auth first instead of attempting writes blind.
4. Only use persisted auth when continuity matters.

## Good triggers

- 登录 B站
- 二维码登录
- cookie 失效
- 验证一下 B站 登录
- 清掉 B站 会话
