"""抽卡引擎：概率判定、双保底、批量抽。随机源可注入，便于测试复现。"""
import json
import secrets

RARITY_NAMES = {1: "普通", 2: "稀有", 3: "史诗", 4: "传说", 5: "SSR"}

RARITY_META = {
    1: {"name": "普通", "color": "#8b93a1", "glow": "rgba(139,147,161,.45)"},
    2: {"name": "稀有", "color": "#4a90d9", "glow": "rgba(74,144,217,.45)"},
    3: {"name": "史诗", "color": "#a86bd8", "glow": "rgba(168,107,216,.5)"},
    4: {"name": "传说", "color": "#e08a2e", "glow": "rgba(224,138,46,.55)"},
    5: {"name": "SSR", "color": "#f5c451", "glow": "rgba(245,196,81,.75)"},
}

DEFAULT_WEIGHTS = {1: 55.0, 2: 28.0, 3: 12.0, 4: 4.0, 5: 1.0}
PITY_LIMIT = 60          # 第 60 抽必出 SSR
COST_SINGLE = 100
COST_TEN = 900
TEN_GUARANTEE_RARITY = 3  # 十连保底：至少 1 张史诗及以上

# 生产随机源；测试里替换为 random.Random(seed) 以获得可复现结果
RNG = secrets.SystemRandom()


def load_weights(conn):
    row = conn.execute("SELECT value FROM app_config WHERE key='weights'").fetchone()
    if not row:
        return dict(DEFAULT_WEIGHTS)
    data = json.loads(row["value"])
    return {int(k): float(v) for k, v in data.items()}


def save_weights(conn, weights):
    normalized = {str(k): round(float(v), 2) for k, v in weights.items()}
    conn.execute(
        "INSERT INTO app_config(key, value) VALUES('weights', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (json.dumps(normalized, ensure_ascii=False),),
    )


def validate_weights(weights):
    """返回错误信息；None 表示合法。"""
    if set(weights) != {1, 2, 3, 4, 5}:
        return "必须恰好包含五个等级"
    if any(v < 0 for v in weights.values()):
        return "概率不能为负数"
    total = sum(weights.values())
    if abs(total - 100.0) > 0.01:
        return "五个等级概率之和必须等于 100%%（当前 %.2f%%）" % total
    if weights[5] <= 0:
        return "SSR 概率必须大于 0"
    return None


def pick_rarity(weights, rng=None):
    """加权抽段：累计权重区间内命中。零权重等级永远不会被抽中。"""
    rng = rng or RNG
    total = sum(v for v in weights.values() if v > 0)
    if total <= 0:
        raise ValueError("概率表非法：总权重为 0")
    point = rng.random() * total
    acc = 0.0
    for rarity in sorted(weights):
        w = weights[rarity]
        if w <= 0:
            continue
        acc += w
        if point < acc:
            return rarity
    # 浮点边界兜底：返回权重最大的等级
    return max((k for k, v in weights.items() if v > 0), key=lambda k: weights[k])


def pick_card(conn, rarity, rng=None):
    """在指定等级已启用的卡中均匀选一张；该等级无卡时退化为全池抽。"""
    rng = rng or RNG
    rows = conn.execute(
        "SELECT * FROM cards WHERE enabled=1 AND rarity=? ORDER BY id", (rarity,)
    ).fetchall()
    if not rows:
        rows = conn.execute("SELECT * FROM cards WHERE enabled=1 ORDER BY id").fetchall()
    if not rows:
        raise RuntimeError("卡池为空，请先执行 seed")
    return dict(rng.choice(rows))


def draw_one(conn, pity, weights, rng=None):
    """单抽：返回 (card, new_pity, is_pity)。"""
    rng = rng or RNG
    if pity >= PITY_LIMIT - 1:
        card = pick_card(conn, 5, rng)
        return card, 0, True
    rarity = pick_rarity(weights, rng)
    card = pick_card(conn, rarity, rng)
    new_pity = 0 if rarity == 5 else pity + 1
    return card, new_pity, False


def draw_batch(conn, pity, weights, count, rng=None):
    """批量抽（1 或 10）。返回 ([(card, is_pity), ...], new_pity)。

    十连保底：整批没有史诗及以上时，把第一张替换为史诗档。
    """
    rng = rng or RNG
    results = []
    for _ in range(count):
        card, pity, is_pity = draw_one(conn, pity, weights, rng)
        results.append((card, is_pity))
    if count >= 10 and not any(card["rarity"] >= TEN_GUARANTEE_RARITY for card, _ in results):
        results[0] = (pick_card(conn, TEN_GUARANTEE_RARITY, rng), False)
    return results, pity
