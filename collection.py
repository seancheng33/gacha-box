"""收集系统：入册、持有数累加、图鉴查询与收集进度。"""
from datetime import datetime


def owned_ids(conn, user_id):
    return {row["card_id"] for row in
            conn.execute("SELECT card_id FROM collections WHERE user_id=?", (user_id,))}


def add_card(conn, user_id, card_id, now=None):
    """入册或累加持有数，返回累加后的数量。"""
    now = now or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO collections(user_id, card_id, count, first_at) VALUES(?, ?, 1, ?) "
        "ON CONFLICT(user_id, card_id) DO UPDATE SET count = count + 1",
        (user_id, card_id, now),
    )
    return conn.execute(
        "SELECT count FROM collections WHERE user_id=? AND card_id=?", (user_id, card_id)
    ).fetchone()["count"]


def album(conn, user_id, rarity=None):
    """全部启用卡 + 当前用户持有数。未拥有的 count 为 0。"""
    sql = (
        "SELECT c.*, COALESCE(col.count, 0) AS count, col.first_at "
        "FROM cards c LEFT JOIN collections col "
        "  ON col.card_id = c.id AND col.user_id = ? "
        "WHERE c.enabled = 1"
    )
    params = [user_id]
    if rarity:
        sql += " AND c.rarity = ?"
        params.append(rarity)
    sql += " ORDER BY c.rarity DESC, c.id"
    return [dict(row) for row in conn.execute(sql, params)]


def progress(conn, user_id):
    """返回 (已收集种类数, 总种类数, 百分比)。"""
    total = conn.execute("SELECT COUNT(*) AS c FROM cards WHERE enabled=1").fetchone()["c"]
    got = conn.execute(
        "SELECT COUNT(DISTINCT col.card_id) AS c FROM collections col "
        "JOIN cards c ON c.id = col.card_id WHERE col.user_id=? AND c.enabled=1",
        (user_id,),
    ).fetchone()["c"]
    pct = round(got * 100.0 / total, 1) if total else 0.0
    return got, total, pct
