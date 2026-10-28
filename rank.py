"""排行榜：收集度 / SSR 数量 / 累计抽数。"""


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def by_collection(conn, limit=20):
    return _rows(
        conn,
        "SELECT u.username, COUNT(DISTINCT col.card_id) AS value "
        "FROM users u JOIN collections col ON col.user_id = u.id "
        "JOIN cards c ON c.id = col.card_id AND c.enabled = 1 "
        "GROUP BY u.id ORDER BY value DESC, u.id ASC LIMIT ?",
        (limit,),
    )


def by_ssr(conn, limit=20):
    """LEFT JOIN：没有 SSR 的用户也上榜（显示 0）。"""
    return _rows(
        conn,
        "SELECT u.username, "
        "COALESCE(SUM(CASE WHEN c.rarity = 5 THEN col.count ELSE 0 END), 0) AS value "
        "FROM users u "
        "LEFT JOIN collections col ON col.user_id = u.id "
        "LEFT JOIN cards c ON c.id = col.card_id "
        "GROUP BY u.id ORDER BY value DESC, u.id ASC LIMIT ?",
        (limit,),
    )


def by_draws(conn, limit=20):
    return _rows(
        conn,
        "SELECT u.username, COUNT(d.id) AS value "
        "FROM users u JOIN draws d ON d.user_id = u.id "
        "GROUP BY u.id ORDER BY value DESC, u.id ASC LIMIT ?",
        (limit,),
    )
