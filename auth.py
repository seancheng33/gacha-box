"""认证与会话：注册、登录（含失败限频）、权限装饰器。密码一律 scrypt 哈希。"""
import time
from datetime import datetime
from functools import wraps

from flask import abort, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

FAIL_LIMIT = 5
LOCK_SECONDS = 600
_fails = {}  # username -> {"count": int, "until": float}


def validate_credentials(username, password):
    username = (username or "").strip()
    if not 3 <= len(username) <= 20:
        return None, "用户名需 3~20 个字符"
    if any(ch.isspace() for ch in username):
        return None, "用户名不能包含空格"
    if len(password or "") < 6:
        return None, "密码至少 6 位"
    return username, None


def register(conn, username, password, initial_coins=1000):
    username, err = validate_credentials(username, password)
    if err:
        raise ValueError(err)
    if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        raise ValueError("该用户名已被注册")
    conn.execute(
        "INSERT INTO users(username, password_hash, coins, created_at) VALUES(?, ?, ?, ?)",
        (username, generate_password_hash(password), initial_coins,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    return conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


def is_locked(username):
    state = _fails.get(username)
    return bool(state and state.get("until", 0) > time.time())


def verify(conn, username, password):
    """返回 (user_row | None, error_message | None)。"""
    username = (username or "").strip()
    if is_locked(username):
        left = int(_fails[username]["until"] - time.time()) // 60 + 1
        return None, "失败次数过多，请 %d 分钟后再试" % left
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password or ""):
        state = _fails.setdefault(username, {"count": 0, "until": 0})
        state["count"] += 1
        if state["count"] >= FAIL_LIMIT:
            state["until"] = time.time() + LOCK_SECONDS
            state["count"] = 0
            return None, "失败次数过多，账号已临时锁定 10 分钟"
        return None, "用户名或密码错误"
    _fails.pop(username, None)
    return row, None


def reset_rate_limit():
    """仅供测试使用。"""
    _fails.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            if request.path.startswith("/draw") or request.is_json:
                abort(401)
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def current_user(conn):
    uid = session.get("uid")
    if not uid:
        return None
    return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
