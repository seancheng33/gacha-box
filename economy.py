"""经济系统：金币增减、每日签到。"""
from datetime import date

REGISTER_COINS = 1000
SIGNIN_REWARD = 100


def grant(conn, user_id, amount):
    """发放金币（可为负，但余额不会低于 0——CHECK 约束兜底）。"""
    conn.execute("UPDATE users SET coins = coins + ? WHERE id=?", (amount, user_id))


def signin(conn, user_id, today=None):
    """每个自然日一次签到。返回 (是否成功, 提示语)。"""
    today = today or date.today().isoformat()
    row = conn.execute("SELECT last_checkin FROM users WHERE id=?", (user_id,)).fetchone()
    if row["last_checkin"] == today:
        return False, "今天已经签到过了，明天再来"
    conn.execute(
        "UPDATE users SET last_checkin=?, coins = coins + ? WHERE id=?",
        (today, SIGNIN_REWARD, user_id),
    )
    return True, "签到成功，金币 +%d" % SIGNIN_REWARD
